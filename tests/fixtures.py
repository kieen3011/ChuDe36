"""Du lieu dung chung da duoc khoa theo G0."""

from copy import deepcopy


BASE_TIMESTAMP = "2026-11-23T00:00:00+07:00"
STEP_ONE_TIMESTAMP = "2026-11-23T00:01:00+07:00"
STEP_THREE_TIMESTAMP = "2026-11-23T00:03:00+07:00"

THRESHOLDS = {
    "A": {
        "temperature": {
            "min": 2.0,
            "max": 8.0,
            "min_inclusive": True,
            "max_inclusive": True,
        },
        "humidity": {
            "min": 85.0,
            "max": 95.0,
            "min_inclusive": True,
            "max_inclusive": True,
        },
    },
    "B": {
        "temperature": {
            "min": 18.0,
            "max": 25.0,
            "min_inclusive": True,
            "max_inclusive": True,
        },
        "humidity": {
            "min": None,
            "max": 60.0,
            "min_inclusive": True,
            "max_inclusive": False,
        },
    },
    "C": {
        "temperature": {
            "min": None,
            "max": 30.0,
            "min_inclusive": True,
            "max_inclusive": False,
        },
        "humidity": {
            "min": 40.0,
            "max": 60.0,
            "min_inclusive": True,
            "max_inclusive": True,
        },
    },
}

SENSOR_PROFILES = {
    "COLD-01": {
        "initial_temperature": 5.0,
        "initial_humidity": 90.0,
        "temperature_step": 0.5,
        "humidity_step": 1.0,
        "incident_schedule": {3: "DISCONNECT", 4: "RECOVER", 7: "INVALID_DATA"},
    },
    "DRY-01": {
        "initial_temperature": 22.0,
        "initial_humidity": 50.0,
        "temperature_step": 0.8,
        "humidity_step": 1.5,
        "incident_schedule": {},
    },
    "SERVER-01": {
        "initial_temperature": 26.0,
        "initial_humidity": 50.0,
        "temperature_step": 1.0,
        "humidity_step": 1.0,
        "incident_schedule": {},
    },
}


def make_reading(
    sensor_id="COLD-01",
    sensor_type="COLD_STORAGE",
    location_id="A",
    status="ACTIVE",
    temperature=5.0,
    humidity=90.0,
    timestamp=BASE_TIMESTAMP,
):
    """Tao ban sao reading hop le de test co the tuy chinh."""
    return {
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "location_id": location_id,
        "status": status,
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": timestamp,
    }


def make_alert(
    sensor_id="COLD-01",
    location_id="A",
    timestamp=BASE_TIMESTAMP,
    severity="WARNING",
    violated_metrics=None,
    temperature=8.1,
    humidity=90.0,
):
    """Tao ban sao alert hop le de test co the tuy chinh."""
    return {
        "sensor_id": sensor_id,
        "location_id": location_id,
        "timestamp": timestamp,
        "severity": severity,
        "violated_metrics": list(violated_metrics or ["temperature"]),
        "temperature": temperature,
        "humidity": humidity,
    }


def copy_thresholds():
    """Tra ve ban sao threshold de test khong lam thay doi fixture goc."""
    return deepcopy(THRESHOLDS)


def copy_sensor_profiles():
    """Tra ve ban sao profile de test khong lam thay doi fixture goc."""
    return deepcopy(SENSOR_PROFILES)

