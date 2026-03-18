from __future__ import annotations

from collections import Counter
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents import create_agent
from hanabi.cards import Card
from hanabi.deck import build_standard_deck
from hanabi.game import HanabiGame
from hanabi.mental_state import ResolvedMentalCard
from hanabi.rules import discard_heuristic_score
from hanabi.state import ALLOWED_ACTION_KINDS, Action


def make_custom_deck(prefix: list[Card]) -> list[Card]:
    deck = build_standard_deck()
    remaining = Counter(deck)
    for card in prefix:
        if remaining[card] <= 0:
            raise ValueError(f"Prefix overuses card {card}")
        remaining[card] -= 1

    tail: list[Card] = []
    for card, count in remaining.items():
        tail.extend([card] * count)
    return prefix + tail


def check_hint_legality() -> None:
    deck = make_custom_deck(
        [
            Card("green", 1),
            Card("green", 2),
            Card("yellow", 3),
            Card("white", 4),
            Card("blue", 5),
            Card("blue", 1),
            Card("blue", 2),
            Card("yellow", 4),
            Card("white", 3),
            Card("green", 5),
        ],
    )
    game = HanabiGame(deck=deck)
    assert Action.hint_color(1, "red") not in game.legal_actions()
    try:
        game.apply_action(Action.hint_color(1, "red"))
    except ValueError:
        return
    raise AssertionError("Illegal hint was accepted by the engine.")


def check_hint_updates_mental_state() -> None:
    deck = make_custom_deck(
        [
            Card("green", 1),
            Card("yellow", 2),
            Card("white", 3),
            Card("blue", 4),
            Card("red", 5),
            Card("green", 1),
            Card("blue", 2),
            Card("yellow", 4),
            Card("white", 3),
            Card("green", 5),
        ],
    )
    game = HanabiGame(deck=deck)
    game.apply_action(Action.hint_rank(1, 1))
    view = game.get_view_for(1)
    first_card = view.my_mental_state.cards[0]
    second_card = view.my_mental_state.cards[1]
    assert all(card.rank == 1 for card in first_card.possible_cards())
    assert all(card.rank != 1 for card in second_card.possible_cards())


def check_partner_model_counts_visible_hand() -> None:
    deck = make_custom_deck(
        [
            Card("red", 1),
            Card("green", 2),
            Card("yellow", 3),
            Card("white", 4),
            Card("blue", 5),
            Card("green", 1),
            Card("blue", 2),
            Card("yellow", 4),
            Card("white", 3),
            Card("green", 5),
        ],
    )
    game = HanabiGame(deck=deck)
    view = game.get_view_for(0)
    red_one = Card("red", 1)
    assert red_one in game.hands[0]
    partner_counts = view.partner_mental_state.cards[0].counts
    assert partner_counts[red_one] == 2


def check_action_model_is_limited_to_three_types() -> None:
    game = HanabiGame(deck=build_standard_deck())
    assert {action.kind for action in game.legal_actions()} <= ALLOWED_ACTION_KINDS
    try:
        Action(kind="swap")
    except ValueError:
        return
    raise AssertionError("Action accepted a kind outside play/discard/hint.")


def check_discard_heuristic_probability_weighting() -> None:
    card = ResolvedMentalCard(
        counts={
            Card("green", 4): 1,
            Card("blue", 4): 1,
        },
    )
    score = discard_heuristic_score(
        card,
        fireworks={color: 0 for color in ("green", "yellow", "white", "blue", "red")},
        discard_pile=(),
    )
    expected = -0.125
    assert abs(score - expected) < 1e-9


def check_discard_requires_open_hint_slot() -> None:
    game = HanabiGame(deck=build_standard_deck())
    assert game.hints == game.MAX_HINTS
    assert Action.discard(0) not in game.legal_actions()
    try:
        game.apply_action(Action.discard(0))
    except ValueError:
        return
    raise AssertionError("Discard was accepted even though hint tokens were already full.")


def check_play_and_discard_update_knowledge() -> None:
    deck = make_custom_deck(
        [
            Card("green", 1),
            Card("yellow", 2),
            Card("white", 3),
            Card("blue", 4),
            Card("red", 5),
            Card("green", 1),
            Card("blue", 2),
            Card("yellow", 4),
            Card("white", 3),
            Card("green", 5),
            Card("red", 1),
            Card("blue", 1),
        ],
    )
    game = HanabiGame(deck=deck)
    before_play = game.get_view_for(0)
    assert len(before_play.my_mental_state.cards) == 5
    assert before_play.my_mental_state.cards[0].possible_cards()
    game.apply_action(Action.play(0))
    after_play = game.get_view_for(0)
    assert len(after_play.my_mental_state.cards) == 5
    assert after_play.my_mental_state.cards[-1].possible_cards()

    assert Action.discard(0) not in game.legal_actions()
    game.apply_action(Action.hint_rank(0, 1))
    game.apply_action(Action.discard(0))
    partner_view = game.get_view_for(1)
    assert len(partner_view.my_mental_state.cards) == 5


def check_all_pairings() -> None:
    pairings = [
        ("outer", "outer"),
        ("outer", "intentional"),
        ("outer", "full"),
        ("intentional", "outer"),
        ("intentional", "intentional"),
        ("intentional", "full"),
        ("full", "outer"),
        ("full", "intentional"),
        ("full", "full"),
    ]
    for seed, (agent_a, agent_b) in enumerate(pairings):
        from hanabi.deck import shuffled_deck

        game = HanabiGame(deck=shuffled_deck(seed))
        score = game.play_game([create_agent(agent_a), create_agent(agent_b)])
        assert 0 <= score <= 25


def main() -> None:
    check_action_model_is_limited_to_three_types()
    check_hint_legality()
    check_hint_updates_mental_state()
    check_partner_model_counts_visible_hand()
    check_discard_heuristic_probability_weighting()
    check_discard_requires_open_hint_slot()
    check_play_and_discard_update_knowledge()
    check_all_pairings()
    print("Validation passed: legality, mental-state updates, and all pairings ran successfully.")


if __name__ == "__main__":
    main()
