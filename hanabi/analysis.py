from __future__ import annotations

from dataclasses import dataclass

from .cards import Card
from .mental_state import ResolvedMentalCard, ResolvedMentalState, apply_hint_to_resolved_state
from .rules import (
    card_has_expendable_identity,
    card_has_playable_identity,
    discard_heuristic_score,
    is_expendable,
    is_playable,
    is_useless,
)
from .state import Action, TurnView

PLAY = "play"
DISCARD = "discard"
MAY_DISCARD = "may_discard"
KEEP = "keep"


@dataclass(frozen=True)
class HintAssessment:
    action: Action
    score: int
    predictions: tuple[str, ...]
    valid: bool
    positive_indices: tuple[int, ...]


@dataclass(frozen=True)
class DiscardAssessment:
    card_index: int
    score: float


def form_intentions(
    partner_hand: tuple[Card, ...],
    fireworks: dict[str, int],
    discard_pile: tuple[Card, ...],
) -> tuple[str, ...]:
    intentions: list[str] = []
    for card in partner_hand:
        if is_playable(card, fireworks):
            intentions.append(PLAY)
        elif is_useless(card, fireworks, discard_pile):
            intentions.append(DISCARD)
        elif is_expendable(card, fireworks, discard_pile):
            intentions.append(MAY_DISCARD)
        else:
            intentions.append(KEEP)
    return tuple(intentions)


def predict_action_for_resolved_card(
    card: ResolvedMentalCard,
    fireworks: dict[str, int],
    discard_pile: tuple[Card, ...],
) -> str:
    if card_has_playable_identity(card, fireworks):
        return PLAY
    if card_has_expendable_identity(card, fireworks, discard_pile):
        return DISCARD
    return KEEP


def assess_hint(
    mental_state: ResolvedMentalState,
    partner_hand: tuple[Card, ...],
    action: Action,
    intentions: tuple[str, ...],
    fireworks: dict[str, int],
    discard_pile: tuple[Card, ...],
) -> HintAssessment:
    assert action.hint is not None
    updated_state, positive_indices, changed = apply_hint_to_resolved_state(
        mental_state,
        partner_hand,
        action.hint,
    )

    if not positive_indices or not changed:
        return HintAssessment(
            action=action,
            score=0,
            predictions=tuple(),
            valid=False,
            positive_indices=positive_indices,
        )

    predictions: list[str] = []
    score = 0
    positive_set = set(positive_indices)
    for index, intention in enumerate(intentions):
        if index in positive_set:
            predicted = predict_action_for_resolved_card(
                updated_state.cards[index],
                fireworks,
                discard_pile,
            )
        else:
            predicted = KEEP

        if predicted == PLAY and intention != PLAY:
            return HintAssessment(
                action=action,
                score=0,
                predictions=tuple(predictions),
                valid=False,
                positive_indices=positive_indices,
            )
        if predicted == DISCARD and intention in {PLAY, KEEP}:
            return HintAssessment(
                action=action,
                score=0,
                predictions=tuple(predictions),
                valid=False,
                positive_indices=positive_indices,
            )

        if predicted == PLAY and intention == PLAY:
            score += 3
        elif predicted == DISCARD and intention == DISCARD:
            score += 2
        elif predicted == DISCARD and intention == MAY_DISCARD:
            score += 1

        predictions.append(predicted)

    return HintAssessment(
        action=action,
        score=score,
        predictions=tuple(predictions),
        valid=True,
        positive_indices=positive_indices,
    )


def legal_hint_assessments(view: TurnView) -> list[HintAssessment]:
    intentions = form_intentions(view.partner_hand, view.fireworks, view.discard_pile)
    assessments: list[HintAssessment] = []
    for action in view.legal_actions:
        if action.kind != "hint" or action.hint is None:
            continue
        assessments.append(
            assess_hint(
                view.partner_mental_state,
                view.partner_hand,
                action,
                intentions,
                view.fireworks,
                view.discard_pile,
            ),
        )
    return assessments


def best_hint_assessment(view: TurnView) -> HintAssessment | None:
    best: HintAssessment | None = None
    for assessment in legal_hint_assessments(view):
        if not assessment.valid or assessment.score <= 0:
            continue
        if best is None or assessment.score > best.score:
            best = assessment
    return best


def discard_assessments(view: TurnView) -> list[DiscardAssessment]:
    return [
        DiscardAssessment(
            card_index=index,
            score=discard_heuristic_score(card, view.fireworks, view.discard_pile),
        )
        for index, card in enumerate(view.my_mental_state.cards)
    ]

