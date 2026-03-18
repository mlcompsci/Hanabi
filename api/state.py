from __future__ import annotations

import json

from api._shared import JsonHandler
from vercel_backend import human_state_payload


class handler(JsonHandler):
    def do_GET(self) -> None:
        self._write_json(human_state_payload(None))

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            self._write_json(human_state_payload(payload.get("session")))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_error(str(exc))
