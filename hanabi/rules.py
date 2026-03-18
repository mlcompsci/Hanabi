from __future__ import annotations

from collections import Counter

from .cards import COLORS, Card, card_copies
from .hints import Hint
from .mental_state import ResolvedMentalCard

HINT_VALUE = 0.5


def is_playable(card: Card, fireworks: dict[str, int]) -> bool:
    return fireworks[card.color] + 1 == card.rank


def is_useless(
    card: Card,
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> bool:
    if fireworks[card.color] >= card.rank:
        return True

    discard_counter = Counter(discard_pile)
    for required_rank in range(fireworks[card.color] + 1, card.rank):
        required_card = Card(card.color, required_rank)
        if discard_counter[required_card] >= card_copies(required_rank):
            return True
    return False


def is_expendable(
    card: Card,
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> bool:
    if is_useless(card, fireworks, discard_pile):
        return True
    discard_counter = Counter(discard_pile)
    return card_copies(card.rank) - discard_counter[card] >= 2


def positively_identified(card: Card, hint: Hint) -> bool:
    return hint.matches(card)


def card_is_known_playable(card: ResolvedMentalCard, fireworks: dict[str, int]) -> bool:
    possible = card.possible_cards()
    return bool(possible) and all(is_playable(identity, fireworks) for identity in possible)


def card_is_known_useless(
    card: ResolvedMentalCard,
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> bool:
    possible = card.possible_cards()
    return bool(possible) and all(is_useless(identity, fireworks, discard_pile) for identity in possible)


def card_has_playable_identity(card: ResolvedMentalCard, fireworks: dict[str, int]) -> bool:
    return any(is_playable(identity, fireworks) for identity in card.possible_cards())


def card_has_expendable_identity(
    card: ResolvedMentalCard,
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> bool:
    return any(is_expendable(identity, fireworks, discard_pile) for identity in card.possible_cards())


def discard_heuristic_score(
    card: ResolvedMentalCard,
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> float:
    total = card.total_count()
    if total == 0:
        return float("-inf")

    expected = 0.0
    for identity, count in card.possible_cards_with_counts():
        probability = count / total
        if is_useless(identity, fireworks, discard_pile):
            expected += probability * HINT_VALUE
            continue

        distance = identity.rank - fireworks[identity.color]
        if distance <= 0:
            expected += probability * HINT_VALUE
            continue

        if is_expendable(identity, fireworks, discard_pile):
            loss = (6 - identity.rank) / (distance * distance)
        else:
            loss = float(6 - identity.rank)

        if identity.rank == 5:
            loss += HINT_VALUE

        expected -= probability * loss
    return expected


def format_fireworks(fireworks: dict[str, int]) -> str:
    return ", ".join(f"{color}:{fireworks[color]}" for color in COLORS)
