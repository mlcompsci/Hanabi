from __future__ import annotations

from hanabi.state import Action, GameEvent, TurnView


class BaseAgent:
    """Base interface for all Hanabi agents in this project."""

    display_name = "Base"

    def __init__(self) -> None:
        self.player_index = -1

    def reset(self, player_index: int) -> None:
        self.player_index = player_index

    def choose_action(self, view: TurnView) -> Action:
        raise NotImplementedError

    def observe(self, event: GameEvent) -> None:
        del event

