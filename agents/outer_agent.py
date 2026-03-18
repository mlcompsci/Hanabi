from __future__ import annotations

from hanabi.rules import card_is_known_playable, card_is_known_useless, is_playable
from hanabi.state import Action, GameEvent, TurnView

from .base_agent import BaseAgent


class OuterAgent(BaseAgent):
    display_name = "Outer"

    def __init__(self) -> None:
        super().__init__()
        self.sent_hint_history: dict[int, set[str]] = {}

    def reset(self, player_index: int) -> None:
        super().reset(player_index)
        self.sent_hint_history = {}

    def observe(self, event: GameEvent) -> None:
        partner_index = 1 - self.player_index

        if (
            event.actor == self.player_index
            and event.action.kind == "hint"
            and event.action.target_player == partner_index
            and event.action.hint is not None
        ):
            for index in event.positive_indices:
                self.sent_hint_history.setdefault(index, set()).add(event.action.hint.kind)

        if event.actor == partner_index and event.action.kind in {"play", "discard"}:
            removed_index = event.action.card_index
            if removed_index is None:
                return
            shifted: dict[int, set[str]] = {}
            for index, kinds in self.sent_hint_history.items():
                if index < removed_index:
                    shifted[index] = set(kinds)
                elif index > removed_index:
                    shifted[index - 1] = set(kinds)
            self.sent_hint_history = shifted

    def choose_action(self, view: TurnView) -> Action:
        for index, card in enumerate(view.my_mental_state.cards):
            if card_is_known_playable(card, view.fireworks):
                return Action.play(index)

        if view.hints < view.max_hints:
            for index, card in enumerate(view.my_mental_state.cards):
                if card_is_known_useless(card, view.fireworks, view.discard_pile):
                    return Action.discard(index)

        if view.hints > 0:
            hint_action = self._choose_hint(view)
            if hint_action is not None:
                return hint_action
            fallback_hint = self._fallback_hint(view)
            if fallback_hint is not None:
                return fallback_hint

        if view.hints < view.max_hints:
            return Action.discard(0)
        return view.legal_actions[0]

    def _choose_hint(self, view: TurnView) -> Action | None:
        playable_indices = [
            index
            for index, card in enumerate(view.partner_hand)
            if is_playable(card, view.fireworks)
        ]
        playable_indices.sort(key=lambda index: (-view.partner_hand[index].rank, index))

        for index in playable_indices:
            action = self._new_hint_for_slot(view, index)
            if action is not None:
                return action

        for index in range(len(view.partner_hand)):
            action = self._new_hint_for_slot(view, index)
            if action is not None:
                return action
        return None

    def _new_hint_for_slot(self, view: TurnView, index: int) -> Action | None:
        card = view.partner_hand[index]
        history = self.sent_hint_history.get(index, set())
        if "rank" not in history:
            return Action.hint_rank(view.partner_index, card.rank)
        if "color" not in history:
            return Action.hint_color(view.partner_index, card.color)
        return None

    def _fallback_hint(self, view: TurnView) -> Action | None:
        for action in view.legal_actions:
            if action.kind == "hint":
                return action
        return None
