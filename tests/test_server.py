from __future__ import annotations

import copy
import http.client
import json
import sys
import threading
import unittest
from http.server import HTTPServer, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kairos_ai.engine import KairosRanker, ModelArtifactError
from kairos_ai.server import MAX_REQUEST_BODY_BYTES, handler_factory


class _FailingRanker:
    def score(self, _snapshot):
        raise ModelArtifactError("C:\\private\\artifacts\\secret-model-hash")


class ServerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(
            (ROOT / "examples" / "input_snapshot.json").read_text(encoding="utf-8")
        )
        cls.ranker = KairosRanker(ROOT / "artifacts" / "kairos_final.cbm")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.ranker))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.host, cls.port = cls.server.server_address

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, payload=None, headers=None):
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            request_headers.setdefault("Content-Type", "application/json")
        for attempt in range(2):
            connection = http.client.HTTPConnection(self.host, self.port, timeout=20)
            try:
                connection.request(method, path, body=body, headers=request_headers)
                response = connection.getresponse()
                raw = response.read()
                return response.status, dict(response.getheaders()), raw
            except (ConnectionAbortedError, ConnectionResetError):
                if attempt == 1:
                    raise
            finally:
                connection.close()

    def test_canonical_response_metadata_and_direct_engine_match(self):
        status, _, raw = self.request("POST", "/score", self.snapshot)
        body = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(
            body["metadata"],
            {
                "review_budget_count": 14,
                "review_budget_fraction": 0.1,
                "total_targets": 134,
            },
        )
        self.assertEqual(body["results"], self.ranker.score(self.snapshot))

    def test_capacity_metadata_matches_ceil_contract(self):
        for fraction, expected in ((0.05, 7), (0.1, 14), (0.2, 27), (1, 134)):
            with self.subTest(fraction=fraction):
                snapshot = copy.deepcopy(self.snapshot)
                snapshot["review_budget_fraction"] = fraction
                status, _, raw = self.request("POST", "/score", snapshot)
                body = json.loads(raw)
                self.assertEqual(status, 200)
                self.assertEqual(body["metadata"]["review_budget_count"], expected)
                self.assertEqual(
                    sum(
                        item["decision"] == "WINDOW_REVIEW"
                        for item in body["results"]
                    ),
                    expected,
                )

    def test_repeated_api_bytes_are_deterministic(self):
        first = self.request("POST", "/score", self.snapshot)
        second = self.request("POST", "/score", self.snapshot)
        self.assertEqual(first[0], 200)
        self.assertEqual(first[2], second[2])

    def test_invalid_json_snapshot_and_media_type(self):
        status, _, raw = self.request("POST", "/score", b"{not-json")
        self.assertEqual((status, json.loads(raw)["error"]), (400, "invalid_json"))

        status, _, raw = self.request(
            "POST", "/score", b"{}", {"Content-Type": "text/plain"}
        )
        self.assertEqual(
            (status, json.loads(raw)["error"]), (415, "unsupported_media_type")
        )

        invalid = copy.deepcopy(self.snapshot)
        invalid["tasks"][0]["pickup_time"] = "forbidden"
        status, _, raw = self.request("POST", "/score", invalid)
        self.assertEqual(
            (status, json.loads(raw)["error"]), (400, "invalid_snapshot")
        )

        invalid = copy.deepcopy(self.snapshot)
        invalid["tasks"][0]["task_lng"] = 181
        status, _, raw = self.request("POST", "/score", invalid)
        self.assertEqual(
            (status, json.loads(raw)["error"]), (400, "invalid_snapshot")
        )

    def test_oversized_declared_body_is_rejected_before_read(self):
        server = HTTPServer(("127.0.0.1", 0), handler_factory(self.ranker))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.putrequest("POST", "/score")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(MAX_REQUEST_BODY_BYTES + 1))
            connection.endheaders()
            response = connection.getresponse()
            raw = response.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(
            (response.status, json.loads(raw)["error"]),
            (413, "request_too_large"),
        )

    def test_unknown_endpoints_are_not_found(self):
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                payload = {} if method == "POST" else None
                status, _, raw = self.request(method, "/unknown", payload)
                self.assertEqual(
                    (status, json.loads(raw)["error"]), (404, "not_found")
                )

    def test_model_failure_is_generic_and_does_not_leak_details(self):
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), handler_factory(_FailingRanker())
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            connection = http.client.HTTPConnection(host, port, timeout=5)
            payload = json.dumps(self.snapshot).encode()
            connection.request(
                "POST",
                "/score",
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(response.status, 503)
        self.assertEqual(json.loads(raw), {"error": "model_unavailable"})
        text = raw.decode().lower()
        self.assertNotIn("traceback", text)
        self.assertNotIn("private", text)
        self.assertNotIn("secret-model-hash", text)

    def test_security_headers_cover_json_and_static_assets(self):
        for method, path, payload in (
            ("GET", "/", None),
            ("GET", "/app.js", None),
            ("GET", "/styles.css", None),
            ("GET", "/health", None),
            ("POST", "/score", self.snapshot),
        ):
            with self.subTest(path=path):
                status, headers, _ = self.request(method, path, payload)
                self.assertEqual(status, 200)
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
                self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_benchmark_shaped_10000_target_payload_fits_documented_cap(self):
        template = copy.deepcopy(self.snapshot["tasks"][0])
        tasks = []
        target_ids = []
        for index in range(10_000):
            task = copy.deepcopy(template)
            task_id = f"benchmark-{index:05d}"
            task["task_id"] = task_id
            tasks.append(task)
            target_ids.append(task_id)
        payload = {
            "review_budget_fraction": 0.1,
            "snapshot_time": self.snapshot["snapshot_time"],
            "target_task_ids": target_ids,
            "tasks": tasks,
        }
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.assertLess(len(encoded), MAX_REQUEST_BODY_BYTES)


if __name__ == "__main__":
    unittest.main()
