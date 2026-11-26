import json
import math
import unittest

from tests.web.client import ApiClient
from web_api.app import create_app
from web_api.services.snapshot_collector import SnapshotCollector


class SimulationApiTests(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient(create_app())

    def test_demo_returns_approved_pipeline_results_and_timeline(self):
        response = self.client.post("/api/simulations/run", json={"mode": "demo"})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["metadata"]["mode"], "demo")
        self.assertEqual(data["metadata"]["actual_step_count"], 10)
        self.assertEqual(len(data["timeline"]), 10)
        self.assertEqual(data["summary"]["total_alerts"], 4)
        self.assertEqual(data["summary"]["warning_count"], 2)
        self.assertEqual(data["summary"]["critical_count"], 2)
        self.assertEqual(data["summary"]["error_count"], 2)
        self.assertEqual(set(data["summary"]["by_location"]), {"A", "B", "C"})
        self.assertTrue(any(len(item["violated_metrics"]) == 2 for item in data["alerts"]))
        self.assertEqual(len(data["temperature_history"]), 3)
        self.assertEqual(len(data["humidity_history"]), 3)
        json.dumps(data, allow_nan=False)

    def test_random_request_is_deterministic_except_response_identity(self):
        payload = {
            "mode": "random",
            "seed": "API-TEST",
            "step_count": 10,
            "step_interval_seconds": 30,
        }
        first = self.client.post("/api/simulations/run", json=payload).json()
        second = self.client.post("/api/simulations/run", json=payload).json()
        self.assertEqual(first["timeline"], second["timeline"])
        self.assertEqual(first["summary"]["total_alerts"], second["summary"]["total_alerts"])
        self.assertNotEqual(first["metadata"]["request_id"], second["metadata"]["request_id"])

    def test_timeline_has_actual_events_errors_and_cumulative_summary(self):
        data = self.client.post("/api/simulations/run", json={"mode": "demo"}).json()
        disconnect = data["timeline"][5]
        repeated = data["timeline"][6]
        recovery = data["timeline"][7]
        invalid = data["timeline"][8]
        self.assertEqual(disconnect["events"][0]["kind"], "DISCONNECT")
        self.assertEqual(disconnect["errors"][0]["kind"], "DISCONNECT")
        self.assertEqual(repeated["events"][0]["kind"], "DISCONNECT")
        self.assertEqual(repeated["errors"], [])
        self.assertEqual(recovery["events"][0]["kind"], "RECOVER")
        cold = next(item for item in recovery["sensors"] if item["reading"]["sensor_id"] == "COLD-01")
        self.assertEqual(cold["freshness"], "RECOVERY_PENDING")
        self.assertEqual(invalid["errors"][0]["kind"], "INVALID_DATA")
        self.assertEqual(disconnect["cumulative_summary"]["error_count"], 1)
        self.assertEqual(invalid["cumulative_summary"]["error_count"], 2)

    def test_snapshot_history_is_not_mutated_by_later_steps(self):
        data = self.client.post("/api/simulations/run", json={"mode": "demo"}).json()
        first = next(item for item in data["timeline"][0]["sensors"] if item["reading"]["sensor_id"] == "COLD-01")
        last = next(item for item in data["timeline"][-1]["sensors"] if item["reading"]["sensor_id"] == "COLD-01")
        self.assertEqual(first["reading"]["temperature"], 5.0)
        self.assertEqual(first["reading"]["timestamp"], data["timeline"][0]["simulated_at"])
        self.assertIsNot(first["reading"], last["reading"])

    def test_simulation_response_disables_caching(self):
        response = self.client.post("/api/simulations/run", json={"mode": "demo"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_request_id_header_matches_response_metadata(self):
        response = self.client.post(
            "/api/simulations/run",
            json={"mode": "random", "seed": "request-id", "step_count": 1},
            headers={"X-Request-ID": "client-request-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-request-id"], "client-request-123")
        self.assertEqual(
            response.json()["metadata"]["request_id"],
            "client-request-123",
        )


class SnapshotCollectorTests(unittest.TestCase):
    def test_active_old_reading_without_recovery_is_stale(self):
        collector = SnapshotCollector()
        reading = {
            "sensor_id": "S1",
            "sensor_type": "COLD_STORAGE",
            "location_id": "A",
            "status": "ACTIVE",
            "temperature": 5.0,
            "humidity": 90.0,
            "timestamp": "2026-01-01T00:00:00",
        }
        collector.record_step(
            step_index=1,
            timestamp="2026-01-01T00:01:00",
            events=[],
            readings=[reading],
            alerts=[],
            errors=[],
            cumulative_summary={},
        )
        self.assertEqual(
            collector.timeline[0]["sensors"][0]["freshness"],
            "STALE",
        )


if __name__ == "__main__":
    unittest.main()
