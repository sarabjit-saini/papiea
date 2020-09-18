import os
import asyncio
import logging
import pytest

from datetime import datetime, timezone
from typing import Optional
from yaml import Loader as YamlLoader
from yaml import load as load_yaml

from papiea.client import EntityCRUD
from papiea.core import Action, AttributeDict, EntityReference, Key, Metadata, ProcedureDescription, S2S_Key, Spec
from papiea.python_sdk import ProviderSdk
from papiea.utils import ref_type

SERVER_PORT = int(os.environ.get("SERVER_PORT", "3000"))
ADMIN_KEY = os.environ.get("PAPIEA_ADMIN_S2S_KEY", "")
PAPIEA_URL = os.getenv("PAPIEA_URL", "http://127.0.0.1:3000")

SERVER_CONFIG_HOST = "127.0.0.1"
SERVER_CONFIG_PORT = 9005
PROVIDER_PREFIX = "test_provider"
PROVIDER_VERSION = "0.1.0"
PROVIDER_ADMIN_S2S_KEY = "Sa8xaic9"
USER_S2S_KEY = ""

BUCKET_KIND = 'bucket'
OBJECT_KIND = 'object'

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def load_yaml_from_file(filename):
    with open(filename) as f:
        return load_yaml(f, Loader=YamlLoader)

def setup_kinds():
    global bucket_kind_dict, object_kind_dict
    global bucket_yaml, object_yaml
    global metadata_extension
    global ensure_bucket_exists_takes, ensure_bucket_exists_returns
    global create_object_takes, create_object_returns
    global link_object_takes, link_object_returns
    global unlink_object_takes, unlink_object_returns

    bucket_kind_dict = AttributeDict(kind=BUCKET_KIND)
    object_kind_dict = AttributeDict(kind=OBJECT_KIND)

    bucket_yaml = load_yaml_from_file("./kinds/bucket_kind.yml")
    object_yaml = load_yaml_from_file("./kinds/object_kind.yml")

    bucket_yaml.get('bucket').get('properties').get('objects').get('items') \
        .get('properties')['reference'] = ref_type(OBJECT_KIND, 'Reference of the objects within the bucket')

    object_yaml.get('object').get('properties').get('references').get('items') \
        .get('properties')['bucket_reference'] = ref_type(BUCKET_KIND, 'Reference of the bucket in which the object exists')

    metadata_extension = load_yaml_from_file("./security/metadata_extension.yml")

    ensure_bucket_exists_takes = load_yaml_from_file("./procedures/ensure_bucket_exists_input.yml")
    ensure_bucket_exists_returns = AttributeDict(
        EnsireBucketExistsOutput=ref_type(BUCKET_KIND, 'Reference of the bucket created/found')
    )

    create_object_takes = load_yaml_from_file("./procedures/create_object_input.yml")
    create_object_returns = AttributeDict(
        CreateObjectOutput=ref_type(OBJECT_KIND, 'Reference of the object created')
    )

    link_object_takes = load_yaml_from_file("./procedures/link_object_input.yml")
    link_object_returns = AttributeDict(
        LinkObjectOutput=ref_type(OBJECT_KIND, 'Reference of the object to which it is linked')
    )

    unlink_object_takes = load_yaml_from_file("./procedures/unlink_object_input.yml")
    unlink_object_returns = AttributeDict(
        UnlinkObjectOutput=ref_type(OBJECT_KIND, 'Reference of the object to which it was linked')
    )

async def create_provider_admin_s2s_key(sdk: ProviderSdk, new_key: Key):
  admin_security_api = sdk.provider_security_api

  the_key = S2S_Key(
    name="Test provider admin S2S key",
    owner="nitesh.idnani@nutanix.com",
    key=new_key,
    user_info={"is_provider_admin": True},
  )

  keys = await admin_security_api.list_keys()
  for key in keys:
    if key.name == the_key.name:
      logger.debug(f"Key {the_key.name} already exists")
      return
  try:
    await admin_security_api.create_key(the_key)
    provider_admin_security_api = sdk.new_security_api(new_key)
    user_info = await provider_admin_security_api.user_info()
    logger.debug(f"User info {user_info}")
  except:
    pass

