import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", ROOT / "models"))
RAW_DIR = DATA_DIR / "raw"
DATASET_URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
FEATURES = [
    "Air temperature [K]", "Process temperature [K]",
    "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"
]
TARGET = "Machine failure"

def find_dataset():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    csvs = list(RAW_DIR.glob("*.csv"))
    if csvs:
        for path in csvs:
            try:
                df = pd.read_csv(path, nrows=2)
                if TARGET in df.columns:
                    return path
            except Exception:
                continue
    zip_path = RAW_DIR / "ai4i_2020_dataset.zip"
    response = requests.get(DATASET_URL, timeout=60)
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    with zipfile.ZipFile(zip_path) as archive:
        candidates = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not candidates:
            raise RuntimeError("UCI archive did not contain a CSV file")
        chosen = next((n for n in candidates if "predictive" in n.lower()), candidates[0])
        with archive.open(chosen) as src:
            output = RAW_DIR / Path(chosen).name
            output.write_bytes(src.read())
    return output

def train_and_register():
    csv_path = find_dataset()
    df = pd.read_csv(csv_path)
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")
    df = df[FEATURES + [TARGET]].dropna()
    X = df[FEATURES]
    y = df[TARGET].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = Pipeline([
        ("classifier", RandomForestClassifier(
            n_estimators=250, random_state=42, class_weight="balanced_subsample",
            min_samples_leaf=2, n_jobs=-1
        ))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 5),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 5),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 5),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 5),
    }
    if y_test.nunique() == 2:
        metrics["roc_auc"] = round(float(roc_auc_score(y_test, prob)), 5)
    version = "rf-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version_dir = MODEL_DIR / "versions" / version
    version_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, version_dir / "model.joblib")
    metadata = {
        "version": version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "RandomForestClassifier",
        "dataset": "UCI AI4I 2020 Predictive Maintenance Dataset",
        "dataset_file": csv_path.name,
        "target": TARGET,
        "features": FEATURES,
        "rows_used": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics": metrics,
        "notes": "Public benchmark dataset; records are synthetic and not live industrial telemetry."
    }
    (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    registry_dir = MODEL_DIR / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "latest.json").write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    print(f"Registered model: {version_dir}")
    return version_dir / "model.joblib", metadata

if __name__ == "__main__":
    try:
        model_path, metadata = train_and_register()
    except Exception as exc:
        print(f"Training failed: {exc}", file=sys.stderr)
        raise
