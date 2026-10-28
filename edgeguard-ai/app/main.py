import logging
import os
import sys
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import SensorReading, PredictionResponse
from app.model_registry import load_latest_model
from app.telemetry import append_event, recent_events
from app.cloud import upload_model, send_telemetry, cloud_status
from scripts.train_model import train_and_register, FEATURES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("edgeguard")
app = FastAPI(title="EdgeGuard AI API", version="1.0.0",
              description="IoT predictive-maintenance inference API using a versioned scikit-learn model.")

model = None
metadata = None

@app.on_event("startup")
def startup():
    global model, metadata
    model, metadata = load_latest_model()
    if model is None:
        logger.info("No registered model found; downloading dataset and training first model.")
        model_path, metadata = train_and_register()
        model, _ = load_latest_model()
        if model is None:
            raise RuntimeError("Model training completed but registry load failed")
        upload_model(model_path, f"{metadata['version']}/model.joblib")
        logger.info("Model registered and loaded: %s", metadata["version"])
    else:
        logger.info("Loaded model: %s", metadata["version"])
        model_path = Path(os.getenv("MODEL_DIR", "models")) / "versions" / metadata["version"] / "model.joblib"
        upload_model(model_path, f"{metadata['version']}/model.joblib")

@app.get("/")
def root():
    return {"name": "EdgeGuard AI", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok" if model is not None else "starting",
            "model_loaded": model is not None,
            "model_version": metadata.get("version") if metadata else None,
            "cloud": cloud_status()}

@app.get("/model-info")
def model_info():
    if not metadata:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    return metadata

@app.post("/predict", response_model=PredictionResponse)
def predict(reading: SensorReading):
    if model is None or metadata is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    values = {
        "Air temperature [K]": reading.air_temperature_k,
        "Process temperature [K]": reading.process_temperature_k,
        "Rotational speed [rpm]": reading.rotational_speed_rpm,
        "Torque [Nm]": reading.torque_nm,
        "Tool wear [min]": reading.tool_wear_min
    }
    try:
        probability = float(model.predict_proba(pd.DataFrame([values], columns=FEATURES))[0][1])
        prediction = int(probability >= 0.5)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")
    risk = "HIGH" if probability >= 0.65 else ("MEDIUM" if probability >= 0.30 else "LOW")
    timestamp = datetime.now(timezone.utc).isoformat()
    result = {
        "timestamp": timestamp, "machine_id": reading.machine_id,
        "air_temperature_k": reading.air_temperature_k,
        "process_temperature_k": reading.process_temperature_k,
        "rotational_speed_rpm": reading.rotational_speed_rpm,
        "torque_nm": reading.torque_nm, "tool_wear_min": reading.tool_wear_min,
        "prediction": prediction,
        "prediction_label": "Potential failure" if prediction else "No failure predicted",
        "failure_probability": round(probability, 5), "risk_level": risk,
        "model_version": metadata["version"]
    }
    append_event(result)
    send_telemetry(result)
    return result

@app.get("/telemetry")
def telemetry(limit: int = 100):
    limit = max(1, min(limit, 1000))
    return {"count": len(recent_events(limit)), "events": recent_events(limit)}

@app.get("/cloud-status")
def cloud():
    return cloud_status()
