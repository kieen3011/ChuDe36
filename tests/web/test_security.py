import json
import unittest

from tests.web.client import ApiClient
from web_api.app import create_app


class SecurityApiTests(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient(create_app())

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.text)
        data = response.json()
        self.assertEqual(data["error"]["code"], code)
        self.assertIn("request_id", data["error"])
        self.assertNotIn("Traceback", response.text)

    def test_invalid_mode_seed_steps_boolean_and_extra_fields(self):
        cases = [
            ({"mode": "other"}, 422),
            ({"mode": "random", "seed": ""}, 422),
            ({"mode": "random", "seed": "x" * 129}, 422),
            ({"mode": "random", "step_count": 0}, 422),
            ({"mode": "random", "step_count": 101}, 422),
            ({"mode": "random", "step_count": True}, 422),
            ({"mode": "random", "step_interval_seconds": True}, 422),
            ({"mode": "random", "path": "report.json"}, 422),
            ({"mode": "random", "thresholds": {}}, 422),
        ]
        for payload, status in cases:
            with self.subTest(payload=payload):
                self.assert_error(
                    self.client.post("/api/simulations/run", json=payload),
                    status,
                    "VALIDATION_ERROR",
                )

    def test_demo_rejects_conflicting_parameters(self):
        for field, value in (
            ("seed", "x"),
            ("step_count", 10),
            ("step_interval_seconds", 60),
        ):
            with self.subTest(field=field):
                self.assert_error(
                    self.client.post("/api/simulations/run", json={"mode": "demo", field: value}),
                    422,
                    "VALIDATION_ERROR",
                )

    def test_nan_and_infinity_are_rejected(self):
        for value in (math_value := [float("nan"), float("inf"), float("-inf")]):
            with self.subTest(value=repr(value)):
                response = self.client.post(
                    "/api/simulations/run",
                    content=json.dumps({"mode": "random", "step_interval_seconds": value}),
                    headers={"content-type": "application/json"},
                )
                self.assertIn(response.status_code, (400, 422))
                self.assertIn(response.json()["error"]["code"], ("MALFORMED_JSON", "VALIDATION_ERROR"))

    def test_malformed_json_has_canonical_error(self):
        response = self.client.post(
            "/api/simulations/run",
            content=b'{"mode":',
            headers={"content-type": "application/json"},
        )
        self.assert_error(response, 400, "MALFORMED_JSON")

    def test_internal_error_is_canonical_and_hides_details(self):
        app = create_app()

        @app.get("/api/test-internal-error")
        def fail_for_test():
            raise RuntimeError("sensitive-local-detail")

        response = ApiClient(app).get("/api/test-internal-error")
        self.assert_error(response, 500, "INTERNAL_ERROR")
        self.assertNotIn("sensitive-local-detail", response.text)

    def test_body_limit_with_and_without_content_length(self):
        oversized = b'{' + b' ' * 65536 + b'}'
        response = self.client.post(
            "/api/simulations/run",
            content=oversized,
            headers={"content-type": "application/json"},
        )
        self.assert_error(response, 413, "PAYLOAD_TOO_LARGE")

    def test_chunked_body_stops_reading_after_limit(self):
        yielded = []

        async def chunks():
            for index in range(1000):
                yielded.append(index)
                yield b"x" * 1024

        response = self.client.post(
            "/api/simulations/run",
            content=chunks(),
            headers={"content-type": "application/json"},
        )
        self.assert_error(response, 413, "PAYLOAD_TOO_LARGE")
        self.assertLess(len(yielded), 1000)

    def test_body_guard_errors_include_security_headers(self):
        response = self.client.post(
            "/api/simulations/run",
            content=b"x" * 65537,
            headers={"content-type": "application/json"},
        )
        self.assert_error(response, 413, "PAYLOAD_TOO_LARGE")
        self.assertIn("x-request-id", response.headers)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["cache-control"], "no-store")

        async def chunks():
            yield b'{"mode":"random","seed":"'
            yield b'x' * 65536
            yield b'"}'

        response = self.client.post(
            "/api/simulations/run",
            content=chunks(),
            headers={"content-type": "application/json"},
        )
        self.assert_error(response, 413, "PAYLOAD_TOO_LARGE")

    def test_cors_uses_explicit_development_origin(self):
        allowed = self.client.options(
            "/api/simulations/run",
            headers={
                "origin": "http://127.0.0.1:5173",
                "access-control-request-method": "POST",
            },
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["access-control-allow-origin"], "http://127.0.0.1:5173")
        denied = self.client.options(
            "/api/simulations/run",
            headers={
                "origin": "https://evil.example",
                "access-control-request-method": "POST",
            },
        )
        self.assertEqual(denied.status_code, 400)

    def test_untrusted_request_id_is_not_reflected(self):
        for value in ("with space", "x" * 129):
            with self.subTest(value=value[:20]):
                response = self.client.get(
                    "/api/health",
                    headers={"X-Request-ID": value},
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotEqual(response.headers["x-request-id"], value)
                self.assertLessEqual(len(response.headers["x-request-id"]), 128)


if __name__ == "__main__":
    unittest.main()
