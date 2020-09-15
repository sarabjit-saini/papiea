import os
import asyncio
import logging
import pytest

from typing import Optional
from yaml import Loader as YamlLoader
from yaml import load as load_yaml

from papiea.client import EntityCRUD
from papiea.core import Action, ProcedureDescription, S2S_Key, Spec
from papiea.python_sdk import ProviderSdk
from papiea.utils import ref_type

SERVER_PORT = int(os.environ.get("SERVER_PORT", "3000"))
ADMIN_KEY = os.environ.get("PAPIEA_ADMIN_S2S_KEY", "")
PAPIEA_URL = os.getenv("PAPIEA_URL", "http://127.0.0.1:3000")
SERVER_CONFIG_HOST = "127.0.0.1"
SERVER_CONFIG_PORT = 9005
PROVIDER_VERSION = "0.1.0"
PROVIDER_ADMIN_S2S_KEY = "Sa8xaic9"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def load_yaml_from_file(filename):
    with open(filename) as f:
        return load_yaml(f, Loader=YamlLoader)

async def create_user_s2s_key(sdk: ProviderSdk):
        admin_security_api = sdk.provider_security_api

        the_key = S2S_Key(
            name="location provider some.user s2s key",
            user_info={"owner": "nitesh", "tenant": "ada14b27-c147-4aca-9b9f-7762f1f48426"},
        )

        new_s2s_key = await admin_security_api.create_key(the_key)
        user_security_api = sdk.new_security_api(new_s2s_key.key)
        await user_security_api.user_info()
        return new_s2s_key.key

class TestBasic:
    bucket_yaml = load_yaml_from_file("./kinds/bucket_kind.yml")
    object_yaml = load_yaml_from_file("./kinds/object_kind.yml")

    @pytest.mark.asyncio
    async def test_basic(self):
        logger.debug("Running")
        assert 1 == 1