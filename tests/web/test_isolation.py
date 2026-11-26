import concurrent.futures
import pathlib
import tempfile
import unittest

from tests.web.client import ApiClient
from web_api.app import create_app


class IsolationTests(unittest.TestCase):
    def run_request(self, seed):
        response = ApiClient(create_app()).post("/api/simulations/run", json={
            "mode": "random",
            "seed": seed,
            "step_count": 20,
            "step_interval_seconds": 1,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_parallel_requests_are_isolated(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            first, second, first_again, demo = list(executor.map(
                lambda item: self.run_request(item) if item != "DEMO" else ApiClient(create_app()).post("/api/simulations/run", json={"mode": "demo"}).json(),
                ["ONE", "TWO", "ONE", "DEMO"],
            ))
        self.assertEqual(first["timeline"], first_again["timeline"])
        self.assertNotEqual(first["timeline"], second["timeline"])
        self.assertEqual(demo["summary"]["total_alerts"], 4)
        self.assertEqual(len({first["metadata"]["request_id"], second["metadata"]["request_id"], first_again["metadata"]["request_id"], demo["metadata"]["request_id"]}), 4)

    def test_http_run_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as directory:
            before = set(pathlib.Path(directory).iterdir())
            old_cwd = pathlib.Path.cwd()
            try:
                import os
                os.chdir(directory)
                response = ApiClient(create_app()).post("/api/simulations/run", json={"mode": "demo"})
            finally:
                os.chdir(old_cwd)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(pathlib.Path(directory).iterdir()), before)


if __name__ == "__main__":
    unittest.main()
