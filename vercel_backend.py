from __future__ import annotations

from typing import Any

from agents import create_agent
from agents.outer_agent import OuterAgent
from hanabi.cards import Card
from hanabi.hints import Hint
from hanabi.game import HanabiGame, TurnLogEntry
from hanabi.mental_state import MentalCardKnowledge, PlayerKnowledge
from hanabi.state import Action, ReceivedHint
from webui.server import (
    WebGameSession,
    ai_match_to_payload,
    format_event,
    payload_to_action,
    view_to_payload,
)


def serialize_card(card: Card) -> dict[str, Any]:
    return {"color": card.color, "rank": card.rank}


def deserialize_card(payload: dict[str, Any]) -> Card:
    return Card(str(payload["color"]), int(payload["rank"]))


def serialize_hint(hint: Hint) -> dict[str, Any]:
    return {"kind": hint.kind, "value": hint.value}


def deserialize_hint(payload: dict[str, Any]) -> Hint:
    value = payload["value"]
    if payload["kind"] == "rank":
        value = int(value)
    return Hint(str(payload["kind"]), value)


def serialize_action(action: Action) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": action.kind}
    if action.card_index is not None:
        payload["card_index"] = action.card_index
    if action.target_player is not None:
        payload["target_player"] = action.target_player
    if action.hint is not None:
        payload["hint"] = serialize_hint(action.hint)
    return payload


def deserialize_action(payload: dict[str, Any]) -> Action:
    kind = str(payload["kind"])
    if kind == "play":
        return Action.play(int(payload["card_index"]))
    if kind == "discard":
        return Action.discard(int(payload["card_index"]))
    hint = deserialize_hint(payload["hint"])
    if hint.kind == "color":
        return Action.hint_color(int(payload["target_player"]), str(hint.value))
    return Action.hint_rank(int(payload["target_player"]), int(hint.value))


def serialize_received_hint(received: ReceivedHint | None) -> dict[str, Any] | None:
    if received is None:
        return None
    return {
        "hint": serialize_hint(received.hint),
        "positive_indices": list(received.positive_indices),
        "source_player": received.source_player,
    }


def deserialize_received_hint(payload: dict[str, Any] | None) -> ReceivedHint | None:
    if payload is None:
        return None
    return ReceivedHint(
        hint=deserialize_hint(payload["hint"]),
        positive_indices=tuple(int(index) for index in payload["positive_indices"]),
        source_player=int(payload["source_player"]),
    )


def serialize_turn_log_entry(entry: TurnLogEntry) -> dict[str, Any]:
    return {
        "turn_number": entry.turn_number,
        "actor": entry.actor,
        "action": serialize_action(entry.action),
        "positive_indices": list(entry.positive_indices),
        "card": serialize_card(entry.card) if entry.card is not None else None,
        "success": entry.success,
        "score_after": entry.score_after,
        "hints_after": entry.hints_after,
        "mistakes_after": entry.mistakes_after,
    }


def deserialize_turn_log_entry(payload: dict[str, Any]) -> TurnLogEntry:
    return TurnLogEntry(
        turn_number=int(payload["turn_number"]),
        actor=int(payload["actor"]),
        action=deserialize_action(payload["action"]),
        positive_indices=tuple(int(index) for index in payload["positive_indices"]),
        card=deserialize_card(payload["card"]) if payload["card"] is not None else None,
        success=payload["success"],
        score_after=int(payload["score_after"]),
        hints_after=int(payload["hints_after"]),
        mistakes_after=int(payload["mistakes_after"]),
    )


def serialize_mental_card(mental_card: MentalCardKnowledge) -> dict[str, Any]:
    return {
        "color_allowed": dict(mental_card.color_allowed),
        "rank_allowed": {str(rank): allowed for rank, allowed in mental_card.rank_allowed.items()},
    }


def deserialize_mental_card(payload: dict[str, Any]) -> MentalCardKnowledge:
    return MentalCardKnowledge(
        color_allowed={str(color): bool(allowed) for color, allowed in payload["color_allowed"].items()},
        rank_allowed={int(rank): bool(allowed) for rank, allowed in payload["rank_allowed"].items()},
    )


def serialize_player_knowledge(knowledge: PlayerKnowledge) -> dict[str, Any]:
    return {"cards": [serialize_mental_card(card) for card in knowledge.cards]}


def deserialize_player_knowledge(payload: dict[str, Any]) -> PlayerKnowledge:
    return PlayerKnowledge(cards=[deserialize_mental_card(card) for card in payload["cards"]])


def serialize_game(game: HanabiGame) -> dict[str, Any]:
    return {
        "fireworks": dict(game.fireworks),
        "hints": game.hints,
        "mistakes_made": game.mistakes_made,
        "current_player": game.current_player,
        "turn_number": game.turn_number,
        "discard_pile": [serialize_card(card) for card in game.discard_pile],
        "hands": [[serialize_card(card) for card in hand] for hand in game.hands],
        "knowledge": [serialize_player_knowledge(knowledge) for knowledge in game.knowledge],
        "turn_log": [serialize_turn_log_entry(entry) for entry in game.turn_log],
        "pending_received_hints": [serialize_received_hint(item) for item in game.pending_received_hints],
        "final_round_started": game.final_round_started,
        "final_turns_taken": game.final_turns_taken,
        "deck": [serialize_card(card) for card in game.deck],
    }


