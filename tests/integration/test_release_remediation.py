import copy
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import display
from alert_system import AlertSystem, DEFAULT_THRESHOLDS
from integration_adapters import AlertAdapter
from main import create_application, create_default_manager, process_event
from statistics_tracker import StatisticsTracker


REPO_ROOT = Path(__file__).resolve().parents[2]


def make_event(kind, timestamp, temperature=None, humidity=None):
    return {
        "kind": kind,
        "sensor_id": "COLD-01",
        "timestamp": timestamp,
        "temperature": temperature,
        "humidity": humidity,
    }


class SafeExportTests(unittest.TestCase):
    def setUp(self):
        self.tracker = StatisticsTracker("EXPORT-TEST")
        self.tracker.record_alert({
            "sensor_id": "S1",
            "location_id": "A",
            "timestamp": "2026-11-26T08:00:00+07:00",
            "severity": "WARNING",
            "violated_metrics": ["temperature"],
            "temperature": 9.0,
            "humidity": 90.0,
        })

    def _assert_replace_failure_preserves_destination(self, method, suffix):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"report.{suffix}"
            path.write_text("OLD_REPORT", encoding="utf-8")
            replace_error = OSError("blocked")
            replace_error.winerror = 650
            with patch("statistics_tracker.os.replace", side_effect=replace_error):
                with self.assertRaisesRegex(OSError, "blocked"):
                    method(str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "OLD_REPORT")
            self.assertEqual([item.name for item in Path(directory).iterdir()], [path.name])

    def test_json_replace_failure_preserves_previous_report_and_cleans_temp(self):
        self._assert_replace_failure_preserves_destination(
            self.tracker.export_json, "json"
        )

    def test_csv_replace_failure_preserves_previous_report_and_cleans_temp(self):
        self._assert_replace_failure_preserves_destination(
            self.tracker.export_csv, "csv"
        )

    def test_replace_failure_without_destination_leaves_no_partial_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            with patch("statistics_tracker.os.replace", side_effect=OSError("blocked")):
                with self.assertRaises(OSError):
                    self.tracker.export_json(str(path))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_csv_replace_failure_without_destination_leaves_no_partial_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.csv"
            replace_error = OSError("blocked")
            replace_error.winerror = 650
            with patch("statistics_tracker.os.replace", side_effect=replace_error):
                with self.assertRaisesRegex(OSError, "blocked"):
                    self.tracker.export_csv(str(path))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_json_serialization_failure_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("OLD_REPORT", encoding="utf-8")
            with patch("statistics_tracker.json.dump", side_effect=TypeError("bad json")):
                with self.assertRaisesRegex(TypeError, "bad json"):
                    self.tracker.export_json(str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "OLD_REPORT")
            self.assertEqual([item.name for item in Path(directory).iterdir()], [path.name])

    def test_csv_serialization_failure_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.csv"
            path.write_text("OLD_REPORT", encoding="utf-8")
            with patch("statistics_tracker.csv.DictWriter.writerow", side_effect=OSError("bad csv")):
                with self.assertRaisesRegex(OSError, "bad csv"):
                    self.tracker.export_csv(str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "OLD_REPORT")
            self.assertEqual([item.name for item in Path(directory).iterdir()], [path.name])


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.manager = create_default_manager()
        self.alerts = AlertAdapter(AlertSystem())
        self.tracker = StatisticsTracker("FRESHNESS-TEST")

    def process(self, item):
        return process_event(
            item, self.manager, self.alerts, self.tracker, item["timestamp"]
        )

    def render(self, current_timestamp):
        stream = io.StringIO()
        with redirect_stdout(stream):
            display.render_snapshot(
                self.manager.collect_readings(), [], 0,
                current_timestamp=current_timestamp,
            )
        return stream.getvalue()

    def test_recovery_keeps_last_value_but_marks_it_pending_new_reading(self):
        t0 = "2026-11-26T08:00:00+07:00"
        t1 = "2026-11-26T08:01:00+07:00"
        t2 = "2026-11-26T08:02:00+07:00"
        self.process(make_event("READING", t0, 5, 90))
        self.process(make_event("DISCONNECT", t1))
        self.process(make_event("DISCONNECT", t1))
        self.process(make_event("RECOVER", t2))

        reading = self.manager.get_sensor("COLD-01").get_reading()
        output = self.render(t2)
        self.assertEqual(reading["status"], "ACTIVE")
        self.assertEqual(reading["timestamp"], t0)
        self.assertIn("cho du lieu moi", output)
        self.assertNotIn("5.0 | 90.0 | NORMAL", output)
        self.assertEqual(self.tracker.get_summary()["total_alerts"], 0)

    def test_first_accepted_reading_after_recovery_restores_freshness(self):
        t0 = "2026-11-26T08:00:00+07:00"
        t1 = "2026-11-26T08:01:00+07:00"
        t2 = "2026-11-26T08:02:00+07:00"
        t3 = "2026-11-26T08:03:00+07:00"
        self.process(make_event("READING", t0, 5, 90))
        self.process(make_event("DISCONNECT", t1))
        self.process(make_event("RECOVER", t2))
        self.process(make_event("READING", t3, 5.5, 89))

        output = self.render(t3)
        self.assertNotIn("cho du lieu moi", output)
        self.assertIn("5.5 | 89.0 | NORMAL", output)


