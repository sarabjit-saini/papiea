import asyncio
import pytest
import time

import __tests__ as papiea_test
import __tests__.utils as utils
import __tests__.procedure_handlers as procedure_handlers

from typing import Optional

from papiea.client import EntityCRUD
from papiea.core import AttributeDict, ProcedureDescription, Spec
from papiea.python_sdk import ProviderSdk
from papiea.python_sdk_exceptions import ApiException, PapieaBaseException, SecurityApiError

# Includes all the entity ops related tests
class TestEntityOperations:

    @pytest.mark.asyncio
    async def test_new_bucket_create(self):
        papiea_test.logger.debug("Running test to create new unique bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_duplicate_bucket_create(self):
        papiea_test.logger.debug("Running test to create a duplicate bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_new_object_create(self):
        papiea_test.logger.debug("Running test to create a new unique object")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_duplicate_object_create(self):
        papiea_test.logger.debug("Running test to create a duplicate object in same bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.content == ""

                await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
        except Exception as ex:
            papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
            assert str(ex) == "Object already exists in the bucket"
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_different_bucket_different_name_link(self):
        papiea_test.logger.debug("Running test to link to different object in a different bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"
                bucket2_name = "test-bucket2"

                bucket1_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                bucket2_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket2_name)
                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0
                assert bucket2_entity.spec.name == bucket2_name
                assert len(bucket2_entity.spec.objects) == 0

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert len(bucket2_entity.spec.objects) == 1
                assert bucket2_entity.spec.objects[0].name == object2_name
                assert bucket2_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_different_bucket_same_name_link(self):
        papiea_test.logger.debug("Running test to link to same object in a different bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"
                bucket2_name = "test-bucket2"

                bucket1_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                bucket2_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket2_name)
                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0
                assert bucket2_entity.spec.name == bucket2_name
                assert len(bucket2_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert len(bucket2_entity.spec.objects) == 1
                assert bucket2_entity.spec.objects[0].name == object1_name
                assert bucket2_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_same_bucket_different_name_link(self):
        papiea_test.logger.debug("Running test to link to different object in the same bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 2
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_same_bucket_same_name_link(self):
        papiea_test.logger.debug("Running test to link to same object in the same bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
        except Exception as ex:
            papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
            assert str(ex) == "Object already exists in the bucket"
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_different_bucket_different_name_exists_link(self):
        papiea_test.logger.debug("Running test to link to different object in a different bucket, different object already exists in the bucket")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"
                bucket2_name = "test-bucket2"

                bucket1_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                bucket2_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket2_name)
                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0
                assert bucket2_entity.spec.name == bucket2_name
                assert len(bucket2_entity.spec.objects) == 0

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket1_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket2_entity.metadata, object2_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                bucket2_entity = await bucket_entity_client.get(bucket2_ref)

                assert len(bucket2_entity.spec.objects) == 1
                assert bucket2_entity.spec.objects[0].name == object2_name
                assert bucket2_entity.spec.objects[0].reference.uuid == b2_object2_entity.metadata.uuid
                assert b2_object2_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
        except Exception as ex:
            papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
            assert str(ex) == "Object already exists in the bucket"
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_non_existent_object_link(self):
        papiea_test.logger.debug("Running test to link to a non-existent object")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid="shouldfailuuid"
                )
                await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
        except Exception as ex:
            papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
            assert str(ex) == "Papiea exception: Entity not found."
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_object_unlink(self):
        papiea_test.logger.debug("Running test to unlink from a valid object")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 2
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid

                bucket_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_object_delete_unlink(self):
        papiea_test.logger.debug("Running test to unlink last reference for a valid object, delete the object")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                bucket_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 0
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_non_existent_object_unlink(self):
        papiea_test.logger.debug("Running test to unlink from a non-existing object")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid="shouldfailuuid"
                )
                await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)
        except Exception as ex:
            papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
            assert str(ex) == "Object not found in the bucket"
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_bucket_name_change_intent(self):
        papiea_test.logger.debug("Running test to change bucket name and validate intent resolver")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert len(bucket1_entity.spec.objects) == 1
                assert bucket1_entity.spec.objects[0].name == object1_name
                assert bucket1_entity.spec.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert b1_object1_entity.spec.content == ""

                retries = 10
                for _ in range(1, retries+1):
                    bucket1_entity = await bucket_entity_client.get(bucket_ref)
                    if len(bucket1_entity.status.objects) == 1:
                        break
                    time.sleep(5)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert len(bucket1_entity.status.objects) == 1
                assert bucket1_entity.status.objects[0].name == object1_name
                assert bucket1_entity.status.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert len(b1_object1_entity.status.references) == 1
                assert b1_object1_entity.status.references[0].bucket_name == bucket1_name
                assert b1_object1_entity.status.references[0].object_name == object1_name
                assert b1_object1_entity.status.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                new_bucket1_name = "new-test-bucket1"
                await bucket_entity_client.invoke_procedure("change_bucket_name", bucket1_entity.metadata, new_bucket1_name)

                for _ in range(1, retries+1):
                    bucket1_entity = await bucket_entity_client.get(bucket_ref)
                    if bucket1_entity.status.name == new_bucket1_name:
                        break
                    time.sleep(5)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert bucket1_entity.spec.name == new_bucket1_name
                assert bucket1_entity.status.name == new_bucket1_name
                assert len(b1_object1_entity.status.references) == 1
                assert b1_object1_entity.status.references[0].bucket_name == new_bucket1_name
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_object_add_bucket_intent(self):
        papiea_test.logger.debug("Running test to add object to bucket and validate intent resolver")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert b1_object1_entity.spec.content == ""

                retries = 10
                for _ in range(1, retries+1):
                    bucket1_entity = await bucket_entity_client.get(bucket_ref)
                    if len(bucket1_entity.status.objects) == 1:
                        break
                    time.sleep(5)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert len(bucket1_entity.status.objects) == 1
                assert bucket1_entity.status.objects[0].name == object1_name
                assert bucket1_entity.status.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert len(b1_object1_entity.status.references) == 1
                assert b1_object1_entity.status.references[0].bucket_name == bucket1_name
                assert b1_object1_entity.status.references[0].object_name == object1_name
                assert b1_object1_entity.status.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_object_remove_bucket_intent(self):
        papiea_test.logger.debug("Running test to remove object from bucket and validate intent resolver")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert b1_object1_entity.spec.content == ""

                retries = 10
                for _ in range(1, retries+1):
                    bucket1_entity = await bucket_entity_client.get(bucket_ref)
                    if len(bucket1_entity.status.objects) == 1:
                        break
                    time.sleep(5)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert len(bucket1_entity.status.objects) == 1
                assert bucket1_entity.status.objects[0].name == object1_name
                assert bucket1_entity.status.objects[0].reference.uuid == b1_object1_entity.metadata.uuid
                assert len(b1_object1_entity.status.references) == 1
                assert b1_object1_entity.status.references[0].bucket_name == bucket1_name
                assert b1_object1_entity.status.references[0].object_name == object1_name
                assert b1_object1_entity.status.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                bucket_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)

                for _ in range(1, retries+1):
                    bucket1_entity = await bucket_entity_client.get(bucket_ref)
                    if len(bucket1_entity.status.objects) == 0:
                        break
                    time.sleep(5)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    object_list = await object_entity_client.get_all()

                assert len(bucket1_entity.spec.objects) == 0
                assert len(bucket1_entity.status.objects) == 0
                assert len(object_list) == 0
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_object_content_change_intent(self):
        papiea_test.logger.debug("Running test to change object content and validate intent resolver")

        try:
            server = await utils.setup_and_register_sdk()
        except Exception as ex:
            papiea_test.logger.debug("Failed to setup/register sdk : " + str(ex))
            return

        try:
            async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert len(bucket1_entity.spec.objects) == 0

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                    bucket1_entity = await bucket_entity_client.get(bucket_ref)

                    assert b1_object1_entity.spec.content == ""

                    obj_content = "test-content"
                    spec = Spec(
                        content=obj_content
                    )
                    watcher_ref = await object_entity_client.update(b1_object1_entity.metadata, spec)
                    op_status = await utils.wait_for_diff_resolver(watcher_ref.watcher)
                    if op_status == True:
                        b1_object1_entity = await object_entity_client.get(object_ref)

                        assert b1_object1_entity.spec.content == obj_content
                        assert b1_object1_entity.status.content == obj_content
                        assert b1_object1_entity.status.size == len(obj_content)
                        assert len(b1_object1_entity.status.references) == 1
                        assert b1_object1_entity.status.references[0].bucket_name == bucket1_name
                        assert b1_object1_entity.status.references[0].object_name == object1_name
                        assert b1_object1_entity.status.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid
                    else:
                        papiea_test.logger.debug("Intent resolver operation failed")
                        assert False
        finally:
            await server.close()