def deserialize_game(payload: dict[str, Any]) -> HanabiGame:
    game = HanabiGame.__new__(HanabiGame)
    game.fireworks = {str(color): int(rank) for color, rank in payload["fireworks"].items()}
    game.hints = int(payload["hints"])
    game.mistakes_made = int(payload["mistakes_made"])
    game.current_player = int(payload["current_player"])
    game.turn_number = int(payload["turn_number"])
    game.discard_pile = [deserialize_card(card) for card in payload["discard_pile"]]
    game.hands = [
        [deserialize_card(card) for card in payload["hands"][0]],
        [deserialize_card(card) for card in payload["hands"][1]],
    ]
    game.knowledge = [deserialize_player_knowledge(item) for item in payload["knowledge"]]
    game.turn_log = [deserialize_turn_log_entry(entry) for entry in payload["turn_log"]]
    game.pending_received_hints = [
        deserialize_received_hint(payload["pending_received_hints"][0]),
        deserialize_received_hint(payload["pending_received_hints"][1]),
    ]
    game.final_round_started = bool(payload["final_round_started"])
    game.final_turns_taken = int(payload["final_turns_taken"])
    game.deck = [deserialize_card(card) for card in payload["deck"]]
    return game


def serialize_agent(agent: Any) -> dict[str, Any]:
    payload = {
        "type": agent.display_name.lower(),
        "player_index": agent.player_index,
    }
    if isinstance(agent, OuterAgent):
        payload["sent_hint_history"] = {
            str(index): sorted(kinds)
            for index, kinds in agent.sent_hint_history.items()
        }
    return payload


def deserialize_agent(payload: dict[str, Any]) -> Any:
    agent = create_agent(str(payload["type"]))
    agent.reset(int(payload["player_index"]))
    if isinstance(agent, OuterAgent):
        agent.sent_hint_history = {
            int(index): set(kinds)
            for index, kinds in payload.get("sent_hint_history", {}).items()
        }
    return agent


def serialize_session(session: WebGameSession) -> dict[str, Any]:
    return {
        "game": serialize_game(session.game),
        "opponent_name": session.opponent_name,
        "ai_agent": serialize_agent(session.ai_agent),
        "log_entries": session.log_entries,
    }


def deserialize_session(payload: dict[str, Any]) -> WebGameSession:
    return WebGameSession(
        game=deserialize_game(payload["game"]),
        opponent_name=str(payload["opponent_name"]),
        ai_agent=deserialize_agent(payload["ai_agent"]),
        log_entries=list(payload["log_entries"]),
    )


def new_human_session(seed: int | None, opponent: str) -> WebGameSession:
    from hanabi.deck import shuffled_deck

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


def human_state_payload(session_payload: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    session = deserialize_session(session_payload) if session_payload is not None else new_human_session(seed=0, opponent="full")
    human_view = session.game.get_view_for(0)
    payload = view_to_payload(
        game=session.game,
        opponent_name=session.opponent_name,
        human_view=human_view,
        log_entries=session.log_entries,
    )
    payload["session"] = serialize_session(session)
    if error is not None:
        payload["error"] = error
    return payload


def new_game_payload(seed: int | None, opponent: str) -> dict[str, Any]:
    session = new_human_session(seed=seed, opponent=opponent)
    return human_state_payload(serialize_session(session))


def apply_human_action_payload(session_payload: dict[str, Any], action_payload: dict[str, Any]) -> dict[str, Any]:
    session = deserialize_session(session_payload)
    if session.game.is_done():
        return human_state_payload(serialize_session(session), error="The game is already over.")
    if session.game.current_player != 0:
        return human_state_payload(serialize_session(session), error="It is not the human player's turn.")

    try:
        action = payload_to_action(action_payload)
        event = session.game.apply_action(action)
    except (KeyError, TypeError, ValueError) as exc:
        return human_state_payload(serialize_session(session), error=str(exc))

    session.ai_agent.observe(event)
    session.log_entries.append(format_event(session.game.turn_log[-1]))

    while not session.game.is_done() and session.game.current_player == 1:
        ai_view = session.game.get_view_for(1)
        ai_action = session.ai_agent.choose_action(ai_view)
        ai_event = session.game.apply_action(ai_action)
        session.ai_agent.observe(ai_event)
        session.log_entries.append(format_event(session.game.turn_log[-1]))

    return human_state_payload(serialize_session(session))


def ai_match_payload(seed: int | None, agent_a: str, agent_b: str) -> dict[str, Any]:
    from hanabi.deck import shuffled_deck

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
