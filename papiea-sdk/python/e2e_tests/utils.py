import time

import e2e_tests as papiea_test

from aiohttp import ClientSession

from papiea.core import AttributeDict, IntentfulStatus
from papiea.utils import json_loads_attrs

async def cleanup():
    async with papiea_test.get_client(papiea_test.OBJECT_KIND) as object_entity_client:
        try:
            object_list = await object_entity_client.get_all()
            for obj in object_list:
                await object_entity_client.delete(obj.metadata)
        except:
            raise

    async with papiea_test.get_client(papiea_test.BUCKET_KIND) as bucket_entity_client:
        try:
            bucket_list = await bucket_entity_client.get_all()
            for bucket in bucket_list:
                await bucket_entity_client.delete(bucket.metadata)
        except:
            raise

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