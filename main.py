"""Application Orchestrator cho he thong giam sat kho."""

from datetime import datetime, timedelta
from numbers import Real

from config import SENSOR_DEFINITIONS
from monitoring_manager import MonitoringManager
from sensor import ColdStorageSensor, DryStorageSensor, ServerRoomSensor


_EVENT_KINDS = frozenset({"READING", "DISCONNECT", "RECOVER", "INVALID_DATA"})
_SENSOR_CLASSES = {
    "COLD_STORAGE": ColdStorageSensor,
    "DRY_STORAGE": DryStorageSensor,
    "SERVER_ROOM": ServerRoomSensor,
}


def create_default_manager():
    """Khoi tao va dang ky cac Sensor trong cau hinh TV1."""

    manager = MonitoringManager()
    for definition in SENSOR_DEFINITIONS:
        sensor_class = _SENSOR_CLASSES[definition["sensor_type"]]
        manager.register_sensor(
            sensor_class(definition["sensor_id"], definition["location_id"])
        )
    return manager


def create_step_timestamp(start_time, step_index, step_seconds):
    """Tao timestamp xac dinh tu moc bat dau va chi so buoc."""

    if not isinstance(start_time, str):
        raise TypeError("start_time must be a string")
    if isinstance(step_index, bool) or not isinstance(step_index, int):
        raise TypeError("step_index must be an integer")
    if step_index < 0:
        raise ValueError("step_index must not be negative")
    if isinstance(step_seconds, bool) or not isinstance(step_seconds, Real):
        raise TypeError("step_seconds must be a real number")
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("start_time must use ISO 8601 format") from error
    return (start + timedelta(seconds=step_index * step_seconds)).isoformat()


def _error_record(kind, event, message):
    """Tao Error Record tam thoi cho den khi TV4 chot schema."""

    return {
        "kind": kind,
        "sensor_id": event.get("sensor_id"),
        "timestamp": event.get("timestamp"),
        "message": message,
    }


def process_event(event, manager, alert_system, statistics):
    """Ap dung mot Simulation Event va tra Environmental Alert neu co."""

    if not isinstance(event, dict):
        raise TypeError("event must be a dictionary")
    kind = event.get("kind")
    if kind not in _EVENT_KINDS:
        raise ValueError("unsupported event kind")

    sensor_id = event.get("sensor_id")
    sensor = manager.get_sensor(sensor_id)
    if sensor is None:
        statistics.record_error(
            _error_record("UNKNOWN_SENSOR", event, "sensor_id is not registered")
        )
        return None

    if kind == "DISCONNECT":
        sensor.set_status("ERROR")
        statistics.record_error(
            _error_record("DISCONNECT", event, "sensor connection lost")
        )
        return None

    if kind == "RECOVER":
        if sensor.get_reading()["status"] == "ERROR":
            sensor.set_status("ACTIVE")
        return None

    if kind == "INVALID_DATA":
        statistics.record_error(
            _error_record("INVALID_DATA", event, "simulation produced invalid data")
        )
        return None

    try:
        accepted = sensor.update_measurement(
            event.get("temperature"),
            event.get("humidity"),
            event.get("timestamp"),
        )
    except (TypeError, ValueError) as error:
        statistics.record_error(_error_record("INVALID_DATA", event, str(error)))
        return None

    if not accepted:
        return None

    new_reading = sensor.get_reading()
    alert = alert_system.evaluate(new_reading)
    if alert is not None:
        statistics.record_alert(alert)
    return alert


def run_simulation(
    manager,
    simulation_engine,
    alert_system,
    statistics,
    display,
    step_count,
    start_time,
    step_seconds,
    csv_path=None,
    json_path=None,
):
    """Dieu phoi mot phien mo phong qua cac interface da thong nhat."""

    if isinstance(step_count, bool) or not isinstance(step_count, int):
        raise TypeError("step_count must be an integer")
    if step_count < 0:
        raise ValueError("step_count must not be negative")

    for step_index in range(step_count):
        timestamp = create_step_timestamp(start_time, step_index, step_seconds)
        events = simulation_engine.generate_events(step_index, timestamp)
        step_alerts = []
        for event in events:
            alert = process_event(event, manager, alert_system, statistics)
            if alert is not None:
                step_alerts.append(alert)
        display.render_snapshot(
            manager.collect_readings(), step_alerts, step_index
        )

    summary = statistics.get_summary()
    display.render_summary(summary)
    if csv_path is not None:
        statistics.export_csv(csv_path)
    if json_path is not None:
        statistics.export_json(json_path)
    return summary
