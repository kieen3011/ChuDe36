"""Application Orchestrator cho he thong giam sat kho."""

import argparse
from datetime import datetime, timedelta
import inspect
import math
from numbers import Real
import sys

import display
from alert_system import AlertSystem
from config import (
    ALERT_LOG_PATH,
    REPORT_PATH,
    SENSOR_DEFINITIONS,
    SENSOR_PROFILES,
    SIMULATION_SEED,
    SIMULATION_START_TIME,
    SIMULATION_STEP_COUNT,
    SIMULATION_STEP_SECONDS,
)
from integration_adapters import (
    AlertAdapter,
    DemoSimulation,
    SimulationAdapter,
    create_display_summary,
)
from monitoring_manager import MonitoringManager
from sensor import ColdStorageSensor, DryStorageSensor, ServerRoomSensor
from statistics_tracker import StatisticsTracker


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


def _is_iso_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _error_record(kind, event, message, sensor=None, trusted_timestamp=None):
    """Tao Error Record theo contract da duoc phe duyet."""

    event_timestamp = event.get("timestamp")
    timestamp = event_timestamp if _is_iso_timestamp(event_timestamp) else trusted_timestamp
    location_id = None
    if sensor is not None:
        location_id = sensor.get_reading()["location_id"]

    sensor_id = event.get("sensor_id")
    if not isinstance(sensor_id, str) or not sensor_id.strip():
        sensor_id = None
    return {
        "kind": kind,
        "sensor_id": sensor_id,
        "location_id": location_id,
        "timestamp": timestamp,
        "message": message,
    }


def process_event(
    event, manager, alert_system, statistics, step_timestamp=None
):
    """Ap dung mot Simulation Event va tra Environmental Alert neu co."""

    if not isinstance(event, dict):
        raise TypeError("event must be a dictionary")
    kind = event.get("kind")
    if kind not in _EVENT_KINDS:
        raise ValueError("unsupported event kind")

    sensor_id = event.get("sensor_id")
    if not isinstance(sensor_id, str) or not sensor_id.strip():
        statistics.record_error(
            _error_record(
                "UNKNOWN_SENSOR",
                event,
                "sensor_id is missing or invalid",
                trusted_timestamp=step_timestamp,
            )
        )
        return None

    sensor = manager.get_sensor(sensor_id)
    if sensor is None:
        statistics.record_error(
            _error_record(
                "UNKNOWN_SENSOR",
                event,
                "sensor_id is not registered",
                trusted_timestamp=step_timestamp,
            )
        )
        return None


    timestamp = event.get("timestamp")
    if not _is_iso_timestamp(timestamp) or (
        step_timestamp is not None and timestamp != step_timestamp
    ):
        statistics.record_error(
            _error_record(
                "INVALID_DATA",
                event,
                "event timestamp does not match the orchestration step",
                sensor,
                step_timestamp,
            )
        )
        return None

    if kind == "DISCONNECT":
        if event.get("temperature") is not None or event.get("humidity") is not None:
            statistics.record_error(
                _error_record(
                    "INVALID_DATA", event, "DISCONNECT must not carry measurement", sensor
                )
            )
            return None
        if sensor.get_reading()["status"] == "ERROR":
            return None
        sensor.set_status("ERROR")
        statistics.record_error(
            _error_record("DISCONNECT", event, "sensor connection lost", sensor)
        )
        return None

    if kind == "RECOVER":
        if event.get("temperature") is not None or event.get("humidity") is not None:
            statistics.record_error(
                _error_record(
                    "INVALID_DATA", event, "RECOVER must not carry measurement", sensor
                )
            )
            return None
        if sensor.get_reading()["status"] == "ERROR":
            sensor.set_status("ACTIVE")
        return None

    if kind == "INVALID_DATA":
        statistics.record_error(
            _error_record(
                "INVALID_DATA", event, "simulation produced invalid data", sensor
            )
        )
        return None


    temperature = event.get("temperature")
    humidity = event.get("humidity")
    if (
        isinstance(temperature, bool)
        or isinstance(humidity, bool)
        or not isinstance(temperature, Real)
        or not isinstance(humidity, Real)
        or not math.isfinite(temperature)
        or not math.isfinite(humidity)
        or not (-50.0 <= temperature <= 100.0)
        or not (0.0 <= humidity <= 100.0)
    ):
        statistics.record_error(
            _error_record(
                "INVALID_DATA", event, "measurement is invalid", sensor
            )
        )
        return None

    try:
        accepted = sensor.update_measurement(
            temperature,
            humidity,
            timestamp,
        )
    except (TypeError, ValueError) as error:
        statistics.record_error(
            _error_record("INVALID_DATA", event, str(error), sensor)
        )
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
        step_recorder = getattr(display, "record_step", None)
        if step_recorder is not None:
            error_start = len(statistics.get_errors())
        step_alerts = []
        for event in events:
            alert = process_event(
                event, manager, alert_system, statistics, timestamp
            )
            if alert is not None:
                step_alerts.append(alert)
        readings = manager.collect_readings()
        if step_recorder is not None:
            step_recorder(
                step_index=step_index,
                timestamp=timestamp,
                events=events,
                readings=readings,
                alerts=step_alerts,
                errors=statistics.get_errors()[error_start:],
                cumulative_summary=statistics.get_summary(),
            )
        snapshot_renderer = display.render_snapshot
        if "current_timestamp" in inspect.signature(snapshot_renderer).parameters:
            snapshot_renderer(
                readings, step_alerts, step_index,
                current_timestamp=timestamp,
            )
        else:
            snapshot_renderer(
                readings, step_alerts, step_index
            )

    summary = statistics.get_summary()
    display.render_summary(create_display_summary(summary))
    if csv_path is not None:
        statistics.export_csv(csv_path)
    if json_path is not None:
        statistics.export_json(json_path)
    return summary


def create_application(mode="random"):
    """Khoi tao cac module production va dependency integration."""
    manager = create_default_manager()

    def status_provider(sensor_id):
        sensor = manager.get_sensor(sensor_id)
        return sensor.get_reading()["status"] if sensor is not None else "ERROR"

    if mode == "demo":
        simulation = DemoSimulation()
    else:
        simulation = SimulationAdapter(
            SIMULATION_SEED, SENSOR_PROFILES, status_provider
        )
    alerts = AlertAdapter(AlertSystem())
    statistics = StatisticsTracker()
    return manager, simulation, alerts, statistics


def main() -> int:
    """Chay phien mo phong mac dinh va tra exit code."""
    try:
        parser = argparse.ArgumentParser(description="IoT Warehouse Monitoring System")
        parser.add_argument(
            "--mode", choices=("random", "demo"), default="random",
            help="Chon mo phong ngau nhien hoac kich ban demo",
        )
        arguments = parser.parse_args()
        manager, simulation, alerts, statistics = create_application(arguments.mode)
        run_simulation(
            manager=manager,
            simulation_engine=simulation,
            alert_system=alerts,
            statistics=statistics,
            display=display,
            step_count=SIMULATION_STEP_COUNT,
            start_time=SIMULATION_START_TIME,
            step_seconds=SIMULATION_STEP_SECONDS,
            csv_path=ALERT_LOG_PATH,
            json_path=REPORT_PATH,
        )
    except Exception as error:
        print(f"Loi nghiem trong: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
