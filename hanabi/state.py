from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Card
from .hints import Hint
from .mental_state import ResolvedMentalState

ALLOWED_ACTION_KINDS = frozenset({"play", "discard", "hint"})


@dataclass(frozen=True)
class Action:
    kind: str
    card_index: int | None = None
    target_player: int | None = None
    hint: Hint | None = None

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_ACTION_KINDS:
            raise ValueError(f"Unknown action kind: {self.kind}")

        if self.kind in {"play", "discard"}:
            if self.card_index is None:
                raise ValueError(f"{self.kind} actions require a card index.")
            if self.target_player is not None or self.hint is not None:
                raise ValueError(f"{self.kind} actions cannot include a target player or hint.")
            return

        if self.card_index is not None:
            raise ValueError("Hint actions cannot include a card index.")
        if self.target_player is None or self.hint is None:
            raise ValueError("Hint actions require both a target player and a hint.")

    @classmethod
    def play(cls, card_index: int) -> "Action":
        return cls(kind="play", card_index=card_index)

    @classmethod
    def discard(cls, card_index: int) -> "Action":
        return cls(kind="discard", card_index=card_index)

    @classmethod
    def hint_color(cls, target_player: int, color: str) -> "Action":
        return cls(kind="hint", target_player=target_player, hint=Hint("color", color))

    @classmethod
    def hint_rank(cls, target_player: int, rank: int) -> "Action":
        return cls(kind="hint", target_player=target_player, hint=Hint("rank", rank))

    def describe(self) -> str:
        if self.kind == "play":
            return f"play card {self.card_index}"
        if self.kind == "discard":
            return f"discard card {self.card_index}"
        return f"hint player {self.target_player} about {self.hint}"


@dataclass(frozen=True)
class ReceivedHint:
    hint: Hint
    positive_indices: tuple[int, ...]
    source_player: int


@dataclass(frozen=True)
class GameEvent:
    actor: int
    action: Action
    positive_indices: tuple[int, ...] = ()
    revealed_card: Card | None = None
    success: bool | None = None
    hints_after: int | None = None
    mistakes_after: int | None = None


@dataclass(frozen=True)
class TurnView:
    player_index: int
    partner_index: int
    my_hand_size: int
    partner_hand: tuple[Card, ...]
    my_mental_state: ResolvedMentalState
    partner_mental_state: ResolvedMentalState
    fireworks: dict[str, int]
    discard_pile: tuple[Card, ...]
    hints: int
    max_hints: int
    mistakes_made: int
    max_mistakes: int
    deck_size: int
    turn_number: int
    legal_actions: tuple[Action, ...]
    pending_received_hint: ReceivedHint | None = None

    @property
    def score(self) -> int:
        return sum(self.fireworks.values())
