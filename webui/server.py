from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents import create_agent
from agents.intentional_agent import IntentionalAgent
from hanabi.analysis import (
    best_hint_assessment,
    discard_assessments,
    form_intentions,
    legal_hint_assessments,
)
from hanabi.cards import COLORS, Card
from hanabi.deck import shuffled_deck
from hanabi.game import HanabiGame, TurnLogEntry
from hanabi.rules import card_is_known_playable, card_is_known_useless
from hanabi.state import Action, TurnView

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


def summarize_possibilities(card, limit: int = 8) -> list[dict[str, Any]]:
    possibilities = sorted(
        card.possible_cards_with_counts(),
        key=lambda item: (item[0].rank, COLORS.index(item[0].color)),
    )
    payload: list[dict[str, Any]] = []
    for identity, count in possibilities[:limit]:
        payload.append(
            {
                "short": identity.short,
                "color": identity.color,
                "rank": identity.rank,
                "count": count,
            },
        )
    if len(possibilities) > limit:
        payload.append({"short": "...", "count": 0})
    return payload


def describe_hint(action: Action) -> str:
    assert action.hint is not None
    if action.hint.kind == "color":
        return f"Color {action.hint.value}"
    return f"Rank {action.hint.value}"


def describe_action(action: Action) -> str:
    if action.kind == "play":
        assert action.card_index is not None
        return f"Play slot {action.card_index + 1}"
    if action.kind == "discard":
        assert action.card_index is not None
        return f"Discard slot {action.card_index + 1}"
    return f"Hint {describe_hint(action)}"


def format_event(turn_entry: TurnLogEntry) -> dict[str, Any]:
    actor = "You" if turn_entry.actor == 0 else "AI"
    action_label = turn_entry.action.kind.upper()
    headline = f"Turn {turn_entry.turn_number} - {actor} - {action_label}"

    if turn_entry.action.kind == "hint" and turn_entry.action.hint is not None:
        targets = ", ".join(str(index + 1) for index in turn_entry.positive_indices) or "none"
        detail = (
            f"Gave {describe_hint(turn_entry.action)} to slots [{targets}]. "
            f"Hints now {turn_entry.hints_after}/{HanabiGame.MAX_HINTS}."
        )
    elif turn_entry.card is not None and turn_entry.action.kind == "play":
        outcome = "success" if turn_entry.success else "misplay"
        slot = turn_entry.action.card_index + 1 if turn_entry.action.card_index is not None else "?"
        detail = (
            f"Played slot {slot} and revealed {turn_entry.card}. "
            f"Result: {outcome}. "
            f"Score {turn_entry.score_after}. "
            f"Mistakes {turn_entry.mistakes_after}/{HanabiGame.MAX_MISTAKES}."
        )
    elif turn_entry.card is not None and turn_entry.action.kind == "discard":
        slot = turn_entry.action.card_index + 1 if turn_entry.action.card_index is not None else "?"
        detail = (
            f"Discarded slot {slot} and revealed {turn_entry.card}. "
            f"Hints now {turn_entry.hints_after}/{HanabiGame.MAX_HINTS}."
        )
    else:
        detail = "Action resolved."

    text = f"{headline}. {detail}"
    return {
        "turn_number": turn_entry.turn_number,
        "actor": turn_entry.actor,
        "actor_label": actor,
        "kind": turn_entry.action.kind,
        "action_label": action_label,
        "headline": headline,
        "detail": detail,
        "text": text,
        "score_after": turn_entry.score_after,
        "hints_after": turn_entry.hints_after,
        "mistakes_after": turn_entry.mistakes_after,
    }


