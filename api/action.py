from __future__ import annotations

import json

from api._shared import JsonHandler
from vercel_backend import apply_human_action_payload, human_state_payload


class handler(JsonHandler):
    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            session = payload.get("session")
            if session is None:
                self._write_json(human_state_payload(None, error="Missing session payload."), status=400)
                return
            action_payload = payload.get("action")
            if not isinstance(action_payload, dict):
                self._write_json(human_state_payload(session, error="Missing action payload."), status=400)
                return
            self._write_json(apply_human_action_payload(session, action_payload))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_error(str(exc), payload={"view_mode": "human"})

    def do_GET(self) -> None:
        self._method_not_allowed()