class SessionIsolationTests(unittest.TestCase):
    def test_default_thresholds_are_deep_copied_per_instance(self):
        original = copy.deepcopy(DEFAULT_THRESHOLDS)
        self.addCleanup(self._restore_defaults, original)
        first = AlertSystem()
        second = AlertSystem()
        first.thresholds["A"]["temp_max"] = 999
        self.assertEqual(second.thresholds["A"]["temp_max"], original["A"]["temp_max"])
        self.assertEqual(DEFAULT_THRESHOLDS, original)

    @staticmethod
    def _restore_defaults(original):
        DEFAULT_THRESHOLDS.clear()
        DEFAULT_THRESHOLDS.update(original)

    def test_caller_thresholds_are_deep_copied_per_instance(self):
        source = copy.deepcopy(DEFAULT_THRESHOLDS)
        original = copy.deepcopy(source)
        first = AlertSystem(source)
        second = AlertSystem(source)
        first.thresholds["A"]["temp_max"] = 999
        source["B"]["hum_max"] = 1
        self.assertEqual(second.thresholds, original)
        self.assertEqual(first.thresholds["B"]["hum_max"], original["B"]["hum_max"])

    def test_application_sessions_have_independent_alert_configuration(self):
        first = create_application()
        second = create_application()
        first[2]._alert_system.thresholds["A"]["temp_max"] = 999
        self.assertEqual(second[2]._alert_system.thresholds["A"]["temp_max"], 8.0)


class CliAndEncodingTests(unittest.TestCase):
    def run_cli(self, *arguments, encoding="utf-8"):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ)
            environment["PYTHONIOENCODING"] = encoding
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "main.py"), *arguments],
                cwd=directory,
                env=environment,
                text=True,
                capture_output=True,
                encoding=encoding,
            )
            files = {
                path.name: path.read_bytes()
                for path in Path(directory).rglob("*") if path.is_file()
            }
        return result, files

    def test_demo_mode_runs_real_pipeline_with_expected_counts(self):
        result, files = self.run_cli("--mode", "demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(files["report.json"].decode("utf-8"))
        self.assertEqual(payload["summary"]["total_alerts"], 4)
        self.assertEqual(payload["summary"]["warning_count"], 2)
        self.assertEqual(payload["summary"]["critical_count"], 2)
        self.assertEqual(payload["summary"]["error_count"], 2)
        self.assertEqual(set(payload["summary"]["by_location"]), {"A", "B", "C"})
        self.assertEqual(
            {item["kind"] for item in payload["errors"]},
            {"DISCONNECT", "INVALID_DATA"},
        )
        self.assertTrue(any(
            set(item["violated_metrics"]) == {"temperature", "humidity"}
            for item in payload["alerts"]
        ))
        self.assertEqual(len(list(csv.DictReader(
            io.StringIO(files["alert_logs.csv"].decode("utf-8"))
        ))), 4)

    def test_random_mode_and_default_mode_remain_available(self):
        default_result, _ = self.run_cli()
        random_result, _ = self.run_cli("--mode", "random")
        self.assertEqual(default_result.returncode, 0, default_result.stderr)
        self.assertEqual(random_result.returncode, 0, random_result.stderr)

    def test_standalone_demos_exit_zero_with_cp1252_redirect(self):
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp1252"
        for script in ("data_simulator.py", "alert_system.py"):
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / script)],
                cwd=tempfile.gettempdir(),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, (script, result.stderr))

    def test_imports_have_no_console_side_effect(self):
        result = subprocess.run(
            [sys.executable, "-c", "import data_simulator, alert_system"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