def discard_summary(discard_pile: tuple[Card, ...]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for card in discard_pile:
        counts[card.short] = counts.get(card.short, 0) + 1
    return [
        {"short": short, "count": count}
        for short, count in sorted(counts.items())
    ]


def face_up_hand_payload(
    hand: list[Card] | tuple[Card, ...],
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> list[dict[str, Any]]:
    intentions = form_intentions(tuple(hand), fireworks, tuple(discard_pile))
    return [
        {
            "slot": index,
            "short": card.short,
            "color": card.color,
            "rank": card.rank,
            "intention": intentions[index],
        }
        for index, card in enumerate(hand)
    ]


def view_to_payload(
    game: HanabiGame,
    opponent_name: str,
    human_view: TurnView,
    log_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendation_agent = IntentionalAgent()
    recommendation_agent.reset(0)
    recommendation = recommendation_agent.choose_action(human_view)

    intentions = form_intentions(
        human_view.partner_hand,
        human_view.fireworks,
        human_view.discard_pile,
    )
    best_hint = best_hint_assessment(human_view)
    hint_assessments = legal_hint_assessments(human_view)
    discard_scores = {item.card_index: item.score for item in discard_assessments(human_view)}
    actual_human_hand = tuple(game.hands[0])
    raw_human_knowledge = tuple(game.knowledge[0].cards)

    legal_action_payloads: list[dict[str, Any]] = []
    for action in human_view.legal_actions:
        legal_action_payloads.append(action_to_payload(action))

    hint_color_actions = sorted(
        {
            action.hint.value
            for action in human_view.legal_actions
            if action.kind == "hint" and action.hint is not None and action.hint.kind == "color"
        },
        key=COLORS.index,
    )
    hint_rank_actions = sorted(
        {
            action.hint.value
            for action in human_view.legal_actions
            if action.kind == "hint" and action.hint is not None and action.hint.kind == "rank"
        },
    )

    return {
        "status": {
            "opponent": opponent_name,
            "turn": game.current_player,
            "human_turn": game.current_player == 0 and not game.is_done(),
            "game_over": game.is_done(),
            "score": game.score(),
            "hints": human_view.hints,
            "max_hints": human_view.max_hints,
            "mistakes": human_view.mistakes_made,
            "max_mistakes": human_view.max_mistakes,
            "deck_size": human_view.deck_size,
            "turn_number": human_view.turn_number,
        },
        "fireworks": human_view.fireworks,
        "discard_pile": discard_summary(human_view.discard_pile),
        "opponent_hand": [
            {
                "slot": index,
                "short": card.short,
                "color": card.color,
                "rank": card.rank,
                "intention": intentions[index],
            }
            for index, card in enumerate(human_view.partner_hand)
        ],
        "human_hand": [
            {
                "slot": index,
                "identified": mental_card.is_identified(),
                "identified_short": mental_card.possible_cards()[0].short if mental_card.is_identified() else None,
                "possible_count": len(mental_card.possible_cards()),
                "hint_knowledge": {
                    "allowed_colors": [
                        color
                        for color, allowed in raw_human_knowledge[index].color_allowed.items()
                        if allowed
                    ],
                    "allowed_ranks": [
                        rank
                        for rank, allowed in raw_human_knowledge[index].rank_allowed.items()
                        if allowed
                    ],
                },
                "known_playable": card_is_known_playable(mental_card, human_view.fireworks),
                "known_useless": card_is_known_useless(mental_card, human_view.fireworks, human_view.discard_pile),
                "discard_score": round(discard_scores[index], 4),
                "possibilities": summarize_possibilities(mental_card),
                "actual_short": actual_human_hand[index].short,
                "actual_color": actual_human_hand[index].color,
                "actual_rank": actual_human_hand[index].rank,
            }
            for index, mental_card in enumerate(human_view.my_mental_state.cards)
        ],
        "heuristics": {
            "recommendation": {
                "label": describe_action(recommendation),
                "action": action_to_payload(recommendation),
            },
            "best_hint": (
                {
                    "label": describe_hint(best_hint.action),
                    "score": best_hint.score,
                    "positive_slots": list(best_hint.positive_indices),
                    "predictions": list(best_hint.predictions),
                }
                if best_hint is not None
                else None
            ),
            "hint_assessments": [
                {
                    "label": describe_hint(item.action),
                    "score": item.score,
                    "valid": item.valid,
                    "positive_slots": list(item.positive_indices),
                    "predictions": list(item.predictions),
                }
                for item in hint_assessments
            ],
            "discard_scores": [
                {
                    "slot": slot,
                    "score": round(score, 4),
                }
                for slot, score in sorted(discard_scores.items())
            ],
        },
        "pending_received_hint": (
            {
                "kind": human_view.pending_received_hint.hint.kind,
                "value": human_view.pending_received_hint.hint.value,
                "positive_slots": list(human_view.pending_received_hint.positive_indices),
            }
            if human_view.pending_received_hint is not None
            else None
        ),
        "controls": {
            "legal_actions": legal_action_payloads,
            "hint_colors": hint_color_actions,
            "hint_ranks": hint_rank_actions,
        },
        "log": log_entries,
    }


def ai_match_to_payload(
    game: HanabiGame,
    agent_a_name: str,
    agent_b_name: str,
    log_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "view_mode": "ai_match",
        "status": {
            "agent_a": agent_a_name,
            "agent_b": agent_b_name,
            "game_over": game.is_done(),
            "score": game.score(),
            "hints": game.hints,
            "max_hints": game.MAX_HINTS,
            "mistakes": game.mistakes_made,
            "max_mistakes": game.MAX_MISTAKES,
            "deck_size": len(game.deck),
            "turn_number": game.turn_number,
        },
        "fireworks": dict(game.fireworks),
        "discard_pile": discard_summary(tuple(game.discard_pile)),
        "agent_a_hand": face_up_hand_payload(game.hands[0], game.fireworks, game.discard_pile),
        "agent_b_hand": face_up_hand_payload(game.hands[1], game.fireworks, game.discard_pile),
        "summary": {
            "label": f"{agent_a_name.title()} vs {agent_b_name.title()}",
            "final_score": game.score(),
            "turns_played": len(game.turn_log),
        },
        "log": log_entries,
    }


def action_to_payload(action: Action) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": action.kind}
    if action.card_index is not None:
        payload["card_index"] = action.card_index
    if action.target_player is not None:
        payload["target_player"] = action.target_player
    if action.hint is not None:
        payload["hint_kind"] = action.hint.kind
        payload["hint_value"] = action.hint.value
    return payload


def payload_to_action(payload: dict[str, Any]) -> Action:
    kind = payload.get("kind")
    if kind == "play":
        return Action.play(int(payload["card_index"]))
    if kind == "discard":
        return Action.discard(int(payload["card_index"]))
    if kind == "hint":
        hint_kind = payload["hint_kind"]
        hint_value = payload["hint_value"]
        target_player = int(payload.get("target_player", 1))
        if hint_kind == "color":
            return Action.hint_color(target_player, str(hint_value))
        return Action.hint_rank(target_player, int(hint_value))
    raise ValueError(f"Unknown action kind: {kind}")


@dataclass
class WebGameSession:
    game: HanabiGame
    opponent_name: str
    ai_agent: Any
    log_entries: list[dict[str, Any]]


class SessionController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session = self._new_session(seed=0, opponent="full")

    def _new_session(self, seed: int | None, opponent: str) -> WebGameSession:
        deck = shuffled_deck(seed) if seed is not None else None
        game = HanabiGame(deck=deck)
        ai_agent = create_agent(opponent)
        ai_agent.reset(1)
        return WebGameSession(
            game=game,
            opponent_name=opponent,
            ai_agent=ai_agent,
            log_entries=[],
        )

    def new_game(self, seed: int | None, opponent: str) -> dict[str, Any]:
        with self._lock:
            try:
                self._session = self._new_session(seed, opponent)
            except ValueError as exc:
                return self._state_payload_locked(error=str(exc))
            return self._state_payload_locked()

    def state(self) -> dict[str, Any]:
        with self._lock:
            return self._state_payload_locked()

    def run_ai_match(self, seed: int | None, agent_a: str, agent_b: str) -> dict[str, Any]:
        with self._lock:
            deck = shuffled_deck(seed) if seed is not None else None
            game = HanabiGame(deck=deck)
            agents = [create_agent(agent_a), create_agent(agent_b)]
            for index, agent in enumerate(agents):
                agent.reset(index)

            log_entries: list[dict[str, Any]] = []
            while not game.is_done():
                view = game.get_view_for(game.current_player)
                action = agents[game.current_player].choose_action(view)
                event = game.apply_action(action)
                for agent in agents:
                    agent.observe(event)
                log_entries.append(format_event(game.turn_log[-1]))

            return ai_match_to_payload(game, agent_a, agent_b, log_entries)

    def apply_human_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._session
            if session.game.is_done():
                return self._state_payload_locked(error="The game is already over.")
            if session.game.current_player != 0:
                return self._state_payload_locked(error="It is not the human player's turn.")

            try:
                action = payload_to_action(payload)
                event = session.game.apply_action(action)
            except (KeyError, TypeError, ValueError) as exc:
                return self._state_payload_locked(error=str(exc))

            session.ai_agent.observe(event)
            session.log_entries.append(format_event(session.game.turn_log[-1]))

            while not session.game.is_done() and session.game.current_player == 1:
                ai_view = session.game.get_view_for(1)
                ai_action = session.ai_agent.choose_action(ai_view)
                ai_event = session.game.apply_action(ai_action)
                session.ai_agent.observe(ai_event)
                session.log_entries.append(format_event(session.game.turn_log[-1]))

            return self._state_payload_locked()

    def _state_payload_locked(self, error: str | None = None) -> dict[str, Any]:
        session = self._session
        human_view = session.game.get_view_for(0)
        payload = view_to_payload(
            game=session.game,
            opponent_name=session.opponent_name,
            human_view=human_view,
            log_entries=session.log_entries,
        )
        if error is not None:
            payload["error"] = error
        return payload


class HanabiRequestHandler(BaseHTTPRequestHandler):
    server_version = "HanabiWebUI/1.0"

    @property
    def controller(self) -> SessionController:
        return self.server.controller  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._write_json(self.controller.state())
            return
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            self._serve_static(relative)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/new-game":
            try:
                payload = self._read_json()
                opponent = str(payload.get("opponent", "full")).lower()
                seed_value = payload.get("seed")
                seed = None if seed_value in {None, ""} else int(seed_value)
                self._write_json(self.controller.new_game(seed=seed, opponent=opponent))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._write_json(self.controller.state() | {"error": str(exc)}, status=400)
            return
        if parsed.path == "/api/action":
            try:
                payload = self._read_json()
                self._write_json(self.controller.apply_human_action(payload))
            except json.JSONDecodeError as exc:
                self._write_json(self.controller.state() | {"error": str(exc)}, status=400)
            return
        if parsed.path == "/api/ai-match":
            try:
                payload = self._read_json()
                agent_a = str(payload.get("agent_a", "full")).lower()
                agent_b = str(payload.get("agent_b", "full")).lower()
                seed_value = payload.get("seed")
                seed = None if seed_value in {None, ""} else int(seed_value)
                self._write_json(self.controller.run_ai_match(seed=seed, agent_a=agent_a, agent_b=agent_b))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._write_json({"view_mode": "ai_match", "error": str(exc)}, status=400)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

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

    def _serve_static(self, relative_path: str) -> None:
        file_path = (STATIC_DIR / relative_path).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content_type, _ = mimetypes.guess_type(file_path.name)
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class HanabiWebServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, HanabiRequestHandler)
        self.controller = SessionController()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Hanabi web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open-browser", action="store_true", help="Open the UI in the default browser.")
    args = parser.parse_args()

    server = HanabiWebServer((args.host, args.port))
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving Hanabi web UI at {url}")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