async def create_user_s2s_key(sdk: ProviderSdk):
    admin_security_api = sdk.provider_security_api

    the_key = S2S_Key(
        name="location provider some.user s2s key",
        user_info={"owner": "nitesh"},
    )

    new_s2s_key = await admin_security_api.create_key(the_key)
    user_security_api = sdk.new_security_api(new_s2s_key.key)
    await user_security_api.user_info()
    return new_s2s_key.key

async def cleanup():
    async with EntityCRUD(
        PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, BUCKET_KIND, USER_S2S_KEY
    ) as bucket_entity_client:
        bucket_list = await bucket_entity_client.get_all()
        for bucket in bucket_list:
            await bucket_entity_client.delete(bucket.metadata)

    async with EntityCRUD(
        PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
    ) as object_entity_client:
        object_list = await object_entity_client.get_all()
        for obj in object_list:
            await object_entity_client.delete(obj.metadata)

async def bucket_constructor(ctx, entity):
  """
  Construct a bucket entity
  """
  logger.debug("Inside bucket constructor")
  status = AttributeDict(
      name=entity.spec.name,
      objects=entity.spec.objects
  )
  await ctx.update_status(entity.metadata, status)

async def object_constructor(ctx, entity):
  """
  Construct a object entity
  """
  logger.debug("Inside object constructor")
  status = AttributeDict(
      content=entity.spec.content
  )
  await ctx.update_status(entity.metadata, status)

async def ensure_bucket_exists_handler(ctx, input_bucket_name):
    # Run get query to obtain the list of buckets
    # Check if bucket_name exists in the bucket list
    # If true, simply return the bucket
    # Else, create a new bucket with input_bucket_name and return

    async with ctx.entity_client_for_user(bucket_kind_dict) as entity_client:
        desired_bucket = await entity_client.filter(AttributeDict(spec=AttributeDict(name=input_bucket_name)))
        if len(desired_bucket.results) != 0:
            logger.debug("Bucket already exists. Returning it...")
            return EntityReference(
                uuid=desired_bucket.results[0].metadata.uuid,
                kind=desired_bucket.results[0].metadata.kind
            )

        logger.debug("Bucket not found. Creating new bucket...")    
        ret_entity = await entity_client.create(
            spec=Spec(name=input_bucket_name, objects=list()),
            metadata_extension={
                "owner": "nutanix"
            }
        )

        return EntityReference(
            uuid=ret_entity.metadata.uuid,
            kind=ret_entity.metadata.kind
        )

    return None

async def create_object_handler(ctx, entity_bucket, input_object_name):
    # check if object name already exists in entity.objects
    # if found, return None/failure
    # else create a new object entity and
    # add the object name and bucket reference in the object' references and
    # add the object name and reference in the objects list

    objects_list = entity_bucket.spec.objects
    if not any(obj.name == input_object_name for obj in objects_list):
        logger.debug("Object not found. Creating new object...")
        async with ctx.entity_client_for_user(object_kind_dict) as entity_client:
            entity_object = await entity_client.create(
                Spec(content="", size=0, last_modified=str(datetime.now(timezone.utc)),
                    references=[AttributeDict(
                        object_name=input_object_name,
                        bucket_reference=EntityReference(
                            uuid=entity_bucket.metadata.uuid,
                            kind=BUCKET_KIND
                        )
                    )]
                ),
                metadata_extension={
                    "owner": "nutanix"
                }
            )

        entity_bucket.spec.objects.append(
            AttributeDict(name=input_object_name,
                reference=EntityReference(
                    uuid=entity_object.metadata.uuid,
                    kind=OBJECT_KIND
                )
            )
        )
        async with ctx.entity_client_for_user(bucket_kind_dict) as entity_client:
            await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )

        return EntityReference(
            uuid=entity_object.metadata.uuid,
            kind=entity_object.metadata.kind
        )
    else:
        logger.debug("Object already exists in the bucket")
        return EntityReference(uuid='', kind='')

    return None

