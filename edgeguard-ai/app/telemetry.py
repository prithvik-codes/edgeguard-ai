import csv
import json
import os
from pathlib import Path
from threading import Lock

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
CSV_PATH = LOG_DIR / "telemetry.csv"
_lock = Lock()
FIELDS = [
    "timestamp", "machine_id", "air_temperature_k", "process_temperature_k",
    "rotational_speed_rpm", "torque_nm", "tool_wear_min", "prediction",
    "prediction_label", "failure_probability", "risk_level", "model_version"
]

def append_event(event: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        exists = CSV_PATH.exists()
        with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            if not exists:
                writer.writeheader()
            writer.writerow(event)

def recent_events(limit=250):
    if not CSV_PATH.exists():
        return []
    with _lock:
        with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows[-limit:]

def event_json(event: dict):
    return json.dumps(event, separators=(",", ":"))
