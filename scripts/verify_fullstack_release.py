from __future__ import annotations

import copy
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kairos_ai.engine import KairosRanker

MODEL = ROOT / "artifacts" / "kairos_final.cbm"
SNAPSHOT = ROOT / "examples" / "input_snapshot.json"
STARTUP_TIMEOUT_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = 30
CAPACITY_EXPECTATIONS = ((0.05, 7), (0.1, 14), (0.2, 27), (1.0, 134))


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request(port: int, method: str, path: str, body: bytes | None = None):
    connection = http.client.HTTPConnection(
        "127.0.0.1", port, timeout=REQUEST_TIMEOUT_SECONDS
    )
    headers = {"Content-Type": "application/json"} if body is not None else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    status = response.status
    response_headers = dict(response.getheaders())
    connection.close()
    return status, response_headers, raw


def wait_for_health(port: int) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, _, raw = request(port, "GET", "/health")
            if status == 200 and json.loads(raw)["status"] == "ok":
                return
        except (ConnectionError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError("server did not become healthy") from last_error


def verify() -> dict:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    ranker = KairosRanker(MODEL)
    direct_started = time.perf_counter()
    direct = ranker.score(snapshot)
    direct_ms = (time.perf_counter() - direct_started) * 1000

    port = available_port()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "kairos_ai.server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_health(port)
        baseline_order = None
        baseline_scores = None
        capacity_results = {}
        canonical_http_ms = None

        for fraction, expected_reviews in CAPACITY_EXPECTATIONS:
            request_snapshot = copy.deepcopy(snapshot)
            request_snapshot["review_budget_fraction"] = fraction
            encoded = json.dumps(request_snapshot, separators=(",", ":")).encode()
            started = time.perf_counter()
            status, headers, raw = request(port, "POST", "/score", encoded)
            elapsed_ms = (time.perf_counter() - started) * 1000
            if status != 200:
                raise AssertionError(f"capacity {fraction} returned HTTP {status}")
            payload = json.loads(raw)
            results = payload["results"]
            metadata = payload["metadata"]
            reviews = sum(
                item["decision"] == "WINDOW_REVIEW" for item in results
            )
            assert len(results) == 134
            assert reviews == expected_reviews
            assert metadata == {
                "review_budget_count": expected_reviews,
                "review_budget_fraction": fraction,
                "total_targets": 134,
            }
            assert "default-src 'self'" in headers["Content-Security-Policy"]
            order = [item["task_id"] for item in results]
            scores = [item["review_score"] for item in results]
            if baseline_order is None:
                baseline_order, baseline_scores = order, scores
            else:
                assert order == baseline_order
                assert scores == baseline_scores
            if fraction == 0.1:
                assert results == direct
                canonical_http_ms = elapsed_ms
            capacity_results[str(int(fraction * 100))] = reviews

        status, _, raw = request(port, "POST", "/score", b"{not-json")
        assert status == 400
        assert json.loads(raw) == {"error": "invalid_json"}

        serialized = json.dumps(direct, separators=(",", ":")).lower()
        for forbidden in ("risk_score", "probability", "likelihood", "confidence"):
            assert forbidden not in serialized

        return {
            "capacity_reviews": capacity_results,
            "canonical_http_ms": round(float(canonical_http_ms), 3),
            "direct_engine_ms": round(direct_ms, 3),
            "malformed_request_status": status,
            "rank_order_matches_direct_engine": True,
            "result": "PASS",
            "total_targets": len(direct),
        }
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
