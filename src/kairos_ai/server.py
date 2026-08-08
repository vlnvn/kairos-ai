from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import KairosRanker, SnapshotError

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "static" / "index.html"
MODEL = ROOT / "artifacts" / "kairos_final.cbm"


def handler_factory(ranker):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {"status": "ok", "model": "kairos_final.cbm", "decision_owner": "human_dispatcher"})
            elif self.path == "/":
                body = STATIC.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            else:
                self.send_json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/score":
                self.send_json(404, {"error": "not_found"}); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                snapshot = json.loads(self.rfile.read(length))
                self.send_json(200, {"results": ranker.score(snapshot)})
            except (SnapshotError, ValueError, json.JSONDecodeError) as exc:
                self.send_json(400, {"error": "invalid_snapshot", "detail": str(exc)})

        def log_message(self, *_):
            return
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(KairosRanker(MODEL)))
    print(f"KAIROS listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

