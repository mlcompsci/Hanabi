from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .cards import COLORS, RANKS, Card, all_cards, card_copies
from .hints import Hint


def _fresh_color_mask() -> dict[str, bool]:
    return {color: True for color in COLORS}


def _fresh_rank_mask() -> dict[int, bool]:
    return {rank: True for rank in RANKS}


@dataclass
class MentalCardKnowledge:
    color_allowed: dict[str, bool] = field(default_factory=_fresh_color_mask)
    rank_allowed: dict[int, bool] = field(default_factory=_fresh_rank_mask)

    def copy(self) -> "MentalCardKnowledge":
        return MentalCardKnowledge(
            color_allowed=dict(self.color_allowed),
            rank_allowed=dict(self.rank_allowed),
        )

    def apply_hint(self, hint: Hint, positive: bool) -> None:
        if hint.kind == "color":
            for color in COLORS:
                if positive:
                    self.color_allowed[color] = color == hint.value
                elif color == hint.value:
                    self.color_allowed[color] = False
            return

        for rank in RANKS:
            if positive:
                self.rank_allowed[rank] = rank == hint.value
            elif rank == hint.value:
                self.rank_allowed[rank] = False


@dataclass(frozen=True)
class ResolvedMentalCard:
    counts: dict[Card, int]

    def possible_cards(self) -> list[Card]:
        return [card for card, count in self.counts.items() if count > 0]

    def possible_cards_with_counts(self) -> list[tuple[Card, int]]:
        return [(card, count) for card, count in self.counts.items() if count > 0]

    def total_count(self) -> int:
        return sum(self.counts.values())

    def is_identified(self) -> bool:
        return len(self.possible_cards()) == 1

    def matrix(self) -> list[list[int]]:
        return [[self.counts[Card(color, rank)] for rank in RANKS] for color in COLORS]

    def apply_hint(self, hint: Hint, positive: bool) -> "ResolvedMentalCard":
        filtered: dict[Card, int] = {}
        for card, count in self.counts.items():
            matches = hint.matches(card)
            filtered[card] = count if matches == positive else 0
        return ResolvedMentalCard(filtered)


@dataclass(frozen=True)
class ResolvedMentalState:
    cards: tuple[ResolvedMentalCard, ...]


@dataclass
class PlayerKnowledge:
    cards: list[MentalCardKnowledge] = field(default_factory=list)

    def copy(self) -> "PlayerKnowledge":
        return PlayerKnowledge(cards=[card.copy() for card in self.cards])

    def remove_card(self, index: int) -> None:
        del self.cards[index]

    def append_unknown(self) -> None:
        self.cards.append(MentalCardKnowledge())


def build_public_counter(
    visible_partner_hand: list[Card] | tuple[Card, ...],
    fireworks: dict[str, int],
    discard_pile: list[Card] | tuple[Card, ...],
) -> Counter[Card]:
    counter: Counter[Card] = Counter(discard_pile)
    counter.update(visible_partner_hand)
    for color in COLORS:
        for rank in range(1, fireworks[color] + 1):
            counter[Card(color, rank)] += 1
    return counter


def resolve_card_knowledge(
    knowledge: MentalCardKnowledge,
    public_counter: Counter[Card],
) -> ResolvedMentalCard:
    counts: dict[Card, int] = {}
    for color in COLORS:
        for rank in RANKS:
            card = Card(color, rank)
            if not knowledge.color_allowed[color] or not knowledge.rank_allowed[rank]:
                counts[card] = 0
                continue
            counts[card] = max(card_copies(rank) - public_counter[card], 0)
    return ResolvedMentalCard(counts=counts)


def resolve_player_knowledge(
    knowledge: PlayerKnowledge,
    public_counter: Counter[Card],
) -> ResolvedMentalState:
    return ResolvedMentalState(
        cards=tuple(resolve_card_knowledge(card, public_counter) for card in knowledge.cards),
    )


def apply_hint_to_knowledge(
    knowledge: PlayerKnowledge,
    hand: list[Card] | tuple[Card, ...],
    hint: Hint,
) -> tuple[tuple[int, ...], bool]:
    positive_indices: list[int] = []
    changed = False
    for index, (card, mental_card) in enumerate(zip(hand, knowledge.cards, strict=True)):
        positive = hint.matches(card)
        if positive:
            positive_indices.append(index)
        before = mental_card.copy()
        mental_card.apply_hint(hint, positive)
        if mental_card != before:
            changed = True
    return tuple(positive_indices), changed


def apply_hint_to_resolved_state(
    state: ResolvedMentalState,
    hand: list[Card] | tuple[Card, ...],
    hint: Hint,
) -> tuple[ResolvedMentalState, tuple[int, ...], bool]:
    updated_cards: list[ResolvedMentalCard] = []
    positive_indices: list[int] = []
    changed = False
    for index, (card, mental_card) in enumerate(zip(hand, state.cards, strict=True)):
        positive = hint.matches(card)
        if positive:
            positive_indices.append(index)
        updated = mental_card.apply_hint(hint, positive)
        if updated.counts != mental_card.counts:
            changed = True
        updated_cards.append(updated)
    return ResolvedMentalState(cards=tuple(updated_cards)), tuple(positive_indices), changed


def unknown_player_knowledge(hand_size: int) -> PlayerKnowledge:
    return PlayerKnowledge(cards=[MentalCardKnowledge() for _ in range(hand_size)])


def empty_resolved_state() -> ResolvedMentalState:
    empty_counts = {card: 0 for card in all_cards()}
    return ResolvedMentalState(cards=tuple(ResolvedMentalCard(dict(empty_counts)) for _ in range(0)))

