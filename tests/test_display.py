"""Kiem thu giao dien console theo G0."""

import io
import unittest
from contextlib import redirect_stdout
from copy import deepcopy

from tests.fixtures import make_alert, make_reading


class DisplayTestCase(unittest.TestCase):
    def capture(self, function, *args):
        """Thu stdout cua ham hien thi."""
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = function(*args)
        return result, stream.getvalue()

    def test_render_snapshot_shows_active_normal_reading(self):
        from display import render_snapshot

        reading = make_reading()
        result, output = self.capture(render_snapshot, [reading], [], 0)

        self.assertIsNone(result)
        self.assertIn("COLD-01", output)
        self.assertIn("COLD_STORAGE", output)
        self.assertIn("ACTIVE", output)
        self.assertIn("5.0", output)
        self.assertIn("90.0", output)
        self.assertIn("NORMAL", output)

    def test_render_snapshot_shows_active_critical_alert(self):
        from display import render_snapshot

        reading = make_reading(temperature=12.0, humidity=90.0)
        alert = make_alert(severity="CRITICAL", temperature=12.0, humidity=90.0)

        _, output = self.capture(render_snapshot, [reading], [alert], 4)

        self.assertIn("CRITICAL", output)

    def test_render_snapshot_matches_current_alert_by_sensor_id(self):
        from display import render_snapshot

        first = make_reading()
        second = make_reading(
            sensor_id="DRY-01",
            sensor_type="DRY_STORAGE",
            location_id="B",
            temperature=25.1,
            humidity=59.0,
        )
        alert = make_alert(
            sensor_id="DRY-01",
            location_id="B",
            severity="WARNING",
            temperature=25.1,
            humidity=59.0,
        )

        _, output = self.capture(render_snapshot, [first, second], [alert], 1)
        dry_line = next(line for line in output.splitlines() if "DRY-01" in line)
        cold_line = next(line for line in output.splitlines() if "COLD-01" in line)

        self.assertIn("WARNING", dry_line)
        self.assertIn("NORMAL", cold_line)

    def test_render_snapshot_marks_stale_value_for_non_active_sensor(self):
        from display import render_snapshot

        reading = make_reading(status="ERROR")
        _, output = self.capture(render_snapshot, [reading], [], 3)

        self.assertIn("ERROR", output)
        self.assertIn("N/A", output)
        self.assertIn("(gia tri cu)", output)

    def test_render_snapshot_uses_na_for_missing_measurement(self):
        from display import render_snapshot

        reading = make_reading(
            status="INACTIVE", temperature=None, humidity=None, timestamp=None
        )
        _, output = self.capture(render_snapshot, [reading], [], 2)

        sensor_line = next(line for line in output.splitlines() if "COLD-01" in line)
        self.assertGreaterEqual(sensor_line.count("N/A"), 3)
        self.assertNotIn("(gia tri cu)", sensor_line)

    def test_render_summary_outputs_counts_without_mutating_input(self):
        from display import render_summary

        summary = {
            "total_alerts": 2,
            "total_errors": 1,
            "by_location": {
                "A": {"WARNING": 1, "CRITICAL": 1, "total": 2}
            },
            "errors_by_type": {"DISCONNECT": 1},
        }
        original = deepcopy(summary)

        result, output = self.capture(render_summary, summary)

        self.assertIsNone(result)
        self.assertIn("TONG KET", output)
        self.assertIn("Tong canh bao: 2", output)
        self.assertIn("Tong loi: 1", output)
        self.assertIn("A", output)
        self.assertIn("DISCONNECT", output)
        self.assertEqual(original, summary)

    def test_render_summary_handles_empty_breakdowns(self):
        from display import render_summary

        summary = {
            "total_alerts": 0,
            "total_errors": 0,
            "by_location": {},
            "errors_by_type": {},
        }

        _, output = self.capture(render_summary, summary)

        self.assertIn("Khong co canh bao moi truong.", output)
        self.assertIn("Khong co loi he thong.", output)

    def test_render_snapshot_does_not_mutate_inputs(self):
        from display import render_snapshot

        readings = [make_reading()]
        alerts = [make_alert()]
        original_readings = deepcopy(readings)
        original_alerts = deepcopy(alerts)

        self.capture(render_snapshot, readings, alerts, 0)

        self.assertEqual(original_readings, readings)
        self.assertEqual(original_alerts, alerts)


if __name__ == "__main__":
    unittest.main()