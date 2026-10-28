import os
import random
import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "3"))

def reading(i):
    # Values are bounded to the API schema. This is a demonstration simulator,
    # not a physically calibrated digital twin.
    stressed = (i % 12 in (8, 9, 10))
    return {
        "machine_id": f"machine-{(i % 3) + 1:03d}",
        "air_temperature_k": round(random.uniform(303, 313) + (4 if stressed else 0), 2),
        "process_temperature_k": round(random.uniform(313, 323) + (3 if stressed else 0), 2),
        "rotational_speed_rpm": random.randint(1100, 1900) - (150 if stressed else 0),
        "torque_nm": round(random.uniform(25, 65) + (15 if stressed else 0), 2),
        "tool_wear_min": random.randint(20, 240) if not stressed else random.randint(180, 300)
    }

def main():
    i = 0
    logging.info("Starting sensor simulator; API=%s interval=%ss", API_URL, INTERVAL)
    while True:
        i += 1
        try:
            response = requests.post(f"{API_URL}/predict", json=reading(i), timeout=10)
            response.raise_for_status()
            data = response.json()
            logging.info("%s | %s | probability=%.3f | risk=%s",
                         data["machine_id"], data["prediction_label"],
                         data["failure_probability"], data["risk_level"])
        except Exception as exc:
            logging.warning("Telemetry send failed: %s", exc)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
