import json
from pathlib import Path
import joblib
from app.model_registry import register_model

class DummyModel:
    pass

def test_register_model_writes_metadata_and_latest(tmp_path, monkeypatch):
    import app.model_registry as registry
    monkeypatch.setattr(registry, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path / "registry")
    monkeypatch.setattr(registry, "VERSIONS_DIR", tmp_path / "versions")
    monkeypatch.setattr(registry, "LATEST_FILE", tmp_path / "registry" / "latest.json")
    metadata = {"version": "test-v1", "metrics": {"f1": 0.5}}
    path = register_model(DummyModel(), metadata)
    assert path.exists()
    assert json.loads(registry.LATEST_FILE.read_text())["version"] == "test-v1"
    assert (tmp_path / "versions" / "test-v1" / "metadata.json").exists()
