"""Pydantic schema cho request va response Web API."""

import math
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from web_api.config import (
    DEFAULT_SEED,
    DEFAULT_STEP_COUNT,
    DEFAULT_STEP_INTERVAL_SECONDS,
    MAX_SEED_LENGTH,
    MAX_STEP_COUNT,
    MAX_STEP_INTERVAL_SECONDS,
    MIN_STEP_INTERVAL_SECONDS,
)


class SimulationRunRequest(BaseModel):
    """Request chay mot phien mo phong stateless."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["random", "demo"]
    seed: StrictStr | None = DEFAULT_SEED
    step_count: StrictInt | None = DEFAULT_STEP_COUNT
    step_interval_seconds: StrictInt | StrictFloat | None = DEFAULT_STEP_INTERVAL_SECONDS
    thresholds: None = None

    @field_validator("seed")
    @classmethod
    def validate_seed(cls, value: str | None) -> str | None:
        if value is None or not value.strip() or len(value) > MAX_SEED_LENGTH:
            raise ValueError("seed must contain 1 to 128 characters")
        return value

    @field_validator("step_count")
    @classmethod
    def validate_step_count(cls, value: int | None) -> int | None:
        if value is None or not 1 <= value <= MAX_STEP_COUNT:
            raise ValueError("step_count must be between 1 and 100")
        return value

    @field_validator("step_interval_seconds")
    @classmethod
    def validate_interval(cls, value: int | float | None) -> float | None:
        if value is None or not math.isfinite(value):
            raise ValueError("step_interval_seconds must be finite")
        if not MIN_STEP_INTERVAL_SECONDS <= value <= MAX_STEP_INTERVAL_SECONDS:
            raise ValueError("step_interval_seconds is outside the approved range")
        return float(value)

    @model_validator(mode="after")
    def reject_demo_conflicts(self):
        if self.mode == "demo" and self.model_fields_set.intersection({
            "seed", "step_count", "step_interval_seconds", "thresholds",
        }):
            raise ValueError("demo mode does not accept simulation overrides")
        return self


class HealthResponse(BaseModel):
    status: Literal["ok"]
    api_version: str
    core_version: str


class SimulationMetadata(BaseModel):
    request_id: str
    api_version: str
    core_version: str
    mode: Literal["random", "demo"]
    effective_seed: str | None
    actual_step_count: int
    step_interval_seconds: float
    simulated_start: str
    simulated_end: str
    generated_at: str


class ReadingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    sensor_type: str
    location_id: str
    status: Literal["ACTIVE", "INACTIVE", "ERROR"]
    temperature: float | None
    humidity: float | None
    timestamp: str | None


class SensorSnapshot(BaseModel):
    reading: ReadingRecord
    freshness: Literal["FRESH", "STALE", "NO_DATA", "RECOVERY_PENDING"]


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    sensor_id: str
    timestamp: str
    temperature: float | None
    humidity: float | None


class AlertRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    location_id: str
    timestamp: str
    severity: Literal["WARNING", "CRITICAL"]
    violated_metrics: list[Literal["temperature", "humidity"]]
    temperature: float
    humidity: float


class ErrorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    sensor_id: str | None
    location_id: str | None
    timestamp: str
    message: str


class LocationCounts(BaseModel):
    WARNING: int
    CRITICAL: int
    total: int


class SummaryRecord(BaseModel):
    session_id: str
    total_alerts: int
    warning_count: int
    critical_count: int
    error_count: int
    by_location: dict[str, LocationCounts]
    errors_by_type: dict[str, int]


class TimelineStep(BaseModel):
    step_index: int
    simulated_at: str
    events: list[EventRecord]
    sensors: list[SensorSnapshot]
    alerts: list[AlertRecord]
    errors: list[ErrorRecord]
    cumulative_summary: SummaryRecord


class HistoryPoint(BaseModel):
    step_index: int
    simulated_at: str
    freshness: Literal["FRESH", "STALE", "NO_DATA", "RECOVERY_PENDING"]
    value: float | None


class SeverityStatistics(BaseModel):
    WARNING: int
    CRITICAL: int


class SimulationStatistics(BaseModel):
    by_location: dict[str, LocationCounts]
    by_severity: SeverityStatistics


class SimulationRunResponse(BaseModel):
    metadata: SimulationMetadata
    timeline: list[TimelineStep]
    readings: list[ReadingRecord]
    temperature_history: dict[str, list[HistoryPoint]]
    humidity_history: dict[str, list[HistoryPoint]]
    alerts: list[AlertRecord]
    errors: list[ErrorRecord]
    summary: SummaryRecord
    statistics: SimulationStatistics


class ErrorDetail(BaseModel):
    field: str
    reason: str


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]
    request_id: str


class CanonicalErrorResponse(BaseModel):
    error: ErrorEnvelope
