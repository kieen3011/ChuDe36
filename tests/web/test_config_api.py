import copy
import os
import unittest
from unittest.mock import patch

from alert_system import DEFAULT_THRESHOLDS
from tests.web.client import ApiClient
from web_api.app import create_app


class ConfigApiTests(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient(create_app())

    def test_config_exposes_approved_defaults_limits_and_capabilities(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["modes"], ["random", "demo"])
        self.assertEqual(data["defaults"]["step_count"], 10)
        self.assertEqual(data["limits"]["step_count_max"], 100)
        self.assertEqual(data["limits"]["request_body_bytes"], 65536)
        self.assertEqual(set(data["thresholds"]), {"A", "B", "C"})
        self.assertFalse(data["capabilities"]["custom_thresholds"])
        self.assertFalse(data["capabilities"]["server_export"])

    def test_config_response_does_not_mutate_core_thresholds(self):
        original = copy.deepcopy(DEFAULT_THRESHOLDS)
        first = self.client.get("/api/config").json()
        first["thresholds"]["A"]["temp_max"] = 999
        second = self.client.get("/api/config").json()
        self.assertEqual(second["thresholds"]["A"]["temp_max"], 8.0)
        self.assertEqual(DEFAULT_THRESHOLDS, original)

    def test_config_reports_when_openapi_is_disabled(self):
        with patch.dict(os.environ, {"CHUDE36_DOCS_ENABLED": "0"}):
            client = ApiClient(create_app())
            response = client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["capabilities"]["openapi"])


if __name__ == "__main__":
    unittest.main()
