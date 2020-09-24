import logging
import os

from papiea.client import EntityCRUD

SERVER_PORT = int(os.environ.get("SERVER_PORT", "3000"))
PAPIEA_ADMIN_S2S_KEY = os.environ.get("PAPIEA_ADMIN_S2S_KEY", "")
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

get_client = lambda kind : EntityCRUD(
    PAPIEA_URL, PROVIDER_PREFIX, PROVIDER_VERSION, kind, USER_S2S_KEY
)