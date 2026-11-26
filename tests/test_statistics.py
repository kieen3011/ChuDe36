from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from statistics import StatisticsTracker


def _make_alert(
    sensor_id: str = "S-A01",
    location_id: str = "A",
    timestamp: str = "2026-11-26T08:00:00+00:00",
    severity: str = "WARNING",
    violated_metrics: list[str] | None = None,
    temperature: float = 9.5,
    humidity: float = 88.0,
) -> dict:
    return {
        "sensor_id": sensor_id,
        "location_id": location_id,
        "timestamp": timestamp,
        "severity": severity,
        "violated_metrics": list(violated_metrics) if violated_metrics is not None else ["temperature"],
        "temperature": temperature,
        "humidity": humidity,
    }


def test_count_by_location_and_separate_severity():
    tracker = StatisticsTracker(session_id="TEST-01")
    assert tracker.record_alert(_make_alert("S-A01", "A", "2026-11-26T08:00:00+00:00", "WARNING")) is True
    assert tracker.record_alert(_make_alert("S-A01", "A", "2026-11-26T08:05:00+00:00", "CRITICAL")) is True
    assert tracker.record_alert(_make_alert("S-B01", "B", "2026-11-26T08:05:00+00:00", "WARNING")) is True

    summary = tracker.get_summary()
    assert summary["total_alerts"] == 3
    assert summary["warning_count"] == 2
    assert summary["critical_count"] == 1
    assert summary["by_location"]["A"] == {"WARNING": 1, "CRITICAL": 1, "total": 2}
    assert summary["by_location"]["B"] == {"WARNING": 1, "CRITICAL": 0, "total": 1}


def test_single_event_when_both_metrics_violated():
    tracker = StatisticsTracker(session_id="TEST-02")
    alert = _make_alert(
        sensor_id="S-A02",
        location_id="A",
        timestamp="2026-11-26T08:00:00+00:00",
        severity="CRITICAL",
        violated_metrics=["temperature", "humidity"],
        temperature=14.0,
        humidity=70.0,
    )
    assert tracker.record_alert(alert) is True

    summary = tracker.get_summary()
    assert summary["total_alerts"] == 1
    assert summary["critical_count"] == 1
    assert summary["warning_count"] == 0
    assert summary["by_location"]["A"]["total"] == 1


def test_deduplication_by_sensor_id_and_timestamp():
    tracker = StatisticsTracker(session_id="TEST-03")
    t1 = "2026-11-26T08:00:00+00:00"
    t2 = "2026-11-26T08:05:00+00:00"

    assert tracker.record_alert(_make_alert("S-C01", "C", t1, "WARNING")) is True
    assert tracker.record_alert(_make_alert("S-C01", "C", t1, "WARNING")) is False
    assert tracker.record_alert(_make_alert("S-C01", "C", t2, "CRITICAL")) is True

    summary = tracker.get_summary()
    assert summary["total_alerts"] == 2
    assert summary["warning_count"] == 1
    assert summary["critical_count"] == 1


def test_record_error_separated_from_environmental_alerts():
    tracker = StatisticsTracker(session_id="TEST-04")
    tracker.record_alert(_make_alert("S-A01", "A", "2026-11-26T08:00:00+00:00", "WARNING"))
    tracker.record_error({"sensor_id": "S-B02", "timestamp": "2026-11-26T08:01:00+00:00", "error_type": "DISCONNECT"})

    summary = tracker.get_summary()
    assert summary["total_alerts"] == 1
    assert summary["warning_count"] == 1
    assert summary["critical_count"] == 0
    assert summary["error_count"] == 1


def test_export_csv_and_json_to_provided_paths(tmp_path: Path):
    tracker = StatisticsTracker(session_id="TEST-05")
    tracker.record_alert(_make_alert("S-A01", "A", "2026-11-26T08:00:00+00:00", "CRITICAL", ["temperature"], 13.0, 89.0))
    tracker.record_error({"sensor_id": "S-A03", "error_type": "INVALID_DATA"})

    csv_file = tmp_path / "alert_logs.csv"
    json_file = tmp_path / "report.json"

    tracker.export_csv(str(csv_file))
    tracker.export_json(str(json_file))

    assert csv_file.exists()
    assert json_file.exists()

    with csv_file.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["sensor_id"] == "S-A01"
    assert rows[0]["severity"] == "CRITICAL"

    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["summary"]["session_id"] == "TEST-05"
    assert data["summary"]["total_alerts"] == 1
    assert data["summary"]["error_count"] == 1
    assert len(data["alerts"]) == 1
    assert len(data["errors"]) == 1


def test_invalid_alert_raises_error():
    tracker = StatisticsTracker(session_id="TEST-06")
    with pytest.raises((TypeError, ValueError)):
        tracker.record_alert({"sensor_id": "S-A01"})