import csv
import json
import tempfile
import unittest
from pathlib import Path

from statistics_tracker import StatisticsTracker


def make_alert(
    sensor_id="S-A01",
    location_id="A",
    timestamp="2026-11-26T08:00:00+00:00",
    severity="WARNING",
    violated_metrics=None,
    temperature=9.5,
    humidity=88.0,
):
    return {
        "sensor_id": sensor_id,
        "location_id": location_id,
        "timestamp": timestamp,
        "severity": severity,
        "violated_metrics": list(violated_metrics or ["temperature"]),
        "temperature": temperature,
        "humidity": humidity,
    }


class StatisticsTrackerTests(unittest.TestCase):
    def test_count_by_location_and_separate_severity(self):
        tracker = StatisticsTracker("TEST-01")
        self.assertTrue(tracker.record_alert(make_alert()))
        self.assertTrue(tracker.record_alert(make_alert(
            timestamp="2026-11-26T08:05:00+00:00", severity="CRITICAL"
        )))
        self.assertTrue(tracker.record_alert(make_alert(
            sensor_id="S-B01", location_id="B",
            timestamp="2026-11-26T08:05:00+00:00",
        )))
        summary = tracker.get_summary()
        self.assertEqual(summary["total_alerts"], 3)
        self.assertEqual(summary["warning_count"], 2)
        self.assertEqual(summary["critical_count"], 1)
        self.assertEqual(summary["by_location"]["A"], {
            "WARNING": 1, "CRITICAL": 1, "total": 2,
        })
        self.assertEqual(summary["by_location"]["B"], {
            "WARNING": 1, "CRITICAL": 0, "total": 1,
        })

    def test_single_event_when_both_metrics_violated(self):
        tracker = StatisticsTracker("TEST-02")
        self.assertTrue(tracker.record_alert(make_alert(
            severity="CRITICAL",
            violated_metrics=["temperature", "humidity"],
            temperature=14.0,
            humidity=70.0,
        )))
        summary = tracker.get_summary()
        self.assertEqual(summary["total_alerts"], 1)
        self.assertEqual(summary["critical_count"], 1)
        self.assertEqual(summary["warning_count"], 0)

    def test_deduplication_by_sensor_id_and_timestamp(self):
        tracker = StatisticsTracker("TEST-03")
        alert = make_alert(sensor_id="S-C01", location_id="C")
        self.assertTrue(tracker.record_alert(alert))
        self.assertFalse(tracker.record_alert(alert))
        self.assertTrue(tracker.record_alert(make_alert(
            sensor_id="S-C01", location_id="C",
            timestamp="2026-11-26T08:05:00+00:00", severity="CRITICAL",
        )))
        self.assertEqual(tracker.get_summary()["total_alerts"], 2)

    def test_record_error_separated_from_environmental_alerts(self):
        tracker = StatisticsTracker("TEST-04")
        tracker.record_alert(make_alert())
        tracker.record_error({
            "kind": "DISCONNECT",
            "sensor_id": "S-B02",
            "location_id": "B",
            "timestamp": "2026-11-26T08:01:00+00:00",
            "message": "sensor disconnected",
        })
        summary = tracker.get_summary()
        self.assertEqual(summary["total_alerts"], 1)
        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(summary["errors_by_type"], {"DISCONNECT": 1})

    def test_export_csv_and_json_to_provided_paths(self):
        tracker = StatisticsTracker("TEST-05")
        tracker.record_alert(make_alert(severity="CRITICAL"))
        tracker.record_error({
            "kind": "INVALID_DATA",
            "sensor_id": "S-A03",
            "location_id": "A",
            "timestamp": "2026-11-26T08:01:00+00:00",
            "message": "invalid data",
        })
        with tempfile.TemporaryDirectory() as directory:
            csv_file = Path(directory) / "alert_logs.csv"
            json_file = Path(directory) / "report.json"
            tracker.export_csv(str(csv_file))
            tracker.export_json(str(json_file))
            with csv_file.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            data = json.loads(json_file.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["severity"], "CRITICAL")
        self.assertEqual(data["summary"]["session_id"], "TEST-05")
        self.assertEqual(data["summary"]["error_count"], 1)

    def test_invalid_alert_raises_error(self):
        tracker = StatisticsTracker("TEST-06")
        with self.assertRaises((TypeError, ValueError)):
            tracker.record_alert({"sensor_id": "S-A01"})


if __name__ == "__main__":
    unittest.main()
