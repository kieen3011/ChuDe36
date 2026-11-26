"""Cau hinh cong khai va gioi han cua Web API."""

import os


API_VERSION = "1"
CORE_VERSION = "8428be8"
DEFAULT_STEP_COUNT = 10
DEFAULT_STEP_INTERVAL_SECONDS = 60.0
DEFAULT_SEED = "CHUDE36-DEMO"
MAX_STEP_COUNT = 100
INTERNAL_BENCHMARK_STEP_COUNT = 500
MIN_STEP_INTERVAL_SECONDS = 0.001
MAX_STEP_INTERVAL_SECONDS = 3600.0
MAX_SEED_LENGTH = 128
MAX_REQUEST_BODY_BYTES = 64 * 1024
DEMO_STEP_COUNT = 10
DEMO_STEP_INTERVAL_SECONDS = 60.0


def docs_enabled() -> bool:
    """Doc bien moi truong de bat hoac tat tai lieu API."""
    return os.getenv("CHUDE36_DOCS_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }


def cors_origins() -> list[str]:
    """Tra explicit CORS allowlist tu bien moi truong."""
    raw = os.getenv(
        "CHUDE36_CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]
