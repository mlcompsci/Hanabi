from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

COLORS: tuple[str, ...] = ("green", "yellow", "white", "blue", "red")
RANKS: tuple[int, ...] = (1, 2, 3, 4, 5)
COPIES_BY_RANK: dict[int, int] = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}


@dataclass(frozen=True, order=True)
class Card:
    color: str
    rank: int

    def __post_init__(self) -> None:
        if self.color not in COLORS:
            raise ValueError(f"Unknown color: {self.color}")
        if self.rank not in RANKS:
            raise ValueError(f"Unknown rank: {self.rank}")

    @property
    def short(self) -> str:
        return f"{self.color[0].upper()}{self.rank}"

    def __str__(self) -> str:
        return f"{self.color} {self.rank}"


def card_copies(rank: int) -> int:
    return COPIES_BY_RANK[rank]


def all_cards() -> list[Card]:
    return [Card(color, rank) for color in COLORS for rank in RANKS]


def count_cards(cards: Iterable[Card]) -> Counter[Card]:
    return Counter(cards)

