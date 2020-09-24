import asyncio
import pytest

import __tests__ as papiea_test
import __tests__.utils as utils
import __tests__.procedure_handlers as procedure_handlers

from typing import Optional

from papiea.client import EntityCRUD
from papiea.core import AttributeDict, ProcedureDescription
from papiea.python_sdk import ProviderSdk
from papiea.python_sdk_exceptions import ApiException, PapieaBaseException, SecurityApiError
from papiea.utils import json_loads_attrs

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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:

            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
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
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                assert b2_object2_entity.spec.references[1].object_name == object2_name
                assert b2_object2_entity.spec.references[1].bucket_reference.uuid == bucket2_entity.metadata.uuid
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"
                bucket2_name = "test-bucket2"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket2_name)
                bucket2_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name
                assert bucket2_entity.spec.name == bucket2_name

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket2_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                assert b2_object2_entity.spec.references[1].object_name == object1_name
                assert b2_object2_entity.spec.references[1].bucket_reference.uuid == bucket2_entity.metadata.uuid
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object2_entity = await object_entity_client.get(object_ref)

                assert b1_object2_entity.spec.references[1].object_name == object2_name
                assert b1_object2_entity.spec.references[1].bucket_reference.uuid == bucket1_entity.metadata.uuid
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
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
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket2_entity.metadata, object2_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                assert b2_object2_entity.spec.references[0].object_name == object2_name
                assert b2_object2_entity.spec.references[0].bucket_reference.uuid == bucket2_entity.metadata.uuid

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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:

            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid="shouldfailuuid"
                )
                await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
                assert str(ex) == "Object not found in the bucket"
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"
                object2_name = "test-object2"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object2_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("link_object", bucket1_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b2_object2_entity = await object_entity_client.get(object_ref)

                assert b2_object2_entity.spec.references[1].object_name == object2_name
                assert b2_object2_entity.spec.references[1].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object2_entity = await object_entity_client.get(object_ref)

                bucket2_entity = await bucket_entity_client.get(bucket_ref)

                assert len(b1_object2_entity.spec.references) == 1
                assert len(bucket2_entity.spec.objects) == 1
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

                object1_name = "test-object1"

                object_ref = await bucket_entity_client.invoke_procedure("create_object", bucket1_entity.metadata, object1_name)
                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    b1_object1_entity = await object_entity_client.get(object_ref)

                assert b1_object1_entity.spec.references[0].object_name == object1_name
                assert b1_object1_entity.spec.references[0].bucket_reference.uuid == bucket1_entity.metadata.uuid

                object_input = AttributeDict(
                    object_name=object1_name,
                    object_uuid=b1_object1_entity.metadata.uuid
                )
                object_ref = await bucket_entity_client.invoke_procedure("unlink_object", bucket1_entity.metadata, object_input)

                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
                    object_list = await object_entity_client.get_all()

                assert len(bucket1_entity.spec.objects) == 0
                assert len(object_list) == 0
            except Exception as ex:
                papiea_test.logger.debug("Failed to perform entity operation : " + str(ex))
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

        async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
            try:
                bucket1_name = "test-bucket1"

                bucket_ref = await bucket_entity_client.invoke_kind_procedure("ensure_bucket_exists", bucket1_name)
                bucket1_entity = await bucket_entity_client.get(bucket_ref)

                assert bucket1_entity.spec.name == bucket1_name

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