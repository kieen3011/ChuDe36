"""Cau hinh dieu phoi thuoc pham vi TV1."""

from datetime import timedelta


SIMULATION_START_TIME = "2026-11-24T08:00:00+07:00"
SIMULATION_STEP_COUNT = 10
SIMULATION_STEP_SECONDS = int(timedelta(minutes=1).total_seconds())

SENSOR_DEFINITIONS = (
    {"sensor_id": "COLD-01", "location_id": "A", "sensor_type": "COLD_STORAGE"},
    {"sensor_id": "DRY-01", "location_id": "B", "sensor_type": "DRY_STORAGE"},
    {"sensor_id": "SERVER-01", "location_id": "C", "sensor_type": "SERVER_ROOM"},
)
