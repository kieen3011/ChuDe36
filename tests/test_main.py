import unittest

from main import (
    create_default_manager,
    create_step_timestamp,
    process_event,
    run_simulation,
)
from monitoring_manager import MonitoringManager
from sensor import Sensor


class RecordingAlertSystem:
    def __init__(self, response=None):
        self.readings = []
        self.response = response

    def evaluate(self, reading):
        self.readings.append(reading)
        return self.response


class RecordingStatistics:
    def __init__(self):
        self.alerts = []
        self.errors = []
        self.exported_csv = []
        self.exported_json = []

    def record_alert(self, alert):
        self.alerts.append(alert)
        return True

    def record_error(self, error):
        self.errors.append(error)

    def get_summary(self):
        return {"alerts": len(self.alerts), "errors": len(self.errors)}

    def export_csv(self, file_path):
        self.exported_csv.append(file_path)

    def export_json(self, file_path):
        self.exported_json.append(file_path)


class RecordingDisplay:
    def __init__(self):
        self.steps = []
        self.summaries = []

    def render_snapshot(self, readings, alerts, step_index):
        self.steps.append((readings, alerts, step_index))

    def render_summary(self, summary):
        self.summaries.append(summary)


class FixedSimulation:
    def __init__(self, events_by_step):
        self.events_by_step = events_by_step
        self.calls = []

    def generate_events(self, step_index, timestamp):
        self.calls.append((step_index, timestamp))
        return self.events_by_step[step_index]


