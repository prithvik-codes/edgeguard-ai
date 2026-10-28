# EdgeGuard AI — IoT Predictive Maintenance

A local-first MLOps project for Windows 11, Docker Compose, FastAPI, Streamlit, scikit-learn, and Floci AZ.

## What it does
- Downloads the public UCI AI4I 2020 Predictive Maintenance dataset.
- Trains a Random Forest classifier and saves versioned model artifacts plus registry metadata.
- Serves predictions through FastAPI.
- Simulates IoT telemetry by sending sensor readings to the API.
- Displays live/recent readings and failure-risk predictions in Streamlit.
- Optionally mirrors model artifacts and telemetry events to Floci AZ Blob Storage and Queue Storage.
- Includes automated tests and a GitHub Actions CI workflow.

> This is a student/demo system, not a safety-critical industrial monitoring system. Model scores are not a guarantee of real-world failure.

## Architecture
`AI4I dataset -> train.py -> models/registry -> FastAPI /predict -> telemetry.csv -> Streamlit dashboard`
`                                                       |-> Floci AZ Blob + Queue (optional)`

## Requirements
- Windows 11
- Docker Desktop with Linux containers
- Floci AZ reachable at `http://localhost:4577`
- Internet for the first dataset download and container image/package downloads

No Azure subscription or paid service is used.

## 1. Check Floci AZ
In PowerShell:
```powershell
Invoke-RestMethod http://localhost:4577/_floci/health
```
Expected: JSON with `"status": "UP"`. If it is not running, start your existing Floci AZ container; don't start a second container on port 4577.

## 2. Create project folders
Extract the ZIP, then:
```powershell
cd edgeguard-ai
Copy-Item .env.example .env
```

