from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents import create_agent
from hanabi.deck import shuffled_deck
from hanabi.game import HanabiGame


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single Hanabi game for inspection.")
    parser.add_argument("agent_a", choices=["outer", "intentional", "full"])
    parser.add_argument("agent_b", choices=["outer", "intentional", "full"])
    parser.add_argument("--seed", type=int, default=0, help="Shuffle seed for the deck.")
    args = parser.parse_args()

    game = HanabiGame(deck=shuffled_deck(args.seed))
    agents = [create_agent(args.agent_a), create_agent(args.agent_b)]
    score = game.play_game(agents)

    print(f"Final score: {score}")
    print(f"Hints left: {game.hints}")
    print(f"Mistakes made: {game.mistakes_made}")
    print("Turn log:")
    for entry in game.turn_log:
        detail = ""
        if entry.card is not None:
            detail = f" -> {entry.card}"
            if entry.success is not None:
                detail += " success" if entry.success else " fail"
        print(
            f"  T{entry.turn_number:02d} P{entry.actor} {entry.action.describe()}"
            f"{detail}; score={entry.score_after}, hints={entry.hints_after}, mistakes={entry.mistakes_after}"
        )


if __name__ == "__main__":
    main()
