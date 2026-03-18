from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents import create_agent
from hanabi.deck import build_standard_deck
from hanabi.game import HanabiGame

from experiments.configs import AGENT_ORDER, DEFAULT_GAMES, DEFAULT_SEED


@dataclass(frozen=True)
class PairingResult:
    average_score: float
    sample_stddev: float


def generate_shared_decks(num_games: int, seed: int) -> list[list]:
    import random

    rng = random.Random(seed)
    decks: list[list] = []
    for _ in range(num_games):
        deck = build_standard_deck()
        rng.shuffle(deck)
        decks.append(deck)
    return decks


def run_pairing(agent_a: str, agent_b: str, decks: list[list]) -> list[int]:
    scores: list[int] = []
    for deck in decks:
        game = HanabiGame(deck=deck)
        agents = [create_agent(agent_a), create_agent(agent_b)]
        scores.append(game.play_game(agents))
    return scores


def summarize(scores: list[int]) -> PairingResult:
    if not scores:
        return PairingResult(average_score=0.0, sample_stddev=0.0)
    if len(scores) == 1:
        return PairingResult(average_score=float(scores[0]), sample_stddev=0.0)
    return PairingResult(
        average_score=statistics.mean(scores),
        sample_stddev=statistics.stdev(scores),
    )


def format_result(result: PairingResult) -> str:
    return f"{result.average_score:>5.2f} ({result.sample_stddev:>4.2f})"


def print_matrix(results: dict[tuple[str, str], PairingResult]) -> None:
    column_width = 16
    header = "Agent \\ Partner".ljust(column_width) + "".join(
        name.title().ljust(column_width) for name in AGENT_ORDER
    )
    print(header)
    for row_agent in AGENT_ORDER:
        line = row_agent.title().ljust(column_width)
        for col_agent in AGENT_ORDER:
            line += format_result(results[(row_agent, col_agent)]).ljust(column_width)
        print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pairwise Hanabi self-play simulations.")
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES, help="Number of shared decks to evaluate.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Seed for generating shared deck orders.")
    args = parser.parse_args()

    decks = generate_shared_decks(args.games, args.seed)
    results: dict[tuple[str, str], PairingResult] = {}

    for row_agent in AGENT_ORDER:
        for col_agent in AGENT_ORDER:
            scores = run_pairing(row_agent, col_agent, decks)
            results[(row_agent, col_agent)] = summarize(scores)

    print(f"Games per pairing: {args.games}")
    print(f"Shared deck seed: {args.seed}")
    print_matrix(results)


if __name__ == "__main__":
    main()
