from __future__ import annotations

from hanabi.analysis import DISCARD, KEEP, PLAY, predict_action_for_resolved_card
from hanabi.state import Action, TurnView

from .intentional_agent import IntentionalAgent


class FullAgent(IntentionalAgent):
    display_name = "Full"

    def choose_action(self, view: TurnView) -> Action:
        interpreted = self._interpret_received_hint(view)
        if interpreted is not None:
            return interpreted
        return super().choose_action(view)

    def _interpret_received_hint(self, view: TurnView) -> Action | None:
        pending = view.pending_received_hint
        if pending is None:
            return None

        play_indices: list[int] = []
        discard_indices: list[int] = []

        for index in pending.positive_indices:
            mental_card = view.my_mental_state.cards[index]
            predicted = predict_action_for_resolved_card(
                mental_card,
                view.fireworks,
                view.discard_pile,
            )
            if predicted == PLAY:
                play_indices.append(index)
            elif predicted == DISCARD:
                discard_indices.append(index)

        if play_indices:
            return Action.play(play_indices[0])
        if discard_indices and view.hints < view.max_hints:
            return Action.discard(discard_indices[0])
        return None
