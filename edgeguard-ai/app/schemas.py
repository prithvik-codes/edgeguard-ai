from pydantic import BaseModel, Field, ConfigDict

class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    machine_id: str = Field(default="machine-001", min_length=1, max_length=64)
    air_temperature_k: float = Field(ge=250, le=400)
    process_temperature_k: float = Field(ge=250, le=450)
    rotational_speed_rpm: float = Field(ge=0, le=10000)
    torque_nm: float = Field(ge=0, le=200)
    tool_wear_min: float = Field(ge=0, le=500)

class PredictionResponse(BaseModel):
    machine_id: str
    prediction: int
    prediction_label: str
    failure_probability: float
    risk_level: str
    model_version: str
    timestamp: str