## 3. Train the model (recommended first run)
Training happens inside the API image at container startup if no registered model exists. To train locally instead:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts\train_model.py
```
Python 3.11 or 3.12 is recommended for broad package compatibility. Local training downloads the dataset to `data/raw/`.

## 4. Start the application
```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f api
```
Open:
- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Model metadata: http://localhost:8000/model-info
- Floci AZ health: http://localhost:4577/_floci/health

First build can take a few minutes. API startup downloads the dataset and trains a model if no model registry entry exists. Keep the terminal online until the API logs say it is ready.

## 5. Test it
```powershell
docker compose exec api pytest -q
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body '{"machine_id":"demo-001","air_temperature_k":310.0,"process_temperature_k":320.0,"rotational_speed_rpm":1380,"torque_nm":60.0,"tool_wear_min":220}'
```
The result is a model prediction; the exact risk depends on the trained model. A high-risk test payload is only for demonstration, not a guaranteed failure.

## 6. Verify Floci cloud integration
The API attempts to create the `edgeguard-artifacts` blob container and `edgeguard-telemetry` queue, then uploads a model artifact and sends telemetry messages. Cloud writes are best-effort: predictions continue if Floci is unavailable.

From Windows, Floci uses `localhost:4577`; from a Compose container, use `host.docker.internal:4577`. Check API logs for `Floci Blob upload succeeded` or a warning. Floci AZ is an emulator, not a real Azure subscription.

If you already run Floci AZ outside this Compose project, keep it running and do not add a second Floci service to `docker-compose.yml`.

## 7. Send one manual sensor event
```powershell
$payload = @{
  machine_id = "manual-001"
  air_temperature_k = 300.0
  process_temperature_k = 310.0
  rotational_speed_rpm = 1500
  torque_nm = 40.0
  tool_wear_min = 80
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body $payload
```

## 8. Stop and reset
```powershell
docker compose down
```
Data in `data/`, `models/`, and `logs/` is bind-mounted and persists. To retrain, stop the stack and remove the local registry/model artifacts before starting it again:
```powershell
docker compose down
Remove-Item .\models\registry\latest.json -ErrorAction SilentlyContinue
Remove-Item .\models\versions\* -Recurse -Force -ErrorAction SilentlyContinue
docker compose up --build -d
```
Do not delete `data/raw/` unless you want the dataset downloaded again.

## Project structure
```text
edgeguard-ai/
├── app/
│   ├── main.py                 # FastAPI API
│   ├── schemas.py              # Request/response models
│   ├── model_registry.py       # Versioned model registry
│   ├── cloud.py                # Floci AZ Blob/Queue integration
│   ├── telemetry.py            # Local CSV history
│   └── dashboard.py            # Streamlit dashboard
├── scripts/
│   └── train_model.py           # Dataset download, training, evaluation, registration
├── tests/
│   ├── test_api.py
│   └── test_registry.py
├── data/raw/                    # Downloaded public dataset
├── models/versions/             # Versioned model artifacts
├── models/registry/              # latest.json metadata pointer
├── logs/
├── Dockerfile
├── Dockerfile.dashboard
├── docker-compose.yml
├── requirements.txt
└── .github/workflows/ci.yml
```

## ML details
- Dataset: UCI AI4I 2020 Predictive Maintenance Dataset (10,000 synthetic industrial records based on a real-world predictive-maintenance scenario).
- Target: `Machine failure`.
- Features: air temperature, process temperature, rotational speed, torque, tool wear.
- Model: Random Forest classifier with class weighting to help with the imbalanced target.
- Evaluation: stratified train/test split, precision, recall, F1, ROC-AUC when both classes occur.
- Registry: timestamped version folder, `model.joblib`, `metadata.json`, and `models/registry/latest.json`.

The dataset itself is synthetic but is a publicly available benchmark. State this accurately in the report.

## Report outline
1. Title page and team/student details.
2. Abstract and problem statement.
3. Objectives and scope.
4. Dataset source, fields, target imbalance, and data-preparation steps.
5. System architecture and workflow diagram.
6. Model choice, train/test strategy, metrics, and limitations.
7. API endpoints and request/response examples.
8. IoT simulator design and message flow.
9. Floci AZ integration: Blob Storage for model artifacts; Queue Storage for telemetry events.
10. Docker/DevOps workflow, tests, CI, and reproducibility.
11. Screenshots and results.
12. Limitations, future enhancements, conclusion.
13. References: UCI AI4I dataset page and Floci AZ documentation.

## Screenshot checklist
Capture your own screenshots after running:
- `docker compose ps` showing services running.
- API `/docs` page with `/predict`, `/health`, `/model-info`.
- `/health` JSON response.
- `/model-info` JSON showing model version and evaluation metrics.
- Streamlit dashboard with recent telemetry and prediction counts.
- API logs showing a sensor event and (if available) Floci Blob/Queue write.
- Floci health endpoint at `http://localhost:4577/_floci/health`.
- `pytest -q` passing.
- GitHub Actions workflow passing (after pushing to your repository).

## Five-minute demo script
- 0:00–0:30 — State the problem: machine downtime and predictive maintenance.
- 0:30–1:00 — Show architecture and explain the UCI benchmark dataset.
- 1:00–1:40 — Show Docker Compose services and `/health` plus `/model-info`.
- 1:40–2:40 — Open Streamlit and show live sensor events arriving from the simulator.
- 2:40–3:20 — Submit a manual `/predict` request and explain the returned probability/risk label.
- 3:20–4:00 — Show model version/metrics and the local model registry files.
- 4:00–4:30 — Show Floci AZ health and logs indicating Blob/Queue integration (if Floci is reachable).
- 4:30–5:00 — Run tests, mention CI, and state limitations/future work.

## Troubleshooting
- Port conflict: `docker compose ps`; ensure ports 8000 and 8501 are free. Keep Floci AZ on 4577.
- API keeps restarting: `docker compose logs --tail 200 api`.
- Dataset download fails: check internet, then retry `docker compose up --build`; local training downloads from UCI.
- Dashboard cannot reach API: Compose uses `http://api:8000` internally; browser uses `localhost:8501`.
- Floci writes fail: check `Invoke-RestMethod http://localhost:4577/_floci/health`, and confirm `.env` uses `http://host.docker.internal:4577` for container-to-host access.
- No dashboard data: wait for simulator events and refresh the page.
