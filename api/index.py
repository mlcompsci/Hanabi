from __future__ import annotations

from api._shared import JsonHandler


class handler(JsonHandler):
    def do_GET(self) -> None:
        self._write_json(
            {
                "name": "Intentional Hanabi API",
                "status": "ok",
                "routes": [
                    "/api/state",
                    "/api/new-game",
                    "/api/action",
                    "/api/ai-match",
                ],
            },
        )

    def do_POST(self) -> None:
        self.do_GET()
