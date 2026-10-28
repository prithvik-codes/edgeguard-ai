from fastapi.testclient import TestClient
import app.main as main

def setup_module():
    # Avoid dataset downloads in unit tests; inject a deterministic fake model.
    class FakeModel:
        def predict_proba(self, rows):
            return [[0.2, 0.8]]
    main.model = FakeModel()
    main.metadata = {"version": "test-model", "metrics": {}}

def test_health():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is True

def test_prediction():
    client = TestClient(main.app)
    response = client.post("/predict", json={
        "machine_id": "test-001",
        "air_temperature_k": 310,
        "process_temperature_k": 320,
        "rotational_speed_rpm": 1400,
        "torque_nm": 50,
        "tool_wear_min": 200
    })
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == 1
    assert data["risk_level"] == "HIGH"
    assert data["model_version"] == "test-model"

def test_reject_invalid_sensor_range():
    client = TestClient(main.app)
    response = client.post("/predict", json={
        "machine_id": "test-002",
        "air_temperature_k": 999,
        "process_temperature_k": 320,
        "rotational_speed_rpm": 1400,
        "torque_nm": 50,
        "tool_wear_min": 200
    })
    assert response.status_code == 422
