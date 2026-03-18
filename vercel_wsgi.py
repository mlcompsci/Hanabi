from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from vercel_backend import ai_match_payload, apply_human_action_payload, human_state_payload, new_game_payload

ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "webui" / "static"


def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
    length_value = environ.get("CONTENT_LENGTH") or "0"
    try:
        length = int(length_value)
    except ValueError:
        length = 0
    raw = environ["wsgi.input"].read(length) if length > 0 else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _json_response(payload: dict[str, Any], status: str = "200 OK") -> tuple[str, list[tuple[str, str]], list[bytes]]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", "no-store, max-age=0"),
        ("Pragma", "no-cache"),
        ("Expires", "0"),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, [body]


def _static_response(relative_path: str) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    file_path = (STATIC_DIR / relative_path).resolve()
    if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
        return _json_response({"error": "Not found."}, status="404 Not Found")
    data = file_path.read_bytes()
    content_type, _ = mimetypes.guess_type(file_path.name)
    headers = [
        ("Content-Type", content_type or "application/octet-stream"),
        ("Cache-Control", "no-store, max-age=0"),
        ("Pragma", "no-cache"),
        ("Expires", "0"),
        ("Content-Length", str(len(data))),
    ]
    return "200 OK", headers, [data]


def _method_not_allowed() -> tuple[str, list[tuple[str, str]], list[bytes]]:
    return _json_response({"error": "Method not allowed."}, status="405 Method Not Allowed")


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = str(environ.get("PATH_INFO", "/")) or "/"

    try:
        if path in {"/", "/index.html"}:
            status, headers, body = _static_response("index.html")
        elif path.startswith("/static/"):
            status, headers, body = _static_response(path.removeprefix("/static/"))
        elif path in {"/api", "/api/"}:
            status, headers, body = _json_response(
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
        elif path == "/api/state":
            if method == "GET":
                status, headers, body = _json_response(human_state_payload(None))
            elif method == "POST":
                payload = _read_json(environ)
                status, headers, body = _json_response(human_state_payload(payload.get("session")))
            else:
                status, headers, body = _method_not_allowed()
        elif path == "/api/new-game":
            if method != "POST":
                status, headers, body = _method_not_allowed()
            else:
                payload = _read_json(environ)
                opponent = str(payload.get("opponent", "full")).lower()
                seed_value = payload.get("seed")
                seed = None if seed_value in {None, ""} else int(seed_value)
                status, headers, body = _json_response(new_game_payload(seed=seed, opponent=opponent))
        elif path == "/api/action":
            if method != "POST":
                status, headers, body = _method_not_allowed()
            else:
                payload = _read_json(environ)
                session = payload.get("session")
                if session is None:
                    status, headers, body = _json_response(
                        human_state_payload(None, error="Missing session payload."),
                        status="400 Bad Request",
                    )
                else:
                    action_payload = payload.get("action")
                    if not isinstance(action_payload, dict):
                        status, headers, body = _json_response(
                            human_state_payload(session, error="Missing action payload."),
                            status="400 Bad Request",
                        )
                    else:
                        status, headers, body = _json_response(apply_human_action_payload(session, action_payload))
        elif path == "/api/ai-match":
            if method != "POST":
                status, headers, body = _method_not_allowed()
            else:
                payload = _read_json(environ)
                agent_a = str(payload.get("agent_a", "full")).lower()
                agent_b = str(payload.get("agent_b", "full")).lower()
                seed_value = payload.get("seed")
                seed = None if seed_value in {None, ""} else int(seed_value)
                status, headers, body = _json_response(ai_match_payload(seed=seed, agent_a=agent_a, agent_b=agent_b))
        else:
            status, headers, body = _json_response({"error": "Not found."}, status="404 Not Found")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        status, headers, body = _json_response({"error": str(exc)}, status="400 Bad Request")

    start_response(status, headers)
    return body
