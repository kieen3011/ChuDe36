from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


VALID_SEVERITIES = {"WARNING", "CRITICAL"}
REQUIRED_ALERT_FIELDS = {
    "sensor_id", "location_id", "timestamp", "severity",
    "violated_metrics", "temperature", "humidity",
}


def _validate_finite_number(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")


class StatisticsTracker:
    """Thong ke canh bao, loi he thong va xuat bao cao."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or datetime.now(timezone.utc).strftime(
            "SIM-%Y%m%dT%H%M%SZ"
        )
        self._seen_keys: set[tuple[str, str]] = set()
        self._alerts: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []
        self._by_location: dict[str, dict[str, int]] = {}
        self._errors_by_type: dict[str, int] = {}
        self._total_warning = 0
        self._total_critical = 0

    def record_alert(self, alert: dict[str, Any]) -> bool:
        """Ghi mot Alert Record hop le va bo qua khoa trung."""
        if not isinstance(alert, dict):
            raise TypeError("alert must be a dict")
        missing = REQUIRED_ALERT_FIELDS - set(alert)
        if missing:
            raise ValueError(f"Missing required alert fields: {sorted(missing)}")

        sensor_id = alert["sensor_id"]
        location_id = alert["location_id"]
        timestamp = alert["timestamp"]
        severity = alert["severity"]
        metrics = alert["violated_metrics"]
        if not isinstance(sensor_id, str) or not sensor_id.strip():
            raise ValueError("sensor_id must be a non-empty string")
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("timestamp must be a non-empty string")
        if severity not in VALID_SEVERITIES:
            raise ValueError("severity must be WARNING or CRITICAL")
        if not isinstance(metrics, (list, tuple)) or not metrics:
            raise ValueError("violated_metrics must be a non-empty list or tuple")
        if any(metric not in {"temperature", "humidity"} for metric in metrics):
            raise ValueError("violated_metrics contains unsupported values")
        _validate_finite_number(alert["temperature"], "temperature")
        _validate_finite_number(alert["humidity"], "humidity")

        record = {
            "sensor_id": sensor_id,
            "location_id": location_id,
            "timestamp": timestamp,
            "severity": severity,
            "violated_metrics": list(metrics),
            "temperature": float(alert["temperature"]),
            "humidity": float(alert["humidity"]),
        }
        json.dumps(record, allow_nan=False)
        key = (sensor_id, timestamp)
        if key in self._seen_keys:
            return False

        self._seen_keys.add(key)
        self._alerts.append(record)
        counts = self._by_location.setdefault(
            location_id, {"WARNING": 0, "CRITICAL": 0, "total": 0}
        )
        counts[severity] += 1
        counts["total"] += 1
        if severity == "WARNING":
            self._total_warning += 1
        else:
            self._total_critical += 1
        return True

    def record_error(self, error: dict[str, Any]) -> None:
        """Ghi Error Record tach biet khoi canh bao moi truong."""
        if not isinstance(error, dict):
            raise TypeError("error must be a dict")
        kind = error.get("kind", error.get("error_type"))
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("error kind must be a non-empty string")
        record = dict(error)
        record["kind"] = kind
        for field_name in ("sensor_id", "location_id"):
            value = record.get(field_name)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{field_name} must be a non-empty string or None")
        timestamp = record.get("timestamp")
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO 8601 string")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error_value:
            raise ValueError("timestamp must use ISO 8601 format") from error_value
        message = record.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        json.dumps(record, allow_nan=False)
        self._errors.append(record)
        self._errors_by_type[kind] = self._errors_by_type.get(kind, 0) + 1

    def get_summary(self) -> dict[str, Any]:
        """Tra Summary Record moi, khong lam lo state noi bo."""
        return {
            "session_id": self.session_id,
            "total_alerts": len(self._alerts),
            "warning_count": self._total_warning,
            "critical_count": self._total_critical,
            "error_count": len(self._errors),
            "by_location": {
                location: dict(counts)
                for location, counts in sorted(self._by_location.items())
            },
            "errors_by_type": dict(sorted(self._errors_by_type.items())),
        }

    def get_alerts(self) -> list[dict[str, Any]]:
        """Tra ban sao cac canh bao theo thu tu ghi nhan."""
        return [
            {**item, "violated_metrics": list(item["violated_metrics"])}
            for item in self._alerts
        ]

    def get_errors(self) -> list[dict[str, Any]]:
        """Tra ban sao cac loi theo thu tu ghi nhan."""
        return [dict(item) for item in self._errors]

    @staticmethod
    def _prepare_paths(file_path: str) -> tuple[Path, Path]:
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be a non-empty string")
        path = Path(file_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
        )
        temp_path = Path(handle.name)
        handle.close()
        return path, temp_path

    @staticmethod
    def _replace_file(temp_path: Path, path: Path) -> None:
        """Thay file dich nguyen tu hoac truyen loi ve caller."""
        os.replace(temp_path, path)

    def export_csv(self, file_path: str) -> None:
        """Xuat CSV bang cach ghi file nguyen tu."""
        path, temp_path = self._prepare_paths(file_path)
        fields = [
            "sensor_id", "location_id", "timestamp", "severity",
            "violated_metrics", "temperature", "humidity",
        ]
        try:
            with temp_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for item in self._alerts:
                    row = dict(item)
                    row["violated_metrics"] = ",".join(item["violated_metrics"])
                    writer.writerow(row)
                stream.flush()
                os.fsync(stream.fileno())
            self._replace_file(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def export_json(self, file_path: str) -> None:
        """Xuat JSON hop le bang cach ghi file nguyen tu."""
        path, temp_path = self._prepare_paths(file_path)
        payload = {
            "summary": self.get_summary(),
            "alerts": [dict(item) for item in self._alerts],
            "errors": [dict(item) for item in self._errors],
        }
        try:
            with temp_path.open("w", encoding="utf-8") as stream:
                json.dump(
                    payload, stream, ensure_ascii=False, indent=2, allow_nan=False
                )
                stream.flush()
                os.fsync(stream.fileno())
            self._replace_file(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
