import logging
import os
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

logger = logging.getLogger(__name__)

ACCOUNT = os.getenv("AZURE_ACCOUNT_NAME", "devstoreaccount1")
KEY = os.getenv("AZURE_ACCOUNT_KEY", "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==")
BASE = os.getenv("FLoci_AZ_BASE_URL", "http://host.docker.internal:4577").rstrip("/")
ENABLED = os.getenv("AZURE_CLOUD_ENABLED", "true").lower() in ("1", "true", "yes")
BLOB_CONTAINER = "edgeguard-artifacts"
QUEUE_NAME = "edgeguard-telemetry"

def _blob_connection_string():
    return (
        f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT};AccountKey={KEY};"
        f"BlobEndpoint={BASE}/{ACCOUNT};"
    )

def _queue_connection_string():
    return (
        f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT};AccountKey={KEY};"
        f"QueueEndpoint={BASE}/{ACCOUNT}-queue;"
    )

def upload_model(model_path, blob_name=None):
    if not ENABLED:
        return False
    try:
        service = BlobServiceClient.from_connection_string(_blob_connection_string())
        container = service.get_container_client(BLOB_CONTAINER)
        try:
            container.create_container()
        except Exception:
            pass
        blob_name = blob_name or model_path.name
        with open(model_path, "rb") as f:
            container.upload_blob(name=blob_name, data=f, overwrite=True)
        logger.info("Floci Blob upload succeeded: %s/%s", BLOB_CONTAINER, blob_name)
        return True
    except Exception as exc:
        logger.warning("Floci Blob upload skipped/failed: %s", exc)
        return False

def send_telemetry(event):
    if not ENABLED:
        return False
    try:
        service = QueueServiceClient.from_connection_string(_queue_connection_string())
        queue = service.get_queue_client(QUEUE_NAME)
        try:
            queue.create_queue()
        except Exception:
            pass
        queue.send_message(__import__("json").dumps(event, separators=(",", ":")))
        logger.info("Floci Queue message sent: %s", QUEUE_NAME)
        return True
    except Exception as exc:
        logger.warning("Floci Queue write skipped/failed: %s", exc)
        return False

def cloud_status():
    if not ENABLED:
        return {"enabled": False, "endpoint": BASE}
    try:
        import requests
        r = requests.get(f"{BASE}/_floci/health", timeout=2)
        return {"enabled": True, "reachable": r.ok, "endpoint": BASE, "status_code": r.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "endpoint": BASE, "error": str(exc)}
