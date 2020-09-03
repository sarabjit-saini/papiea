import os
from typing import Optional

import pytest
import yaml

from papiea.python_sdk import ProviderSdk

PAPIEA_URL = "http://127.0.0.1:3000"
ADMIN_KEY = os.environ.get("PAPIEA_ADMIN_S2S_KEY", "")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "3000"))

SERVER_CONFIG_HOST = "127.0.0.1"
SERVER_CONFIG_PORT = 9005

location: Optional[dict] = None

with open("./test_data/location_kind_test_data.yml") as file:
    location = yaml.full_load(file)


class TestBasic:
    @pytest.mark.asyncio
    async def test_register_provider(self):
        prefix = "python_location_provider"
        version = "0.1.0"
        async with ProviderSdk.create_provider(PAPIEA_URL, ADMIN_KEY, SERVER_CONFIG_HOST, SERVER_CONFIG_PORT) as sdk:
            sdk.prefix(prefix)
            sdk.version(version)
            sdk.new_kind(location)
            await sdk.register()
            await sdk.server.close()
