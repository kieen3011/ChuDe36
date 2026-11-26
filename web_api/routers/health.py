"""Health va config endpoints."""

import copy

from fastapi import APIRouter

from alert_system import DEFAULT_THRESHOLDS
from config import SENSOR_DEFINITIONS
from web_api.config import (
    API_VERSION,
    CORE_VERSION,
    DEFAULT_SEED,
    DEFAULT_STEP_COUNT,
    DEFAULT_STEP_INTERVAL_SECONDS,
    MAX_REQUEST_BODY_BYTES,
    MAX_SEED_LENGTH,
    MAX_STEP_COUNT,
    MAX_STEP_INTERVAL_SECONDS,
    MIN_STEP_INTERVAL_SECONDS,
    docs_enabled,
)
from web_api.schemas import HealthResponse


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    """Tra liveness va version cong khai."""
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "core_version": CORE_VERSION,
    }


@router.get("/config")
def get_config() -> dict:
    """Tra ban sao approved config va resource limit."""
    return {
        "modes": ["random", "demo"],
        "defaults": {
            "seed": DEFAULT_SEED,
            "step_count": DEFAULT_STEP_COUNT,
            "step_interval_seconds": DEFAULT_STEP_INTERVAL_SECONDS,
        },
        "limits": {
            "seed_length_max": MAX_SEED_LENGTH,
            "step_count_max": MAX_STEP_COUNT,
            "step_interval_seconds_min": MIN_STEP_INTERVAL_SECONDS,
            "step_interval_seconds_max": MAX_STEP_INTERVAL_SECONDS,
            "request_body_bytes": MAX_REQUEST_BODY_BYTES,
        },
        "sensor_definitions": copy.deepcopy(SENSOR_DEFINITIONS),
        "locations": ["A", "B", "C"],
        "thresholds": copy.deepcopy(DEFAULT_THRESHOLDS),
        "freshness_values": [
            "FRESH", "STALE", "NO_DATA", "RECOVERY_PENDING",
        ],
        "capabilities": {
            "custom_thresholds": False,
            "server_export": False,
            "openapi": docs_enabled(),
        },
    }
