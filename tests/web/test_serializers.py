import csv
import io
import json
import unittest

from web_api.services.serializers import serialize_alerts_csv, serialize_report_json


class SerializerTests(unittest.TestCase):
    def test_csv_and_json_are_in_memory_and_canonical(self):
        report = {
            "alerts": [{
                "sensor_id": "S1",
                "location_id": "A",
                "timestamp": "2026-11-24T08:00:00+07:00",
                "severity": "WARNING",
                "violated_metrics": ["temperature"],
                "temperature": 9.0,
                "humidity": 90.0,
            }],
            "errors": [],
            "summary": {"total_alerts": 1},
        }
        csv_text = serialize_alerts_csv(report["alerts"])
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        self.assertEqual(rows[0]["violated_metrics"], "temperature")
        json_text = serialize_report_json(report)
        self.assertEqual(json.loads(json_text), report)
        self.assertNotIn("NaN", json_text)

    def test_json_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            serialize_report_json({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
