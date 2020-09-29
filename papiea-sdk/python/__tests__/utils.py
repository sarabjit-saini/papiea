import json
import time

from aiohttp import ClientSession
from yaml import Loader as YamlLoader
from yaml import load as load_yaml

import __tests__ as papiea_test
import __tests__.procedure_handlers as procedure_handlers

from papiea.client import EntityCRUD
from papiea.core import AttributeDict, IntentfulStatus, Key, ProcedureDescription, S2S_Key
from papiea.python_sdk import ProviderSdk, ProviderServerManager
from papiea.python_sdk_exceptions import ApiException, PapieaBaseException, SecurityApiError
from papiea.utils import json_loads_attrs, ref_type

def load_yaml_from_file(filename):
    with open(filename) as f:
        return load_yaml(f, Loader=YamlLoader)

def setup_kinds():
    global bucket_kind_dict, object_kind_dict
    global bucket_yaml, object_yaml
    global metadata_extension
    global ensure_bucket_exists_takes, ensure_bucket_exists_returns
    global change_bucket_name_takes, change_bucket_name_returns
    global create_object_takes, create_object_returns
    global link_object_takes, link_object_returns
    global unlink_object_takes, unlink_object_returns

    bucket_kind_dict = AttributeDict(kind=papiea_test.BUCKET_KIND)
    object_kind_dict = AttributeDict(kind=papiea_test.OBJECT_KIND)

    bucket_yaml = load_yaml_from_file("./kinds/bucket_kind.yml")
    object_yaml = load_yaml_from_file("./kinds/object_kind.yml")

    bucket_yaml.get("bucket").get("properties").get("objects").get("items") \
        .get("properties")["reference"] = ref_type(papiea_test.OBJECT_KIND, "Reference of the objects within the bucket")

    object_yaml.get("object").get("properties").get("references").get("items") \
        .get("properties")["bucket_reference"] = ref_type(papiea_test.BUCKET_KIND, "Reference of the bucket in which the object exists")

    metadata_extension = load_yaml_from_file("./security/metadata_extension.yml")

    ensure_bucket_exists_takes = load_yaml_from_file("./procedures/ensure_bucket_exists_input.yml")
    ensure_bucket_exists_returns = AttributeDict(
        EnsireBucketExistsOutput=ref_type(papiea_test.BUCKET_KIND, "Reference of the bucket created/found")
    )

    change_bucket_name_takes = load_yaml_from_file("./procedures/change_bucket_name.yml")
    change_bucket_name_returns = AttributeDict(
        ChangeBucketNameOutput=ref_type(papiea_test.BUCKET_KIND, "Reference of the bucket with new name"),
    )
    change_bucket_name_returns.get("ChangeBucketNameOutput").get("properties") \
        ["message"] = AttributeDict(type="string", description="Error message")

    create_object_takes = load_yaml_from_file("./procedures/create_object_input.yml")
    create_object_returns = AttributeDict(
        CreateObjectOutput=ref_type(papiea_test.OBJECT_KIND, "Reference of the object created"),
    )
    create_object_returns.get("CreateObjectOutput").get("properties") \
        ["message"] = AttributeDict(type="string", description="Error message")

    link_object_takes = load_yaml_from_file("./procedures/link_object_input.yml")
    link_object_returns = AttributeDict(
        LinkObjectOutput=ref_type(papiea_test.OBJECT_KIND, "Reference of the object to which it is linked")
    )
    link_object_returns.get("LinkObjectOutput").get("properties") \
        ["message"] = AttributeDict(type="string", description="Error message")

    unlink_object_takes = load_yaml_from_file("./procedures/unlink_object_input.yml")
    unlink_object_returns = AttributeDict(
        UnlinkObjectOutput=ref_type(papiea_test.BUCKET_KIND, "Reference of the bucket from which the object was removed")
    )
    unlink_object_returns.get("UnlinkObjectOutput").get("properties") \
        ["message"] = AttributeDict(type="string", description="Error message")

async def create_provider_admin_s2s_key(sdk: ProviderSdk, new_key: Key):
    admin_security_api = sdk.provider_security_api

    the_key = S2S_Key(
        name="Test provider admin S2S key",
        owner="nitesh.idnani@nutanix.com",
        key=new_key,
        user_info={"is_provider_admin": True},
    )

    try:
        keys = await admin_security_api.list_keys()
        for key in keys:
            if key.name == the_key.name:
                papiea_test.logger.debug(f"Key {the_key.name} already exists")
                return
    except SecurityApiError as err:
        raise SecurityApiError.from_error(err, str(err))

    try:
        await admin_security_api.create_key(the_key)
        provider_admin_security_api = sdk.new_security_api(new_key)
        await provider_admin_security_api.user_info()
        # papiea_test.logger.debug(f"User info {user_info}")
    except SecurityApiError as err:
        raise SecurityApiError.from_error(err, str(err))

async def create_user_s2s_key(sdk: ProviderSdk):
    admin_security_api = sdk.provider_security_api

    the_key = S2S_Key(
        name="test provider some.user s2s key",
        user_info={"owner": "nutanix"},
    )

    try:
        new_s2s_key = await admin_security_api.create_key(the_key)
        user_security_api = sdk.new_security_api(new_s2s_key.key)
        await user_security_api.user_info()
        return new_s2s_key.key
    except SecurityApiError as err:
        raise SecurityApiError.from_error(err, str(err))

