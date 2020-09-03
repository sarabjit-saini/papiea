import os
from typing import Optional

import asyncio
import inflect
import pytest
import yaml

from papiea.python_sdk import ProviderSdk

SERVER_PORT = int(os.environ.get("SERVER_PORT", "3000"))
ADMIN_KEY = os.environ.get("PAPIEA_ADMIN_S2S_KEY", "")
PAPIEA_URL = "http://127.0.0.1:3000"

SERVER_CONFIG_HOST = "127.0.0.1"
SERVER_CONFIG_PORT = 9005

inflect_engine = inflect.engine()
location: Optional[dict] = None

with open("./test_data/location_kind_test_data.yml") as file:
    location = yaml.full_load(file)

'''
provider_api_admin
provider_api
entity_api
'''

class TestBasic:
    @pytest.mark.asyncio
    async def test_pluralize_words(self):
        assert inflect_engine.plural_noun("test")  == "tests"
        assert inflect_engine.plural_noun("provider") == "providers"
        # use of done callback??
        
    location_yaml = None
    location_array_yaml = None
    
    provider_version = "0.1.0"
    with open("./test_data/location_kind_test_data.yml") as file:
        location_yaml = yaml.full_load(file)
    with open("./test_data/location_kind_test_data_array.yml") as file:
        location_array_yaml = yaml.full_load(file)
    
    @pytest.mark.asyncio
    async def test_yaml_exists(self):
        assert self.location_yaml != None
        assert self.location_yaml["Location"] != None

    @pytest.mark.asyncio
    async def test_yaml_spec_only_and_properties(self):
        location_field = self.location_yaml["Location"]
        assert location_field["x-papiea-entity"] == "spec-only"
        props = location_field["properties"]
        assert props != None
        for prop in props:
            assert props[prop] != None

    @pytest.mark.asyncio
    async def test_empty_kind_yaml(self):
        async with ProviderSdk.create_provider(PAPIEA_URL, ADMIN_KEY, SERVER_CONFIG_HOST, SERVER_CONFIG_PORT) as sdk:
            with pytest.raises(Exception) as excinfo:
                sdk.new_kind({})
            assert str(excinfo.value) == "Wrong kind description specified"

    @pytest.mark.asyncio
    async def test_valid_kind_yaml(self):
        async with ProviderSdk.create_provider(PAPIEA_URL, ADMIN_KEY, SERVER_CONFIG_HOST, SERVER_CONFIG_PORT) as sdk:
            location_manager = sdk.new_kind(self.location_yaml)
            assert location_manager.kind["name"] == "Location"

'''
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
'''