from __future__ import annotations

import json

from api._shared import JsonHandler, parse_seed
from vercel_backend import ai_match_payload


class handler(JsonHandler):
    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            agent_a = str(payload.get("agent_a", "full")).lower()
            agent_b = str(payload.get("agent_b", "full")).lower()
            seed = parse_seed(payload.get("seed"))
            self._write_json(ai_match_payload(seed=seed, agent_a=agent_a, agent_b=agent_b))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_error(str(exc), payload={"view_mode": "ai_match"})

    def do_GET(self) -> None:
        self._method_not_allowed()
