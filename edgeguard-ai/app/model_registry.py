import json
import os
from pathlib import Path
import joblib

MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
REGISTRY_DIR = MODEL_DIR / "registry"
VERSIONS_DIR = MODEL_DIR / "versions"
LATEST_FILE = REGISTRY_DIR / "latest.json"

def latest_metadata():
    if not LATEST_FILE.exists():
        return None
    try:
        pointer = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
        meta_path = VERSIONS_DIR / pointer["version"] / "metadata.json"
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return None

def load_latest_model():
    metadata = latest_metadata()
    if not metadata:
        return None, None
    model_path = VERSIONS_DIR / metadata["version"] / "model.joblib"
    if not model_path.exists():
        return None, metadata
    return joblib.load(model_path), metadata

def register_model(model, metadata):
    version = metadata["version"]
    version_dir = VERSIONS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, version_dir / "model.joblib")
    (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    LATEST_FILE.write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")
    return version_dir / "model.joblib"
