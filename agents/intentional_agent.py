from __future__ import annotations

from hanabi.analysis import (
    MAY_DISCARD,
    PLAY,
    best_hint_assessment,
    discard_assessments,
    form_intentions,
)
from hanabi.rules import (
    card_is_known_playable,
    card_is_known_useless,
)
from hanabi.state import Action, TurnView

from .base_agent import BaseAgent


class IntentionalAgent(BaseAgent):
    display_name = "Intentional"

    def choose_action(self, view: TurnView) -> Action:
        known_play = self._known_play(view)
        if known_play is not None:
            return known_play

        if view.hints < view.max_hints:
            known_useless_discard = self._known_useless_discard(view)
            if known_useless_discard is not None:
                return known_useless_discard

        fallback_hint: Action | None = None
        if view.hints > 0:
            best_hint = self._best_hint(view)
            if best_hint is not None:
                return best_hint
            fallback_hint = self._fallback_hint(view)
            if view.hints == view.max_hints and fallback_hint is not None:
                return fallback_hint

        if view.hints < view.max_hints:
            return self._best_discard(view)
        if fallback_hint is not None:
            return fallback_hint
        return view.legal_actions[0]

    def _known_play(self, view: TurnView) -> Action | None:
        for index, card in enumerate(view.my_mental_state.cards):
            if card_is_known_playable(card, view.fireworks):
                return Action.play(index)
        return None

    def _known_useless_discard(self, view: TurnView) -> Action | None:
        for index, card in enumerate(view.my_mental_state.cards):
            if card_is_known_useless(card, view.fireworks, view.discard_pile):
                return Action.discard(index)
        return None

    def _best_hint(self, view: TurnView) -> Action | None:
        best = best_hint_assessment(view)
        return best.action if best is not None else None

    def _best_discard(self, view: TurnView) -> Action:
        assessments = discard_assessments(view)
        best = max(assessments, key=lambda assessment: assessment.score)
        return Action.discard(best.card_index)

    def _fallback_hint(self, view: TurnView) -> Action | None:
        for action in view.legal_actions:
            if action.kind == "hint":
                return action
        return None
