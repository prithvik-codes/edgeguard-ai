import os
import time
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
st.set_page_config(page_title="EdgeGuard AI", page_icon="🛠️", layout="wide")
st.title("🛠️ EdgeGuard AI")
st.caption("IoT predictive maintenance • FastAPI • scikit-learn • Docker • Floci AZ")

auto_refresh = st.sidebar.checkbox("Auto-refresh every 5 seconds", value=True)
limit = st.sidebar.slider("Events to display", min_value=20, max_value=250, value=100, step=10)

try:
    health = requests.get(f"{API}/health", timeout=3).json()
    model_info = requests.get(f"{API}/model-info", timeout=3).json()
    events = requests.get(f"{API}/telemetry?limit={limit}", timeout=5).json().get("events", [])
except Exception as exc:
    st.error(f"Cannot reach API at {API}: {exc}")
    st.info("Start the stack with `docker compose up --build -d` and wait for the API model to train.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("API status", health.get("status", "unknown").upper())
c2.metric("Model version", model_info.get("version", "not loaded"))
c3.metric("Dataset rows", f"{model_info.get('rows_used', 0):,}")
c4.metric("Events shown", len(events))

with st.expander("Model evaluation", expanded=True):
    metrics = model_info.get("metrics", {})
    cols = st.columns(max(1, len(metrics)))
    for col, (name, value) in zip(cols, metrics.items()):
        col.metric(name.replace("_", " ").title(), f"{value:.3f}")

cloud = health.get("cloud", {})
st.caption(f"Floci AZ endpoint: {cloud.get('endpoint', 'unknown')} · reachable: {cloud.get('reachable', 'not checked')}")

if not events:
    st.warning("Waiting for sensor readings. The simulator sends a new reading every few seconds.")
else:
    df = pd.DataFrame(events)
    for col in ["failure_probability", "air_temperature_k", "process_temperature_k",
                "rotational_speed_rpm", "torque_nm", "tool_wear_min"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    high = int((df.get("risk_level", pd.Series(dtype=str)) == "HIGH").sum())
    predicted = int((pd.to_numeric(df.get("prediction", pd.Series(dtype=float)), errors="coerce") == 1).sum())
    a, b, c = st.columns(3)
    a.metric("Potential failures predicted", predicted)
    b.metric("High-risk events", high)
    c.metric("Mean failure probability", f"{df['failure_probability'].mean():.1%}" if "failure_probability" in df else "n/a")

    if "timestamp" in df and "failure_probability" in df:
        st.subheader("Failure probability over time")
        fig = px.line(df, x="timestamp", y="failure_probability", color="machine_id",
                      markers=True, title="Model-estimated failure probability")
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
    if {"air_temperature_k", "torque_nm"}.issubset(df.columns):
        st.subheader("Sensor readings")
        fig2 = px.scatter(df, x="air_temperature_k", y="torque_nm", color="risk_level",
                          hover_data=["machine_id", "failure_probability", "tool_wear_min"])
        st.plotly_chart(fig2, use_container_width=True)
    st.subheader("Recent predictions")
    show_cols = [c for c in ["timestamp", "machine_id", "prediction_label", "failure_probability",
                             "risk_level", "air_temperature_k", "process_temperature_k",
                             "rotational_speed_rpm", "torque_nm", "tool_wear_min", "model_version"] if c in df]
    st.dataframe(df[show_cols].iloc[::-1], use_container_width=True, hide_index=True)

if auto_refresh:
    time.sleep(5)
    st.rerun()