async def link_object_handler(ctx, entity_bucket, input_object):
    # assuming input_object to be the object name and the uid
    # check if the name already exist in the objects list
    # if exists, return None/failure
    # else add object name and bucket uid in object' references list and
    # add object name and uid in bucket' objects list

    objects_list = entity_bucket.spec.objects
    if not any(obj.name == input_object.object_name for obj in objects_list):
        logger.debug("Object not found. Linking the object...")
        entity_bucket.spec.objects.append(
            AttributeDict(name=input_object.object_name,
                reference=EntityReference(
                    uuid=input_object.object_uuid,
                    kind=OBJECT_KIND
                )
            )
        )
        async with ctx.entity_client_for_user(bucket_kind_dict) as entity_client:
            await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )

        async with ctx.entity_client_for_user(object_kind_dict) as entity_client:
            entity_object = await entity_client.get(AttributeDict(uuid=input_object.object_uuid))
            entity_object.spec.references.append(
                AttributeDict(object_name=input_object.object_name,
                    bucket_reference=AttributeDict(
                        uuid=entity_bucket.metadata.uuid,
                        kind=BUCKET_KIND
                    )
                )
            )
            await entity_client.update(
                metadata=entity_object.metadata,
                spec=entity_object.spec
            )
            ret_entity = await entity_client.get(entity_object.metadata)

        return EntityReference(
            uuid=ret_entity.metadata.uuid,
            kind=ret_entity.metadata.kind
        )
    else:
        logger.debug("Object already exists in the bucket")
        return EntityReference(uuid='', kind='')

    return None

async def unlink_object_handler(ctx, entity_bucket, input_object):
    # assuming input_object to be the object name and the uid
    # check if the name exists in the object list
    # if does not exists, return None/failure
    # else remove the object name and reference from the objects list and
    # remove the object name and bucket reference from the object' references list
    # if the object' references list become empty, delete the object entity

    objects_list = entity_bucket.spec.objects
    if any(obj.name == input_object.object_name for obj in objects_list):
        logger.debug("Object found. Unlinking the object...")
        entity_bucket.spec.objects[:] = [d for d in entity_bucket.spec.objects if d.get('name') != input_object.object_name]
        async with ctx.entity_client_for_user(bucket_kind_dict) as entity_client:
            await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )

        async with ctx.entity_client_for_user(object_kind_dict) as entity_client:
            entity_object = await entity_client.get(AttributeDict(uuid=input_object.object_uuid))
            entity_object.spec.references[:] = [d for d in entity_object.spec.references
                if d.get('object_name') != input_object.object_name or d.get('bucket_reference') != {'uuid': entity_bucket.metadata.uuid, 'kind': BUCKET_KIND}]

            if not entity_object.spec.references:
                logger.debug("Object refcount is zero. Deleting the object...")
                await entity_client.delete(entity_object.metadata)
                return EntityReference(uuid='', kind='')

            await entity_client.update(
                metadata=entity_object.metadata,
                spec=entity_object.spec
            )
            ret_entity = await entity_client.get(entity_object.metadata)

        return EntityReference(
            uuid=ret_entity.metadata.uuid,
            kind=ret_entity.metadata.kind
        )
    else:
        logger.debug("Object not found in the bucket")
        return EntityReference(uuid='', kind='')

    return None

async def print_kinds_data():
    async with EntityCRUD(
        PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, BUCKET_KIND, USER_S2S_KEY
    ) as bucket_entity_client:
        print(await bucket_entity_client.get_all())
    async with EntityCRUD(
        PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
    ) as object_entity_client:
        print(await object_entity_client.get_all())


