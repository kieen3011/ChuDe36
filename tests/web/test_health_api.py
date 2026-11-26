import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from tests.web.client import ApiClient
from web_api.app import create_app


class HealthApiTests(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient(create_app())

    def test_health_returns_public_version_fields(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ok",
            "api_version": "1",
            "core_version": "8428be8",
        })
        self.assertNotIn(os.getcwd(), response.text)

    def test_root_serves_frontend_without_openapi_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<html", response.text.lower())
        self.assertIn("IoT", response.text)
        self.assertNotIn("/", self.client.get("/openapi.json").json()["paths"])

    def test_openapi_can_be_disabled_by_environment(self):
        with patch.dict(os.environ, {"CHUDE36_DOCS_ENABLED": "0"}):
            client = ApiClient(create_app())
        self.assertEqual(client.get("/docs").status_code, 404)
        self.assertEqual(client.get("/openapi.json").status_code, 404)

    def test_openapi_lists_only_implemented_public_endpoints(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = set(response.json()["paths"])
        self.assertEqual(paths, {
            "/api/health",
            "/api/config",
            "/api/simulations/run",
        })

    def test_openapi_freezes_nested_response_and_error_schemas(self):
        schema = self.client.get("/openapi.json").json()
        components = schema["components"]["schemas"]
        response_schema = components["SimulationRunResponse"]["properties"]
        self.assertEqual(
            response_schema["readings"]["items"]["$ref"],
            "#/components/schemas/ReadingRecord",
        )
        self.assertEqual(
            response_schema["timeline"]["items"]["$ref"],
            "#/components/schemas/TimelineStep",
        )
        self.assertEqual(
            set(components["ReadingRecord"]["properties"]),
            {
                "sensor_id", "sensor_type", "location_id", "status",
                "temperature", "humidity", "timestamp",
            },
        )
        responses = schema["paths"]["/api/simulations/run"]["post"]["responses"]
        self.assertEqual(
            responses["422"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/CanonicalErrorResponse",
        )

    def test_import_has_no_console_side_effect(self):
        result = subprocess.run(
            [sys.executable, "-c", "import web_api.app"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
