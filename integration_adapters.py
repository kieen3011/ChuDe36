from __future__ import annotations

import math
from copy import deepcopy
from typing import Callable

from alert_system import AlertLevel, AlertSystem
from data_simulator import DataSimulator


ZONE_LABELS = {"A": "Khu A", "B": "Khu B", "C": "Khu C"}


class SimulationAdapter:
    """Chuyen du lieu TV2 thanh Simulation Event theo tung sensor."""

    def __init__(
        self,
        seed: str,
        sensor_profiles: dict,
        status_provider: Callable[[str], str] | None = None,
    ) -> None:
        self.seed = str(seed)
        self._profiles = deepcopy(sensor_profiles)
        self._status_provider = status_provider
        self._outages: set[str] = set()
        self._simulators = {
            sensor_id: DataSimulator(f"{self.seed}:{sensor_id}")
            for sensor_id in self._profiles
        }

    @staticmethod
    def _event(kind, sensor_id, timestamp, temperature=None, humidity=None):
        return {
            "kind": kind,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "temperature": temperature,
            "humidity": humidity,
        }

    @staticmethod
    def _is_invalid(temperature, humidity):
        values = (temperature, humidity)
        if any(isinstance(value, bool) for value in values):
            return True
        if not all(isinstance(value, (int, float)) for value in values):
            return True
        if not all(math.isfinite(value) for value in values):
            return True
        return not (-50.0 <= temperature <= 100.0 and 0.0 <= humidity <= 100.0)

    def _status(self, sensor_id):
        if self._status_provider is not None:
            return self._status_provider(sensor_id)
        return "ERROR" if sensor_id in self._outages else "ACTIVE"

    def generate_events(self, step_index: int, timestamp: str) -> list[dict]:
        """Sinh toi da mot event cho moi sensor theo thu tu ID."""
        events = []
        for sensor_id in sorted(self._profiles):
            profile = self._profiles[sensor_id]
            status = self._status(sensor_id)
            if status == "INACTIVE":
                continue

            incident = profile.get("incident_schedule", {}).get(step_index)
            simulator = self._simulators[sensor_id]
            zone_label = ZONE_LABELS.get(
                profile["location_id"], profile["location_id"]
            )
            if incident == "DISCONNECT":
                temperature, humidity = None, None
            elif incident == "INVALID_DATA":
                temperature, humidity = -999.0, -999.0
            else:
                temperature, humidity = simulator.next_reading(
                    zone_label,
                    profile.get("inject_noise_prob", 0.0),
                    profile.get("inject_disconnect_prob", 0.0),
                )

            if temperature is None or humidity is None:
                if sensor_id not in self._outages and status != "ERROR":
                    self._outages.add(sensor_id)
                    events.append(self._event("DISCONNECT", sensor_id, timestamp))
                else:
                    self._outages.add(sensor_id)
                continue

            if self._is_invalid(temperature, humidity):
                events.append(
                    self._event(
                        "INVALID_DATA", sensor_id, timestamp, temperature, humidity
                    )
                )
                continue

            if sensor_id in self._outages or status == "ERROR":
                self._outages.discard(sensor_id)
                events.append(self._event("RECOVER", sensor_id, timestamp))
                continue

            events.append(
                self._event(
                    "READING", sensor_id, timestamp, temperature, humidity
                )
            )
        return events


class AlertAdapter:
    """Chuyen Reading Record thanh Alert Record co cau truc."""

    def __init__(self, alert_system: AlertSystem) -> None:
        self._alert_system = alert_system

    def evaluate(self, reading: dict) -> dict | None:
        level, metrics = self._alert_system.evaluate_metrics(
            reading["location_id"],
            reading["temperature"],
            reading["humidity"],
        )
        if level == AlertLevel.NORMAL:
            return None
        return {
            "sensor_id": reading["sensor_id"],
            "location_id": reading["location_id"],
            "timestamp": reading["timestamp"],
            "severity": level.name,
            "violated_metrics": metrics,
            "temperature": reading["temperature"],
            "humidity": reading["humidity"],
        }


class DemoSimulation:
    """Phat chuoi event xac dinh qua cung pipeline production."""

    _EVENTS = {
        0: ("READING", "COLD-01", 5.0, 90.0),
        1: ("READING", "COLD-01", 9.0, 90.0),
        2: ("READING", "COLD-01", 12.0, 70.0),
        3: ("READING", "DRY-01", 22.0, 60.0),
        4: ("READING", "SERVER-01", 33.0, 50.0),
        5: ("DISCONNECT", "COLD-01", None, None),
        6: ("DISCONNECT", "COLD-01", None, None),
        7: ("RECOVER", "COLD-01", None, None),
        8: ("INVALID_DATA", "COLD-01", -999.0, -999.0),
        9: ("READING", "COLD-01", 5.0, 90.0),
    }

    def generate_events(self, step_index: int, timestamp: str) -> list[dict]:
        """Tao mot event demo cho buoc hien tai."""
        definition = self._EVENTS.get(step_index)
        if definition is None:
            return []
        kind, sensor_id, temperature, humidity = definition
        return [{
            "kind": kind,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "temperature": temperature,
            "humidity": humidity,
        }]


def create_display_summary(summary: dict) -> dict:
    """Tao compatibility view cho TV5 ma khong mutate summary goc."""
    view = deepcopy(summary)
    if "error_count" in view:
        view["total_errors"] = view["error_count"]
    return view
