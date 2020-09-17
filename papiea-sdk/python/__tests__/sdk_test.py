import os
import asyncio
import logging
import pytest

from datetime import datetime
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

BUCKET_KIND = "bucket"
OBJECT_KIND = "object"

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
    global bucket_kind, object_kind
    global metadata_extension
    global ensure_bucket_exists_takes, ensure_bucket_exists_returns

    bucket_kind = load_yaml_from_file("./kinds/bucket_kind.yml")
    object_kind = load_yaml_from_file("./kinds/object_kind.yml")
    
    metadata_extension = load_yaml_from_file("./security/metadata_extension.yml")

    ensure_bucket_exists_takes = load_yaml_from_file("./procedures/ensure_bucket_exists_input.yml")
    ensure_bucket_exists_returns = load_yaml_from_file("./procedures/ensure_bucket_exists_output.yml")
    
    bucket_kind.get('bucket').get('properties').get('objects').get('items') \
        .get('properties')['reference'] = ref_type(OBJECT_KIND, 'Reference of the objects within the bucket')
    
    object_kind.get('object').get('properties').get('references').get('items') \
        .get('properties')['bucket_reference'] = ref_type(BUCKET_KIND, 'Reference of the bucket in which the object exists')

    ensure_bucket_exists_returns['EnsureBucketExistsOutput'] = ref_type(BUCKET_KIND, 'Reference of the bucket created/found')

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

async def ensure_bucket_exists_handler(ctx, input_bucket_name):
    # Run get query to obtain the list of buckets
    # Check if bucket_name exists in the bucket list
    # If true, simply return the bucket
    # Else, create a new bucket with input_bucket_name and return
    # TODO: Use the filter function instead of get_all to verify existence

    b_kind = EntityReference(
        kind=BUCKET_KIND
    )
    async with ctx.entity_client_for_user(b_kind) as entity_client:
        bucket_list = await entity_client.get_all()
        for bucket in bucket_list:
            if bucket.spec.name == input_bucket_name:
                logger.debug("Bucket already exists. Returning it...")
                return EntityReference(
                    uuid=bucket.metadata.uuid,
                    kind=bucket.metadata.kind
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
    # TODO: Use the filter function to find if object name already exists

    objects_list = entity_bucket.spec.objects
    if not any(obj.name == input_object_name for obj in objects_list):

        async with ctx.entity_client_for_user({'kind': OBJECT_KIND}) as entity_client:
            entity_object = await entity_client.create(
                Spec(content="", size=0, lat_modified=datetime.utcnow(), references=
                    [{'object_name': input_object_name, 'bucket_reference': {'uuid': entity_bucket.metadata.uuid, 'kind': BUCKET_KIND}}])
            )
        
        entity_bucket.spec.objects.append({'name':input_object_name, 'reference': {'uuid': entity_object.metadata.uuid, 'kind': OBJECT_KIND}})
        async with ctx.entity_client_for_user({'kind': BUCKET_KIND}) as entity_client:
            await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )
        
        return {'uuid': entity_object.metadata.uuid, 'kind': entity_object.metadata.kind}
    else:
        return None
    return None

async def link_object_handler(ctx, entity_bucket, input):
    # assuming input to be the object name and the uid
    # check if the name already exist in the objects list
    # if exists, return None/failure
    # else add object name and bucket uid in object' references list and
    # add object name and uid in bucket' objects list
    # TODO: Use the filter function to find if object name already exists

    objects_list = entity_bucket.spec.objects
    if not any(obj.name == input.object_name for obj in objects_list):

        entity_bucket.spec.objects.append({'name':input.object_name, 'reference': {'uuid': input.object_uuid, 'kind': OBJECT_KIND}})
        async with ctx.entity_client_for_user({'kind': BUCKET_KIND}) as entity_client:
            ret_entity = await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )

        async with ctx.entity_client_for_user({'kind': OBJECT_KIND}) as entity_client:
            entity_object = await entity_client.get({'uuid': input.object_uuid})
            entity_object.spec.references.append({'object_name': input.object_name, 'bucket_reference': {'uuid': entity_bucket.metadata.uuid, 'kind': BUCKET_KIND}})
            await entity_client.update(
                metadata=entity_object.metadata,
                spec=entity_object.spec
            )

        return {'uuid': ret_entity.metadata.uuid, 'kind': ret_entity.metadata.kind}
    else:
        return None
    
    return None

async def unlink_object_handler(ctx, entity_bucket, input):
    # assuming input to be the object name and the uid
    # check if the name exists in the object list
    # if does not exists, return None/failure
    # else remove the object name and reference from the objects list and
    # remove the object name and bucket reference from the object' references list
    # if the object' references list become empty, delete the object entity
    # TODO: Use the filter function to find if object name exists

    objects_list = entity_bucket.spec.objects
    if any(obj.name == input.object_name for obj in objects_list):
        
        entity_bucket.spec.objects[:] = [d for d in entity_bucket.spec.objects if d.get('name') != input.object_name]
        async with ctx.entity_client_for_user({'kind': BUCKET_KIND}) as entity_client:
            ret_entity = await entity_client.update(
                metadata=entity_bucket.metadata,
                spec=entity_bucket.spec
            )

        async with ctx.entity_client_for_user({'kind': OBJECT_KIND}) as entity_client:
            entity_object = await entity_client.get({'uuid': input.object_uuid})
            entity_object.spec.references[:] = [d for d in entity_object.spec.objects
                if d.get('object_name') != input.object_name or d.get('bucket_reference') != {'uuid': entity_bucket.metadata.uuid, 'kind': BUCKET_KIND}]

            if not entity_object.spec.references:
                await entity_client.delete(entity_object.metadata)
            else:
                await entity_client.update(
                    metadata=entity_object.metadata,
                    spec=entity_object.spec
                )

        return {'uuid': ret_entity.metadata.uuid, 'kind': ret_entity.metadata.kind}
    else:
        return None

    return None

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

            bucket = sdk.new_kind(bucket_kind)
            # bucket.on_create(bucket_constructor)

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

            await sdk.register()
            
            global USER_S2S_KEY
            USER_S2S_KEY = await create_user_s2s_key(sdk)
            async with EntityCRUD(
                PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, BUCKET_KIND, USER_S2S_KEY
            ) as entity_client:

                bucket1_name = "test-bucket1"

                bucket_ref = await entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket_entity = await entity_client.get(bucket_ref)

            assert bucket_entity.spec.name == bucket1_name