def reading_event(sensor_id="S01", timestamp="2026-11-24T08:00:00+07:00"):
    return {
        "kind": "READING",
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "temperature": 5.0,
        "humidity": 90.0,
    }


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.manager = MonitoringManager()
        self.sensor = Sensor("S01", "A")
        self.manager.register_sensor(self.sensor)
        self.alert_system = RecordingAlertSystem()
        self.statistics = RecordingStatistics()

    def test_create_step_timestamp_is_deterministic_and_distinct(self):
        first = create_step_timestamp("2026-11-24T08:00:00+07:00", 0, 60)
        third = create_step_timestamp("2026-11-24T08:00:00+07:00", 2, 60)

        self.assertEqual(first, "2026-11-24T08:00:00+07:00")
        self.assertEqual(third, "2026-11-24T08:02:00+07:00")

    def test_create_default_manager_registers_configured_sensor_subclasses(self):
        manager = create_default_manager()

        self.assertEqual(
            [
                (reading["sensor_id"], reading["sensor_type"], reading["location_id"])
                for reading in manager.collect_readings()
            ],
            [
                ("COLD-01", "COLD_STORAGE", "A"),
                ("DRY-01", "DRY_STORAGE", "B"),
                ("SERVER-01", "SERVER_ROOM", "C"),
            ],
        )

    def test_create_step_timestamp_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            create_step_timestamp("not-a-time", 0, 60)
        with self.assertRaises(TypeError):
            create_step_timestamp("2026-11-24T08:00:00", True, 60)
        with self.assertRaises(ValueError):
            create_step_timestamp("2026-11-24T08:00:00", -1, 60)

    def test_accepted_reading_is_evaluated_and_alert_is_recorded(self):
        alert = {
            "sensor_id": "S01",
            "location_id": "A",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "severity": "WARNING",
            "violated_metrics": ["temperature"],
            "temperature": 5.0,
            "humidity": 90.0,
        }
        self.alert_system.response = alert

        result = process_event(
            reading_event(), self.manager, self.alert_system, self.statistics
        )

        self.assertEqual(result, alert)
        self.assertEqual(len(self.alert_system.readings), 1)
        self.assertEqual(self.statistics.alerts, [alert])
        self.assertEqual(self.sensor.get_reading()["temperature"], 5.0)

    def test_rejected_reading_is_not_evaluated_as_stale_data(self):
        self.sensor.update_measurement(4.0, 89.0, "2026-11-24T07:59:00+07:00")
        self.sensor.set_status("INACTIVE")

        result = process_event(
            reading_event(), self.manager, self.alert_system, self.statistics
        )

        self.assertIsNone(result)
        self.assertEqual(self.alert_system.readings, [])
        self.assertEqual(self.statistics.alerts, [])
        self.assertEqual(self.sensor.get_reading()["temperature"], 4.0)

    def test_invalid_reading_is_recorded_as_data_error_without_alert(self):
        event = reading_event()
        event["temperature"] = float("nan")

        result = process_event(
            event, self.manager, self.alert_system, self.statistics
        )

        self.assertIsNone(result)
        self.assertEqual(self.alert_system.readings, [])
        self.assertEqual(self.statistics.errors[0]["kind"], "INVALID_DATA")
        self.assertIsNone(self.sensor.get_reading()["temperature"])

    def test_disconnect_sets_error_and_records_device_error(self):
        event = {
            "kind": "DISCONNECT",
            "sensor_id": "S01",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "temperature": None,
            "humidity": None,
        }

        self.assertIsNone(
            process_event(event, self.manager, self.alert_system, self.statistics)
        )
        self.assertEqual(self.sensor.get_reading()["status"], "ERROR")
        self.assertEqual(self.statistics.errors[0]["kind"], "DISCONNECT")
        self.assertEqual(self.alert_system.readings, [])

    def test_recover_activates_only_error_sensor(self):
        event = {
            "kind": "RECOVER",
            "sensor_id": "S01",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "temperature": None,
            "humidity": None,
        }
        self.sensor.set_status("ERROR")
        process_event(event, self.manager, self.alert_system, self.statistics)
        self.assertEqual(self.sensor.get_reading()["status"], "ACTIVE")

        self.sensor.set_status("INACTIVE")
        process_event(event, self.manager, self.alert_system, self.statistics)
        self.assertEqual(self.sensor.get_reading()["status"], "INACTIVE")

    def test_invalid_data_event_does_not_update_or_evaluate(self):
        event = {
            "kind": "INVALID_DATA",
            "sensor_id": "S01",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "temperature": "bad",
            "humidity": 90.0,
        }

        process_event(event, self.manager, self.alert_system, self.statistics)

        self.assertEqual(self.statistics.errors[0]["kind"], "INVALID_DATA")
        self.assertEqual(self.alert_system.readings, [])
        self.assertIsNone(self.sensor.get_reading()["temperature"])

    def test_missing_sensor_is_recorded_without_environmental_alert(self):
        process_event(
            reading_event(sensor_id="UNKNOWN"),
            self.manager,
            self.alert_system,
            self.statistics,
        )

        self.assertEqual(self.statistics.errors[0]["kind"], "UNKNOWN_SENSOR")
        self.assertEqual(self.alert_system.readings, [])

    def test_unknown_event_kind_is_rejected(self):
        event = reading_event()
        event["kind"] = "OTHER"

        with self.assertRaises(ValueError):
            process_event(event, self.manager, self.alert_system, self.statistics)

    def test_run_simulation_routes_each_step_and_final_outputs(self):
        alert = {
            "sensor_id": "S01",
            "location_id": "A",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "severity": "WARNING",
            "violated_metrics": ["humidity"],
            "temperature": 5.0,
            "humidity": 90.0,
        }
        self.alert_system.response = alert
        simulation = FixedSimulation([[reading_event()]])
        display = RecordingDisplay()

        summary = run_simulation(
            manager=self.manager,
            simulation_engine=simulation,
            alert_system=self.alert_system,
            statistics=self.statistics,
            display=display,
            step_count=1,
            start_time="2026-11-24T08:00:00+07:00",
            step_seconds=60,
            csv_path="output/alert_logs.csv",
            json_path="output/report.json",
        )

        self.assertEqual(simulation.calls, [(0, "2026-11-24T08:00:00+07:00")])
        self.assertEqual(display.steps[0][1], [alert])
        self.assertEqual(display.steps[0][2], 0)
        self.assertEqual(display.steps[0][0][0]["temperature"], 5.0)
        self.assertEqual(summary, {"alerts": 1, "errors": 0})
        self.assertEqual(display.summaries, [summary])
        self.assertEqual(self.statistics.exported_csv, ["output/alert_logs.csv"])
        self.assertEqual(self.statistics.exported_json, ["output/report.json"])


if __name__ == "__main__":
    unittest.main()