async def cleanup():
    async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
        try:
            bucket_list = await bucket_entity_client.get_all()
            for bucket in bucket_list:
                await bucket_entity_client.delete(bucket.metadata)
        except PapieaBaseException as papiea_exception:
            raise papiea_exception
        except ApiException as api_exception:
            raise api_exception
        except Exception as ex:
            raise ex

    async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
        try:
            object_list = await object_entity_client.get_all()
            for obj in object_list:
                await object_entity_client.delete(obj.metadata)
        except PapieaBaseException as papiea_exception:
            raise papiea_exception
        except ApiException as api_exception:
            raise api_exception
        except Exception as ex:
            raise ex

async def print_kinds_data():
    async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
        try:
            print(await bucket_entity_client.get_all())
        except:
            papiea_test.logger.debug("Failed to fetch the buckets")
            pass
    async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
        try:
            print(await object_entity_client.get_all())
        except:
            papiea_test.logger.debug("Failed to fetch the objects")
            pass

async def setup_and_register_sdk() -> ProviderServerManager:

    setup_kinds()

    async with ProviderSdk.create_provider(
        papiea_test.PAPIEA_URL, papiea_test.PAPIEA_ADMIN_S2S_KEY, papiea_test.SERVER_CONFIG_HOST, papiea_test.SERVER_CONFIG_PORT, logger=papiea_test.logger
    ) as sdk:
        sdk.version(papiea_test.PROVIDER_VERSION)
        sdk.prefix(papiea_test.PROVIDER_PREFIX)

        # TODO: Add security policy to set the secure_with parameters
        sdk.metadata_extension(metadata_extension)
        try:
            await create_provider_admin_s2s_key(sdk, papiea_test.PROVIDER_ADMIN_S2S_KEY)
        except SecurityApiError as err:
            raise Exception(str(err))

        try:
            bucket = sdk.new_kind(bucket_yaml)
        except Exception as ex:
            raise ex
        bucket.on_create(procedure_handlers.bucket_create_handler)

        try:
            obj = sdk.new_kind(object_yaml)
        except Exception as ex:
            raise ex
        obj.on_create(procedure_handlers.object_create_handler)

        bucket.on("name", procedure_handlers.bucket_name_handler)
        bucket.on("objects.+{name}", procedure_handlers.on_object_added)
        bucket.on("objects.-{name}", procedure_handlers.on_object_removed)

        obj.on("content", procedure_handlers.object_content_handler)

        ensure_bucket_exists_procedure_description = ProcedureDescription(
            input_schema=ensure_bucket_exists_takes,
            output_schema=ensure_bucket_exists_returns,
            description="Description for ensure_bucket_exists kind-level procedure"
        )
        bucket.kind_procedure(
            "ensure_bucket_exists",
            ensure_bucket_exists_procedure_description,
            procedure_handlers.ensure_bucket_exists_handler
        )

        change_bucket_name_procedure_description = ProcedureDescription(
            input_schema=change_bucket_name_takes,
            output_schema=change_bucket_name_returns,
            description="Description for change_bucket_name entity-level procedure"
        )
        bucket.entity_procedure(
            "change_bucket_name",
            change_bucket_name_procedure_description,
            procedure_handlers.change_bucket_name_handler
        )

        create_object_procedure_description = ProcedureDescription(
            input_schema=create_object_takes,
            output_schema=create_object_returns,
            description="Description for create_object entity-level procedure"
        )
        bucket.entity_procedure(
                "create_object",
                create_object_procedure_description,
                procedure_handlers.create_object_handler
        )

        link_object_procedure_description = ProcedureDescription(
            input_schema=link_object_takes,
            output_schema=link_object_returns,
            description="Description for link_object entity-level procedure"
        )
        bucket.entity_procedure(
                "link_object",
                link_object_procedure_description,
                procedure_handlers.link_object_handler
        )

        unlink_object_procedure_description = ProcedureDescription(
            input_schema=unlink_object_takes,
            output_schema=unlink_object_returns,
            description="Description for unlink_object entity-level procedure"
        )
        bucket.entity_procedure(
                "unlink_object",
                unlink_object_procedure_description,
                procedure_handlers.unlink_object_handler
        )

        try:
            await sdk.register()
        except Exception as ex:
            raise ex

        try:
            papiea_test.USER_S2S_KEY = await create_user_s2s_key(sdk)
        except SecurityApiError as err:
            raise Exception(str(err))

        try:
            await cleanup()
        except PapieaBaseException as papiea_exception:
            papiea_test.logger.debug("Failed cleanup : " + str(papiea_exception))
            raise Exception("Cleanup operation failed")
        except ApiException as api_exception:
            papiea_test.logger.debug("Failed cleanup : " + str(api_exception))
            raise Exception("Cleanup operation failed")
        except Exception as ex:
            papiea_test.logger.debug("Failed cleanup : " + str(ex))
            raise Exception("Cleanup operation failed")

        return sdk.server

async def get_intent_watcher(id: str, headers: dict = {}):
    try:
        async with ClientSession() as session:
            async with session.get(
                f"{ papiea_test.PAPIEA_URL }/services/intent_watcher/{ id }",
                headers=headers
            ) as resp:
                res = await resp.text()
                if res == "":
                    return None
                return json_loads_attrs(res)
    except Exception as ex:
        papiea_test.logger.debug("Failed to get intent watcher : " + str(ex))
        return None

async def wait_for_diff_resolver(watcher: AttributeDict, retries: int = 10) -> bool:
    try:
        for _ in range(1, retries+1):
            watcher = await get_intent_watcher(watcher.uuid)
            if watcher.status == IntentfulStatus.Completed_Successfully:
                return True
            time.sleep(5)
    except:
        return False
    return False