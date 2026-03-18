from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .cards import COLORS, RANKS, Card
from .deck import build_standard_deck, clone_deck, shuffled_deck
from .mental_state import (
    PlayerKnowledge,
    apply_hint_to_knowledge,
    build_public_counter,
    resolve_player_knowledge,
    unknown_player_knowledge,
)
from .rules import is_playable
from .state import Action, GameEvent, ReceivedHint, TurnView


@dataclass(frozen=True)
class TurnLogEntry:
    turn_number: int
    actor: int
    action: Action
    positive_indices: tuple[int, ...]
    card: Card | None
    success: bool | None
    score_after: int
    hints_after: int
    mistakes_after: int


class HanabiGame:
    """Strict two-player Hanabi simulator for the paper reproduction."""

    NUM_PLAYERS = 2
    HAND_SIZE = 5
    MAX_HINTS = 8
    MAX_MISTAKES = 3

    def __init__(self, deck: Iterable[Card] | None = None) -> None:
        self.fireworks: dict[str, int] = {color: 0 for color in COLORS}
        self.hints = self.MAX_HINTS
        self.mistakes_made = 0
        self.current_player = 0
        self.turn_number = 1
        self.discard_pile: list[Card] = []
        self.hands: list[list[Card]] = [[], []]
        self.knowledge: list[PlayerKnowledge] = []
        self.turn_log: list[TurnLogEntry] = []
        self.pending_received_hints: list[ReceivedHint | None] = [None, None]
        self.final_round_started = False
        self.final_turns_taken = 0
        self.deck: list[Card] = clone_deck(deck) if deck is not None else build_standard_deck()
        if deck is None:
            self.deck = shuffled_deck()
        self._deal_initial_hands()

    def _deal_initial_hands(self) -> None:
        for _ in range(self.NUM_PLAYERS):
            self.knowledge.append(unknown_player_knowledge(self.HAND_SIZE))
        for player_index in range(self.NUM_PLAYERS):
            for _ in range(self.HAND_SIZE):
                self._draw_card(player_index)

    def _draw_card(self, player_index: int) -> None:
        if not self.deck:
            return
        self.hands[player_index].append(self.deck.pop(0))
        if len(self.knowledge[player_index].cards) < len(self.hands[player_index]):
            self.knowledge[player_index].append_unknown()

    def partner_of(self, player_index: int) -> int:
        return 1 - player_index

    def legal_actions(self, player_index: int | None = None) -> tuple[Action, ...]:
        player = self.current_player if player_index is None else player_index
        actions: list[Action] = []
        for card_index in range(len(self.hands[player])):
            actions.append(Action.play(card_index))
            if self.hints < self.MAX_HINTS:
                actions.append(Action.discard(card_index))

        if self.hints > 0:
            partner = self.partner_of(player)
            partner_hand = self.hands[partner]
            seen_colors = {card.color for card in partner_hand}
            seen_ranks = {card.rank for card in partner_hand}
            for color in COLORS:
                if color in seen_colors:
                    actions.append(Action.hint_color(partner, color))
            for rank in RANKS:
                if rank in seen_ranks:
                    actions.append(Action.hint_rank(partner, rank))
        return tuple(actions)

    def is_legal_action(self, action: Action, player_index: int | None = None) -> bool:
        return action in self.legal_actions(player_index)

    def _current_turn_view(self) -> TurnView:
        player = self.current_player
        partner = self.partner_of(player)
        my_public_counter = build_public_counter(
            visible_partner_hand=self.hands[partner],
            fireworks=self.fireworks,
            discard_pile=self.discard_pile,
        )
        partner_model_counter = build_public_counter(
            visible_partner_hand=self.hands[player],
            fireworks=self.fireworks,
            discard_pile=self.discard_pile,
        )
        return TurnView(
            player_index=player,
            partner_index=partner,
            my_hand_size=len(self.hands[player]),
            partner_hand=tuple(self.hands[partner]),
            my_mental_state=resolve_player_knowledge(self.knowledge[player], my_public_counter),
            partner_mental_state=resolve_player_knowledge(
                self.knowledge[partner],
                partner_model_counter,
            ),
            fireworks=dict(self.fireworks),
            discard_pile=tuple(self.discard_pile),
            hints=self.hints,
            max_hints=self.MAX_HINTS,
            mistakes_made=self.mistakes_made,
            max_mistakes=self.MAX_MISTAKES,
            deck_size=len(self.deck),
            turn_number=self.turn_number,
            legal_actions=self.legal_actions(player),
            pending_received_hint=self.pending_received_hints[player],
        )

    def get_view_for(self, player_index: int) -> TurnView:
        current = self.current_player
        self.current_player = player_index
        try:
            return self._current_turn_view()
        finally:
            self.current_player = current

    def apply_action(self, action: Action) -> GameEvent:
        if not self.is_legal_action(action):
            raise ValueError(f"Illegal action for player {self.current_player}: {action}")

        actor = self.current_player
        partner = self.partner_of(actor)
        deck_was_empty = not self.deck
        positive_indices: tuple[int, ...] = ()
        revealed_card: Card | None = None
        success: bool | None = None
        self.pending_received_hints[actor] = None

        if action.kind == "hint":
            assert action.hint is not None
            assert action.target_player == partner
            self.hints -= 1
            positive_indices, _changed = apply_hint_to_knowledge(
                self.knowledge[partner],
                self.hands[partner],
                action.hint,
            )
            self.pending_received_hints[partner] = ReceivedHint(
                hint=action.hint,
                positive_indices=positive_indices,
                source_player=actor,
            )
        elif action.kind == "play":
            assert action.card_index is not None
            revealed_card = self.hands[actor].pop(action.card_index)
            self.knowledge[actor].remove_card(action.card_index)
            success = is_playable(revealed_card, self.fireworks)
            if success:
                self.fireworks[revealed_card.color] += 1
                if revealed_card.rank == 5:
                    self.hints = min(self.MAX_HINTS, self.hints + 1)
            else:
                self.discard_pile.append(revealed_card)
                self.mistakes_made += 1
            self._draw_card(actor)
        elif action.kind == "discard":
            assert action.card_index is not None
            revealed_card = self.hands[actor].pop(action.card_index)
            self.knowledge[actor].remove_card(action.card_index)
            self.discard_pile.append(revealed_card)
            self.hints = min(self.MAX_HINTS, self.hints + 1)
            self._draw_card(actor)
        else:
            raise ValueError(f"Unknown action kind: {action.kind}")

        if deck_was_empty:
            self.final_turns_taken += 1
        elif not self.deck:
            self.final_round_started = True
            self.final_turns_taken = 0

        if not deck_was_empty and not self.deck:
            self.final_round_started = True

        event = GameEvent(
            actor=actor,
            action=action,
            positive_indices=positive_indices,
            revealed_card=revealed_card,
            success=success,
            hints_after=self.hints,
            mistakes_after=self.mistakes_made,
        )
        self.turn_log.append(
            TurnLogEntry(
                turn_number=self.turn_number,
                actor=actor,
                action=action,
                positive_indices=positive_indices,
                card=revealed_card,
                success=success,
                score_after=self.score(),
                hints_after=self.hints,
                mistakes_after=self.mistakes_made,
            ),
        )
        self.current_player = partner
        self.turn_number += 1
        return event

    def score(self) -> int:
        return sum(self.fireworks.values())

    def is_done(self) -> bool:
        if self.mistakes_made >= self.MAX_MISTAKES:
            return True
        if all(rank == 5 for rank in self.fireworks.values()):
            return True
        return self.final_round_started and self.final_turns_taken >= self.NUM_PLAYERS

    def play_game(self, agents: list["BaseAgent"]) -> int:
        if len(agents) != self.NUM_PLAYERS:
            raise ValueError("This reproduction only supports exactly two agents.")

        for index, agent in enumerate(agents):
            agent.reset(index)

        while not self.is_done():
            view = self._current_turn_view()
            action = agents[self.current_player].choose_action(view)
            event = self.apply_action(action)
            for agent in agents:
                agent.observe(event)
        return self.score()


from agents.base_agent import BaseAgent  # noqa: E402  pylint: disable=wrong-import-position
