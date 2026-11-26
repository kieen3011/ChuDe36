import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import display
from alert_system import AlertSystem
from data_simulator import DataSimulator
from integration_adapters import (
    AlertAdapter,
    SimulationAdapter,
    create_display_summary,
)
from main import create_default_manager, process_event, run_simulation
from sensor import Sensor
from statistics_tracker import StatisticsTracker


ROOT = Path(__file__).resolve().parents[2]


class ContractIntegrationTests(unittest.TestCase):
    def test_real_modules_can_be_imported(self):
        self.assertTrue(callable(run_simulation))
        self.assertTrue(callable(AlertSystem))
        self.assertTrue(callable(StatisticsTracker))

    def test_default_manager_has_three_sensor_types(self):
        readings = create_default_manager().collect_readings()
        self.assertEqual(
            [item["sensor_type"] for item in readings],
            ["COLD_STORAGE", "DRY_STORAGE", "SERVER_ROOM"],
        )

    def test_simulator_exposes_canonical_generate_events_api(self):
        simulator = SimulationAdapter(
            "CHUDE36-TEST",
            {"S": {"location_id": "A", "incident_schedule": {}}},
        )
        events = simulator.generate_events(0, "2026-11-24T08:00:00+07:00")
        self.assertIsInstance(events, list)

    def test_orchestrator_accepts_real_alert_system(self):
        event = {
            "kind": "READING",
            "sensor_id": "COLD-01",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "temperature": 5.0,
            "humidity": 90.0,
        }
        result = process_event(
            event,
            create_default_manager(),
            AlertAdapter(AlertSystem()),
            StatisticsTracker("TEST"),
        )
        self.assertIsNone(result)

    def test_alert_system_returns_canonical_warning_record(self):
        reading = {
            "sensor_id": "COLD-01",
            "sensor_type": "COLD_STORAGE",
            "location_id": "A",
            "status": "ACTIVE",
            "temperature": 9.0,
            "humidity": 90.0,
            "timestamp": "2026-11-24T08:00:00+07:00",
        }
        alert = AlertAdapter(AlertSystem()).evaluate(reading)
        self.assertEqual(alert["severity"], "WARNING")
        self.assertEqual(alert["violated_metrics"], ["temperature"])

    def test_normal_reading_returns_none(self):
        reading = {
            "sensor_id": "COLD-01",
            "sensor_type": "COLD_STORAGE",
            "location_id": "A",
            "status": "ACTIVE",
            "temperature": 5.0,
            "humidity": 90.0,
            "timestamp": "2026-11-24T08:00:00+07:00",
        }
        self.assertIsNone(AlertAdapter(AlertSystem()).evaluate(reading))

    def test_location_a_is_a_valid_core_identifier(self):
        result = AlertSystem().evaluate("S", "A", 5.0, 90.0, "t")
        self.assertEqual(result["status"], "OK")

    def test_zone_b_humidity_equal_sixty_is_warning(self):
        result = AlertSystem().evaluate("S", "Khu B", 22.0, 60.0, "t")
        self.assertNotEqual(result["alert_level"], "Bình thường")

    def test_zone_c_temperature_equal_thirty_is_warning(self):
        result = AlertSystem().evaluate("S", "Khu C", 30.0, 50.0, "t")
        self.assertNotEqual(result["alert_level"], "Bình thường")

    def test_critical_delta_is_three_degrees(self):
        result = AlertSystem().evaluate("S", "Khu B", 28.1, 50.0, "t")
        self.assertEqual(result["alert_level"], "Cảnh báo nghiêm trọng")

    def test_two_violations_create_one_structured_alert(self):
        reading = {
            "sensor_id": "S",
            "sensor_type": "COLD_STORAGE",
            "location_id": "A",
            "status": "ACTIVE",
            "temperature": 12.0,
            "humidity": 70.0,
            "timestamp": "t",
        }
        result = AlertAdapter(AlertSystem()).evaluate(reading)
        self.assertEqual(
            set(result["violated_metrics"]), {"temperature", "humidity"}
        )

    def test_bool_is_not_a_valid_alert_measurement(self):
        result = AlertSystem().evaluate("S", "Khu A", True, True, "t")
        self.assertEqual(result["status"], "ERROR")

    def test_invalid_alert_does_not_poison_dedup_key(self):
        tracker = StatisticsTracker("TEST")
        invalid = {
            "sensor_id": "S",
            "location_id": "A",
            "timestamp": "t",
            "severity": "WARNING",
            "violated_metrics": "temperature",
            "temperature": 9.0,
            "humidity": 90.0,
        }
        corrected = dict(invalid, violated_metrics=["temperature"])
        with self.assertRaises(ValueError):
            tracker.record_alert(invalid)
        self.assertTrue(tracker.record_alert(corrected))

    def test_summary_is_compatible_with_display(self):
        summary = StatisticsTracker("TEST").get_summary()
        self.assertIn("errors_by_type", summary)
        view = create_display_summary(summary)
        display.render_summary(view)
        self.assertNotIn("total_errors", summary)

    def test_stale_reading_does_not_create_alert(self):
        manager = create_default_manager()
        sensor = manager.get_sensor("COLD-01")
        sensor.update_measurement(5.0, 90.0, "2026-11-24T07:59:00+07:00")
        sensor.set_status("INACTIVE")
        event = {
            "kind": "READING",
            "sensor_id": "COLD-01",
            "timestamp": "2026-11-24T08:00:00+07:00",
            "temperature": 12.0,
            "humidity": 70.0,
        }
        result = process_event(
            event, manager, AlertSystem(), StatisticsTracker("TEST")
        )
        self.assertIsNone(result)

    def test_valid_alert_deduplicates(self):
        tracker = StatisticsTracker("TEST")
        alert = {
            "sensor_id": "S",
            "location_id": "A",
            "timestamp": "t",
            "severity": "WARNING",
            "violated_metrics": ["temperature"],
            "temperature": 9.0,
            "humidity": 90.0,
        }
        self.assertTrue(tracker.record_alert(alert))
        self.assertFalse(tracker.record_alert(alert))

    def test_multiple_sensors_can_share_location(self):
        tracker = StatisticsTracker("TEST")
        for sensor_id in ("S1", "S2"):
            tracker.record_alert(
                {
                    "sensor_id": sensor_id,
                    "location_id": "A",
                    "timestamp": "t",
                    "severity": "WARNING",
                    "violated_metrics": ["temperature"],
                    "temperature": 9.0,
                    "humidity": 90.0,
                }
            )
        self.assertEqual(tracker.get_summary()["by_location"]["A"]["total"], 2)

    def test_seed_is_reproducible(self):
        first = DataSimulator("CHUDE36-TEST")
        second = DataSimulator("CHUDE36-TEST")
        first_values = [first.next_reading("Khu A", 0, 0) for _ in range(5)]
        second_values = [second.next_reading("Khu A", 0, 0) for _ in range(5)]
        self.assertEqual(first_values, second_values)

    def test_json_export_rejects_nan(self):
        tracker = StatisticsTracker("TEST")
        with self.assertRaises((TypeError, ValueError)):
            tracker.record_alert(
                {
                    "sensor_id": "S",
                    "location_id": "A",
                    "timestamp": "t",
                    "severity": "WARNING",
                    "violated_metrics": ["temperature"],
                    "temperature": math.nan,
                    "humidity": 90.0,
                }
            )

    def test_main_cli_runs_system_and_creates_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "main.py")],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertTrue((Path(directory) / "output" / "report.json").exists())

    def test_standard_library_statistics_is_not_shadowed(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import statistics; print(statistics.mean([1, 2, 3]))",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "2")

    def test_continuous_disconnect_is_counted_by_approved_policy(self):
        manager = create_default_manager()

        def status_provider(sensor_id):
            return manager.get_sensor(sensor_id).get_reading()["status"]

        simulator = SimulationAdapter(
            "TEST",
            {
                "COLD-01": {
                    "location_id": "A",
                    "incident_schedule": {
                        0: "DISCONNECT",
                        1: "DISCONNECT",
                        2: "RECOVER",
                    },
                }
            },
            status_provider,
        )
        tracker = StatisticsTracker("TEST")
        alerts = AlertAdapter(AlertSystem())
        for step in range(3):
            timestamp = f"2026-11-24T08:0{step}:00+07:00"
            for event in simulator.generate_events(step, timestamp):
                process_event(event, manager, alerts, tracker, timestamp)
        self.assertEqual(tracker.get_summary()["error_count"], 1)
        self.assertEqual(
            manager.get_sensor("COLD-01").get_reading()["status"], "ACTIVE"
        )

    def test_unknown_sensor_error_nullable_fields(self):
        tracker = StatisticsTracker("TEST")
        timestamp = "2026-11-24T08:00:00+07:00"
        event = {
            "kind": "READING",
            "sensor_id": "UNKNOWN",
            "timestamp": timestamp,
            "temperature": 5.0,
            "humidity": 90.0,
        }
        process_event(
            event,
            create_default_manager(),
            AlertAdapter(AlertSystem()),
            tracker,
            timestamp,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            tracker.export_json(str(path))
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["errors"][0]["sensor_id"], "UNKNOWN")
        self.assertIsNone(data["errors"][0]["location_id"])


if __name__ == "__main__":
    unittest.main()
