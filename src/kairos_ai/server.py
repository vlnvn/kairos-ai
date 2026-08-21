from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .engine import KairosRanker, ModelArtifactError, SnapshotError

ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = ROOT / "static"
MODEL = ROOT / "artifacts" / "kairos_final.cbm"
MAX_REQUEST_BODY_BYTES = 8 * 1024 * 1024

STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; connect-src 'self'; "
        "frame-ancestors 'none'; img-src 'self'; object-src 'none'; "
        "script-src 'self'; style-src 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def handler_factory(ranker, static_root: Path = STATIC_ROOT):
    class Handler(BaseHTTPRequestHandler):
        server_version = "KAIROS"
        sys_version = ""

        def _send_headers(self, status: int, content_type: str, length: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()

        def send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            self._send_headers(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/health":
                self.send_json(
                    200,
                    {
                        "decision_owner": "human_dispatcher",
                        "model": "kairos_final.cbm",
                        "status": "ok",
                    },
                )
                return

            static_route = STATIC_ROUTES.get(path)
            if static_route is None:
                self.send_json(404, {"error": "not_found"})
                return

            filename, content_type = static_route
            try:
                body = (static_root / filename).read_bytes()
            except OSError:
                self.send_json(503, {"error": "service_unavailable"})
                return
            self._send_headers(200, content_type, len(body))
            self.wfile.write(body)

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/score":
                self.send_json(404, {"error": "not_found"})
                return

            media_type = self.headers.get_content_type().lower()
            if media_type != "application/json":
                self.send_json(415, {"error": "unsupported_media_type"})
                return

            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length) if raw_length is not None else -1
            except ValueError:
                length = -1
            if length < 0:
                self.send_json(400, {"error": "invalid_request"})
                return
            if length > MAX_REQUEST_BODY_BYTES:
                self.send_json(413, {"error": "request_too_large"})
                return

            try:
                snapshot = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_json(400, {"error": "invalid_json"})
                return

            try:
                results = ranker.score(snapshot)
            except SnapshotError:
                self.send_json(400, {"error": "invalid_snapshot"})
                return
            except ModelArtifactError:
                self.send_json(503, {"error": "model_unavailable"})
                return
            except Exception:
                self.send_json(503, {"error": "scoring_unavailable"})
                return

            try:
                metadata = {
                    "review_budget_count": sum(
                        item["decision"] == "WINDOW_REVIEW" for item in results
                    ),
                    "review_budget_fraction": snapshot["review_budget_fraction"],
                    "total_targets": len(results),
                }
                self.send_json(200, {"metadata": metadata, "results": results})
            except (KeyError, TypeError, ValueError):
                self.send_json(500, {"error": "response_unavailable"})

        def log_message(self, *_: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(
        (args.host, args.port), handler_factory(KairosRanker(MODEL))
    )
    print(f"KAIROS listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
