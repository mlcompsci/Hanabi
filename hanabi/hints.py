from __future__ import annotations

from dataclasses import dataclass

from .cards import COLORS, Card, RANKS


@dataclass(frozen=True)
class Hint:
    kind: str
    value: str | int

    def __post_init__(self) -> None:
        if self.kind not in {"color", "rank"}:
            raise ValueError(f"Unknown hint kind: {self.kind}")
        if self.kind == "color" and self.value not in COLORS:
            raise ValueError(f"Unknown color hint: {self.value}")
        if self.kind == "rank" and self.value not in RANKS:
            raise ValueError(f"Unknown rank hint: {self.value}")

    def matches(self, card: Card) -> bool:
        if self.kind == "color":
            return card.color == self.value
        return card.rank == self.value

    def label(self) -> str:
        return f"{self.kind}:{self.value}"

    def __str__(self) -> str:
        if self.kind == "color":
            return f"color {self.value}"
        return f"rank {self.value}"