class TestBasic:

    @pytest.mark.asyncio
    async def test_basic(self):
        logger.debug("Running basic test")

        setup_kinds()

        async with ProviderSdk.create_provider(
            PAPIEA_URL, ADMIN_KEY, SERVER_CONFIG_HOST, SERVER_CONFIG_PORT, logger=logger
        ) as sdk:
            sdk.version(PROVIDER_VERSION)
            sdk.prefix(PROVIDER_PREFIX)

            # TODO: Add security policy to set the secure_with parameters
            sdk.metadata_extension(metadata_extension)
            await create_provider_admin_s2s_key(sdk, ADMIN_KEY)

            bucket = sdk.new_kind(bucket_yaml)
            obj = sdk.new_kind(object_yaml)
            bucket.on_create(bucket_constructor)
            obj.on_create(object_constructor)
            # bucket -> name change handler
            # bucket -> objects change handler
            # object -> content change handler
            ensure_bucket_exists_procedure_description = ProcedureDescription(
                input_schema=ensure_bucket_exists_takes,
                output_schema=ensure_bucket_exists_returns,
                description="Description for ensure_bucket_exists kind-level procedure"
            )
            bucket.kind_procedure(
                "ensure_bucket_exists",
                ensure_bucket_exists_procedure_description,
                ensure_bucket_exists_handler
            )

            create_object_procedure_description = ProcedureDescription(
                input_schema=create_object_takes,
                output_schema=create_object_returns,
                description="Description for create_object entity-level procedure"
            )
            bucket.entity_procedure(
                    "create_object",
                    create_object_procedure_description,
                    create_object_handler
            )

            link_object_procedure_description = ProcedureDescription(
                input_schema=link_object_takes,
                output_schema=link_object_returns,
                description="Description for link_object entity-level procedure"
            )
            bucket.entity_procedure(
                    "link_object",
                    link_object_procedure_description,
                    link_object_handler
            )

            unlink_object_procedure_description = ProcedureDescription(
                input_schema=unlink_object_takes,
                output_schema=unlink_object_returns,
                description="Description for unlink_object entity-level procedure"
            )
            bucket.entity_procedure(
                    "unlink_object",
                    unlink_object_procedure_description,
                    unlink_object_handler
            )

            await sdk.register()

            global USER_S2S_KEY
            USER_S2S_KEY = await create_user_s2s_key(sdk)

            await cleanup()

            '''
            Test Scenario:
            test-bucket1
                - test-object1
                - test-object2

            test-bucket2
                - test-object1 (refers the test-bucket1.test-object2 object)
                - test-object2

            1. Create buckets test-bucket1 and test-bucket2
            2. Create object test-object1 and test-object2 inside test-bucket1
            3. Create object test-object2 inside test-bucket2
            4. Link object test-object1 inside test-bucket2 to test-object2 inside test-bucket1
            5. Unlink object test-object1 inside test-bucket2 (should affect test-bucket1.test-object2)
            6. Unlink test-object2 inside test-bucket1 (should delete test-bucket1.test-object2)
            '''
            async with EntityCRUD(
                PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, BUCKET_KIND, USER_S2S_KEY
            ) as bucket_entity_client:

                bucket1_name = "test-bucket1"
                bucket2_name = "test-bucket2"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket2_name)
                bucket2_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert bucket2_entity.spec.name == bucket2_name

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object2_name)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    b1_object2_entity = await object_entity_client.get(object_ref)

                assert b1_object2_entity.spec.references[0].object_name == object2_name
                assert b1_object2_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket2_entity.metadata, object2_name)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                assert b2_object2_entity.spec.references[0].object_name == object2_name
                assert b2_object2_entity.spec.references[0].bucket_reference.uuid == bucket2_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object2_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    b2_object1_entity = await object_entity_client.get(object_ref)

                assert b2_object1_entity.spec.references[1].object_name == object1_name
                assert b2_object1_entity.spec.references[1].bucket_reference.uuid == bucket2_entity.metadata.uuid

                object_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket2_entity.metadata, object_input)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    b1_object2_entity = await object_entity_client.get(object_ref)

                bucket2_entity = await bucket_entity_client.get(bucket_ref)

                assert len(b1_object2_entity.spec.references) == 1
                assert len(bucket2_entity.spec.objects) == 1

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object2_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)
                async with EntityCRUD(
                    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, OBJECT_KIND, USER_S2S_KEY
                ) as object_entity_client:
                    object_list = await object_entity_client.get_all()

                bucket1_entity = await bucket_entity_client.get(AttributeDict(uuid=bucket1_entity.metadata.uuid))

                assert len(object_list) == 2
                assert len(bucket1_entity.spec.objects) == 1

                await print_kinds_data()