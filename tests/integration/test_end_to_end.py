import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import display
from alert_system import AlertSystem
from config import SENSOR_PROFILES, SIMULATION_SEED
from integration_adapters import AlertAdapter, SimulationAdapter
from main import create_default_manager, process_event, run_simulation
from statistics_tracker import StatisticsTracker


def event(kind, sensor_id, timestamp, temperature=None, humidity=None):
    return {
        "kind": kind,
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "temperature": temperature,
        "humidity": humidity,
    }


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.manager = create_default_manager()
        self.alerts = AlertAdapter(AlertSystem())
        self.tracker = StatisticsTracker("E2E")

    def process(self, item):
        return process_event(
            item,
            self.manager,
            self.alerts,
            self.tracker,
            item["timestamp"],
        )

    def test_deterministic_pipeline_covers_environment_and_device_paths(self):
        times = [f"2026-11-24T08:{index:02d}:00+07:00" for index in range(9)]
        self.assertIsNone(self.process(event("READING", "COLD-01", times[0], 5, 90)))
        warning = self.process(event("READING", "COLD-01", times[1], 9, 90))
        critical = self.process(event("READING", "COLD-01", times[2], 12, 70))
        self.process(event("DISCONNECT", "COLD-01", times[3]))
        self.process(event("DISCONNECT", "COLD-01", times[4]))
        self.process(event("RECOVER", "COLD-01", times[5]))
        self.process(event("INVALID_DATA", "COLD-01", times[6], -999, -999))
        self.process(event("READING", "UNKNOWN", times[7], 5, 90))
        self.process(event("DISCONNECT", "COLD-01", times[8]))

        self.assertEqual(warning["severity"], "WARNING")
        self.assertEqual(critical["severity"], "CRITICAL")
        self.assertEqual(
            set(critical["violated_metrics"]), {"temperature", "humidity"}
        )
        summary = self.tracker.get_summary()
        self.assertEqual(summary["total_alerts"], 2)
        self.assertEqual(summary["warning_count"], 1)
        self.assertEqual(summary["critical_count"], 1)
        self.assertEqual(summary["error_count"], 4)
        self.assertEqual(summary["errors_by_type"], {
            "DISCONNECT": 2,
            "INVALID_DATA": 1,
            "UNKNOWN_SENSOR": 1,
        })
        self.assertEqual(
            summary["total_alerts"],
            summary["warning_count"] + summary["critical_count"],
        )
        self.assertEqual(
            summary["error_count"], sum(summary["errors_by_type"].values())
        )

    def test_invalid_reading_keeps_last_valid_measurement(self):
        first = event(
            "READING", "COLD-01", "2026-11-24T08:00:00+07:00", 5, 90
        )
        invalid = event(
            "READING", "COLD-01", "2026-11-24T08:01:00+07:00", -999, 90
        )
        self.process(first)
        self.process(invalid)
        reading = self.manager.get_sensor("COLD-01").get_reading()
        self.assertEqual(reading["temperature"], 5.0)
        self.assertEqual(reading["timestamp"], first["timestamp"])

    def test_event_timestamp_mismatch_uses_trusted_step_timestamp(self):
        trusted = "2026-11-24T08:00:00+07:00"
        item = event("READING", "COLD-01", "bad", 5, 90)
        process_event(
            item, self.manager, self.alerts, self.tracker, trusted
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.tracker.export_json(str(path))
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["errors"][0]["timestamp"], trusted)

    def test_real_simulator_pipeline_is_reproducible_and_exports(self):
        def build_run(directory):
            manager = create_default_manager()

            def status_provider(sensor_id):
                return manager.get_sensor(sensor_id).get_reading()["status"]

            simulator = SimulationAdapter(
                SIMULATION_SEED, SENSOR_PROFILES, status_provider
            )
            tracker = StatisticsTracker("REAL-E2E")
            csv_path = Path(directory) / "alert_logs.csv"
            json_path = Path(directory) / "report.json"
            with redirect_stdout(io.StringIO()):
                summary = run_simulation(
                    manager,
                    simulator,
                    AlertAdapter(AlertSystem()),
                    tracker,
                    display,
                    10,
                    "2026-11-24T08:00:00+07:00",
                    60,
                    str(csv_path),
                    str(json_path),
                )
            readings = manager.collect_readings()
            return summary, readings, csv_path, json_path

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = build_run(first_dir)
            second = build_run(second_dir)
            self.assertEqual(first[0], second[0])
            self.assertEqual(first[1], second[1])
            for output in (first[2], first[3], second[2], second[3]):
                self.assertTrue(output.exists())
            with first[2].open("r", encoding="utf-8", newline="") as stream:
                list(csv.DictReader(stream))
            payload = json.loads(first[3].read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"], first[0])

    def test_threshold_boundaries_and_exact_critical_delta(self):
        alert_system = AlertSystem()
        cases = [
            ("B", 22, 59.999, None),
            ("B", 22, 60, "WARNING"),
            ("B", 28, 50, "CRITICAL"),
            ("C", 29.999, 50, None),
            ("C", 30, 50, "WARNING"),
            ("C", 33, 50, "CRITICAL"),
            ("A", 5, 75, "CRITICAL"),
        ]
        for index, (location, temperature, humidity, severity) in enumerate(cases):
            reading = {
                "sensor_id": f"S{index}",
                "sensor_type": "GENERIC",
                "location_id": location,
                "status": "ACTIVE",
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": f"2026-11-24T08:{index:02d}:00+07:00",
            }
            result = AlertAdapter(alert_system).evaluate(reading)
            if severity is None:
                self.assertIsNone(result)
            else:
                self.assertEqual(result["severity"], severity)


if __name__ == "__main__":
    unittest.main()
