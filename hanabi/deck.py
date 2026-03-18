from __future__ import annotations

import random
from typing import Sequence

from .cards import COLORS, RANKS, Card, card_copies


def build_standard_deck() -> list[Card]:
    deck: list[Card] = []
    for color in COLORS:
        for rank in RANKS:
            deck.extend(Card(color, rank) for _ in range(card_copies(rank)))
    return deck


def shuffled_deck(seed: int | None = None) -> list[Card]:
    rng = random.Random(seed)
    deck = build_standard_deck()
    rng.shuffle(deck)
    return deck


def clone_deck(cards: Sequence[Card]) -> list[Card]:
    return list(cards)

