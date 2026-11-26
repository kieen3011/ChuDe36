from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_SEVERITIES = {"WARNING", "CRITICAL"}
SEVERITY_RANK = {"WARNING": 1, "CRITICAL": 2}
REQUIRED_ALERT_FIELDS = {
    "sensor_id",
    "location_id",
    "timestamp",
    "severity",
    "violated_metrics",
    "temperature",
    "humidity",
}


class StatisticsTracker:
    """Module TV4: Thống kê cảnh báo vượt ngưỡng, ghi lỗi riêng và xuất CSV/JSON."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or datetime.now(timezone.utc).strftime("SIM-%Y%m%dT%H%M%SZ")
        self._seen_keys: set[tuple[str, str]] = set()
        self._alerts: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []
        self._by_location: dict[str, dict[str, int]] = {}
        self._total_warning: int = 0
        self._total_critical: int = 0

    def record_alert(self, alert: dict[str, Any]) -> bool:
        """
        Ghi nhận một Alert Record từ TV3.
        Trả về True nếu thêm mới thành công, False nếu trùng khóa (sensor_id, timestamp).
        """
        if not isinstance(alert, dict):
            raise TypeError("alert must be a dict")

        missing = REQUIRED_ALERT_FIELDS - set(alert.keys())
        if missing:
            raise ValueError(f"Missing required alert fields: {sorted(missing)}")

        sensor_id = alert["sensor_id"]
        location_id = alert["location_id"]
        timestamp = alert["timestamp"]
        severity = alert["severity"]

        if not isinstance(sensor_id, str) or not sensor_id.strip():
            raise ValueError("sensor_id must be a non-empty string")
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("timestamp must be a non-empty string")
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'; expected WARNING or CRITICAL")

        dedup_key = (sensor_id, timestamp)
        if dedup_key in self._seen_keys:
            return False

        self._seen_keys.add(dedup_key)

        violated_metrics = alert["violated_metrics"]
        if not isinstance(violated_metrics, (list, tuple)):
            raise ValueError("violated_metrics must be a list or tuple")

        record = {
            "sensor_id": sensor_id,
            "location_id": location_id,
            "timestamp": timestamp,
            "severity": severity,
            "violated_metrics": list(violated_metrics),
            "temperature": alert["temperature"],
            "humidity": alert["humidity"],
        }
        self._alerts.append(record)

        if location_id not in self._by_location:
            self._by_location[location_id] = {"WARNING": 0, "CRITICAL": 0, "total": 0}

        self._by_location[location_id][severity] += 1
        self._by_location[location_id]["total"] += 1

        if severity == "WARNING":
            self._total_warning += 1
        else:
            self._total_critical += 1

        return True

    def record_error(self, error: dict[str, Any]) -> None:
        """Ghi nhận lỗi thiết bị/dữ liệu tách biệt khỏi thống kê vượt ngưỡng môi trường."""
        if not isinstance(error, dict):
            raise TypeError("error must be a dict")
        json.dumps(error, allow_nan=False)
        self._errors.append(dict(error))

    def get_summary(self) -> dict[str, Any]:
        """Trả về bảng tổng hợp thống kê cuối phiên cho orchestrator và TV5."""
        return {
            "session_id": self.session_id,
            "total_alerts": len(self._alerts),
            "warning_count": self._total_warning,
            "critical_count": self._total_critical,
            "error_count": len(self._errors),
            "by_location": {
                loc: dict(counts) for loc, counts in sorted(self._by_location.items())
            },
        }

    def export_csv(self, file_path: str) -> None:
        """Xuất lịch sử cảnh báo môi trường ra file CSV theo đường dẫn được cung cấp."""
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be a non-empty string")

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "sensor_id",
            "location_id",
            "timestamp",
            "severity",
            "violated_metrics",
            "temperature",
            "humidity",
        ]

        with path.open(mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in self._alerts:
                row = dict(item)
                row["violated_metrics"] = ",".join(str(m) for m in item["violated_metrics"])
                writer.writerow(row)

    def export_json(self, file_path: str) -> None:
        """Xuất thông tin phiên mô phỏng và tổng hợp theo vị trí/mức độ ra file JSON."""
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be a non-empty string")

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "summary": self.get_summary(),
            "alerts": list(self._alerts),
            "errors": list(self._errors),
        }

        with path.open(mode="w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)