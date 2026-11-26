"""Request-scoped service tai su dung Stable Python Core."""

import copy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from alert_system import AlertSystem
from config import SENSOR_PROFILES, SIMULATION_START_TIME
from integration_adapters import AlertAdapter, DemoSimulation, SimulationAdapter
from main import create_default_manager, create_step_timestamp, run_simulation
from statistics_tracker import StatisticsTracker
from web_api.config import (
    API_VERSION,
    CORE_VERSION,
    DEMO_STEP_COUNT,
    DEMO_STEP_INTERVAL_SECONDS,
)
from web_api.schemas import SimulationRunRequest
from web_api.services.snapshot_collector import SnapshotCollector


class SimulationService:
    """Chay mot simulation doc lap cho moi lan goi."""

    def run(
        self,
        request: SimulationRunRequest,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        request_id = request_id or str(uuid4())
        manager = create_default_manager()

        if request.mode == "demo":
            simulation = DemoSimulation()
            seed = None
            step_count = DEMO_STEP_COUNT
            interval = DEMO_STEP_INTERVAL_SECONDS
        else:
            seed = request.seed
            step_count = request.step_count
            interval = request.step_interval_seconds

            def status_provider(sensor_id: str) -> str:
                sensor = manager.get_sensor(sensor_id)
                return (
                    sensor.get_reading()["status"]
                    if sensor is not None else "ERROR"
                )

            simulation = SimulationAdapter(
                seed, copy.deepcopy(SENSOR_PROFILES), status_provider
            )

        collector = SnapshotCollector()
        tracker = StatisticsTracker(f"API-{request.mode}-{seed or 'DEMO'}")
        summary = run_simulation(
            manager=manager,
            simulation_engine=simulation,
            alert_system=AlertAdapter(AlertSystem()),
            statistics=tracker,
            display=collector,
            step_count=step_count,
            start_time=SIMULATION_START_TIME,
            step_seconds=interval,
            csv_path=None,
            json_path=None,
        )
        alerts = tracker.get_alerts()
        errors = tracker.get_errors()
        final_readings = manager.collect_readings()
        temperature_history, humidity_history = self._build_history(
            collector.timeline
        )
        return {
            "metadata": {
                "request_id": request_id,
                "api_version": API_VERSION,
                "core_version": CORE_VERSION,
                "mode": request.mode,
                "effective_seed": seed,
                "actual_step_count": step_count,
                "step_interval_seconds": float(interval),
                "simulated_start": SIMULATION_START_TIME,
                "simulated_end": create_step_timestamp(
                    SIMULATION_START_TIME, step_count - 1, interval
                ),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "timeline": collector.timeline,
            "readings": final_readings,
            "temperature_history": temperature_history,
            "humidity_history": humidity_history,
            "alerts": alerts,
            "errors": errors,
            "summary": summary,
            "statistics": {
                "by_location": copy.deepcopy(summary["by_location"]),
                "by_severity": {
                    "WARNING": summary["warning_count"],
                    "CRITICAL": summary["critical_count"],
                },
            },
        }

    @staticmethod
    def _build_history(
        timeline: list[dict[str, Any]],
    ) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
        temperatures: dict[str, list[dict]] = {}
        humidities: dict[str, list[dict]] = {}
        for step in timeline:
            for item in step["sensors"]:
                reading = item["reading"]
                sensor_id = reading["sensor_id"]
                common = {
                    "step_index": step["step_index"],
                    "simulated_at": step["simulated_at"],
                    "freshness": item["freshness"],
                }
                temperatures.setdefault(sensor_id, []).append({
                    **common, "value": reading["temperature"],
                })
                humidities.setdefault(sensor_id, []).append({
                    **common, "value": reading["humidity"],
                })
        return temperatures, humidities
