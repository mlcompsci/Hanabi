from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any


def parse_seed(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


class JsonHandler(BaseHTTPRequestHandler):
    server_version = "HanabiVercelAPI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _write_error(self, message: str, status: int = 400, payload: dict[str, Any] | None = None) -> None:
        response = dict(payload or {})
        response["error"] = message
        self._write_json(response, status=status)

    def _method_not_allowed(self) -> None:
        self._write_error("Method not allowed.", status=HTTPStatus.METHOD_NOT_ALLOWED)
