"""Pure serializer khong doc hoac ghi filesystem."""

import csv
import io
import json
from typing import Any


ALERT_FIELDS = [
    "sensor_id", "location_id", "timestamp", "severity",
    "violated_metrics", "temperature", "humidity",
]


def serialize_alerts_csv(alerts: list[dict[str, Any]]) -> str:
    """Serialize canonical alerts thanh CSV trong bo nho."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=ALERT_FIELDS)
    writer.writeheader()
    for alert in alerts:
        row = dict(alert)
        row["violated_metrics"] = ",".join(alert["violated_metrics"])
        writer.writerow(row)
    return stream.getvalue()


def serialize_report_json(report: dict[str, Any]) -> str:
    """Serialize report thanh strict JSON trong bo nho."""
    return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
