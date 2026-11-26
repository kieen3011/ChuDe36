"""Collector headless luu timeline ma khong in console."""

import copy
from typing import Any


class SnapshotCollector:
    """Thu thap snapshot va summary doc lap theo tung buoc."""

    def __init__(self) -> None:
        self.timeline: list[dict[str, Any]] = []
        self.final_summary: dict[str, Any] | None = None

    @staticmethod
    def _freshness(
        reading: dict[str, Any],
        timestamp: str,
        recovered: bool,
    ) -> str:
        has_value = (
            reading.get("temperature") is not None
            or reading.get("humidity") is not None
        )
        if not has_value:
            return "NO_DATA"
        if reading.get("status") == "ACTIVE":
            if reading.get("timestamp") == timestamp:
                return "FRESH"
            return "RECOVERY_PENDING" if recovered else "STALE"
        return "STALE"

    def record_step(
        self,
        *,
        step_index: int,
        timestamp: str,
        events: list[dict],
        readings: list[dict],
        alerts: list[dict],
        errors: list[dict],
        cumulative_summary: dict,
    ) -> None:
        """Luu bang chung thuc cua buoc hien tai bang deep copy."""
        recovered_sensor_ids = {
            event.get("sensor_id")
            for event in events
            if event.get("kind") == "RECOVER"
        }
        sensors = [
            {
                "reading": copy.deepcopy(reading),
                "freshness": self._freshness(
                    reading,
                    timestamp,
                    reading.get("sensor_id") in recovered_sensor_ids,
                ),
            }
            for reading in readings
        ]
        self.timeline.append({
            "step_index": step_index,
            "simulated_at": timestamp,
            "events": copy.deepcopy(events),
            "sensors": sensors,
            "alerts": copy.deepcopy(alerts),
            "errors": copy.deepcopy(errors),
            "cumulative_summary": copy.deepcopy(cumulative_summary),
        })

    def render_snapshot(
        self,
        readings: list[dict],
        alerts: list[dict],
        step_index: int,
        current_timestamp: str | None = None,
    ) -> None:
        """Giu API renderer; record_step moi la nguon timeline."""

    def render_summary(self, summary: dict) -> None:
        """Luu final summary bang ban sao."""
        self.final_summary = copy.deepcopy(summary)
