from __future__ import annotations

import json

from api._shared import JsonHandler, parse_seed
from vercel_backend import new_game_payload


class handler(JsonHandler):
    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            opponent = str(payload.get("opponent", "full")).lower()
            seed = parse_seed(payload.get("seed"))
            self._write_json(new_game_payload(seed=seed, opponent=opponent))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_error(str(exc), payload={"view_mode": "human"})

    def do_GET(self) -> None:
        self._method_not_allowed()
