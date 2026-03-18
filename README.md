# Intentional Hanabi (2-Player Reproduction)

This repository reproduces the 2-player Hanabi agents described in the paper **"An Intentional AI for Hanabi"** as a clarity-first Python project. The implementation focuses on the paper's agent architecture rather than modern search or learning methods, and includes:

- the Outer State baseline
- the Intentional AI
- the Full AI
- pairwise self-play simulations across all ordered pairings

The project is intentionally restricted to **2-player Hanabi** and does not generalize the agent logic to 3+ players.

## Paper Citation

Primary reproduced paper:

Eger, Markus, Chris Martens, and Marcela Alfaro Cordoba. **"An Intentional AI for Hanabi."** *2017 IEEE Conference on Computational Intelligence and Games (CIG 2017)*, pp. 68-75, 2017.

Baseline strategy context:

Osawa, Hirotaka. **"Solving Hanabi: Estimating Hands by Opponent's Actions in Cooperative Game with Incomplete Information."** *Workshops at the Twenty-Ninth AAAI Conference on Artificial Intelligence*, 2015.

## What Was Implemented

- A correct 2-player Hanabi engine with the standard 50-card deck, 5-card hands, 8 hints, 3 mistakes, hint/play/discard actions, draw-after-play-or-discard, and endgame final turns after the deck empties.
- Paper-style mental-state tracking for hidden cards using per-card color/rank count matrices.
- Public-information card counting from played cards, discarded cards, and the visible partner hand.
- Helper predicates matching the paper terminology: `Playable`, `Useless`, `Expendable`, and positive hint identification.
- The Outer baseline using known playable / known useless checks and simple non-intentional hinting.
- The Intentional AI with intention formation, hint prediction, hint scoring, and a paper-style discard heuristic.
- The Full AI with intentional interpretation of received hints using the same prediction logic.
- Pairwise simulation tooling for all ordered pairings among `Outer`, `Intentional`, and `Full`.
- A local web UI so a human can play in the browser against the paper-style agents and inspect live discard and hint scores.
- A local Tkinter UI so a human can play against the paper-style agents and inspect live discard and hint scores.
- A small validation script covering legality, knowledge updates, and smoke tests for all pairings.

## Repository Layout

| Path | Purpose | Paper Section |
| --- | --- | --- |
| `hanabi/cards.py` | Card identities, colors, ranks, multiplicities | II, IV-A |
| `hanabi/deck.py` | Standard deck construction and shuffling | II |
| `hanabi/game.py` | 2-player engine, action legality, end conditions, game loop | II |
| `hanabi/state.py` | Action, event, turn-view, and hint-record data structures | II, IV-D |
| `hanabi/hints.py` | Hint representation and matching | II, IV-B, IV-D |
| `hanabi/mental_state.py` | Hidden-card knowledge, hint application, resolved count matrices | IV-A |
| `hanabi/rules.py` | `Playable`, `Useless`, `Expendable`, known-playable/useless, discard heuristic | II, IV-B, IV-C, IV-D |
| `hanabi/analysis.py` | Reusable Intentional/Full heuristic analysis for agents and UI | IV-B, IV-C, IV-D |
| `agents/base_agent.py` | Shared agent interface | N/A |
| `agents/outer_agent.py` | Outer baseline | IV outline, Osawa baseline |
| `agents/intentional_agent.py` | Intentional hinting and discard logic | IV-B, IV-C |
| `agents/full_agent.py` | Intentional hint interpretation on receipt | IV-D |
| `experiments/run_single_game.py` | Inspect one ordered pairing on one shuffle | Reproduction support |
| `experiments/run_pairwise_simulations.py` | All ordered pairings on shared deck orders | V, Table II |
| `experiments/validate_project.py` | Legality and smoke-test checks | Reproduction support |
| `webui/server.py` | Local HTTP server and browser-playable web UI | Reproduction support |
| `ui/hanabi_tk.py` | Human-vs-agent desktop UI with live heuristic inspector | Reproduction support |

## Assumptions Where The Paper Was Underspecified

The paper gives the high-level logic clearly, but leaves a few implementation details open. This reproduction uses the simplest reasonable choices and keeps them explicit:

1. **2-player only.**
   Everything is hard-coded to the 2-player version described in the paper.

2. **Deterministic tie-breaking.**
   When multiple equivalent choices exist, the code uses deterministic ordering for reproducibility:
   leftmost cards first, stable action ordering, and deterministic hint selection.

3. **Outer baseline hinting is simple and non-intentional.**
   The baseline hints the highest-rank visible playable partner card first, preferring an unseen rank hint before an unseen color hint. If no playable card is targeted, it gives the first unseen simple hint on the partner's hand. It does not use intentional hint scoring or intentional interpretation.

4. **Partner mental-state modeling mirrors the paper's visibility assumptions.**
   A player's own mental state `MA` and the modeled cooperator state `MB` both use card counting from played cards, discarded cards, and the cards visible in the other player's hand, matching the paper's mental-state description.

5. **Per-card counting is implemented, but not full joint hand inference.**
   Each hidden card tracks how many copies of each identity are still individually consistent with that slot. The project does not perform a full cross-slot joint constraint solve over all hidden cards simultaneously, because the paper does not specify that stronger inference step.

6. **`Useless` and `Expendable` are implemented as rule predicates over game state.**
   `Useless` means the card is already played or blocked forever by missing lower ranks. `Expendable` means discarding it would not necessarily reduce the maximum possible score, which in this implementation includes useless cards and identities with another surviving copy.

7. **Known-useless auto-discard in Intentional/Full follows the reference behavior.**
   These agents immediately discard a known useless card only when hints are not already full. At 8 hints they look for a hint first, since discarding cannot increase the hint pool further.

8. **Discard heuristic uses an explicit numerical approximation.**
   For a hidden card with identity probability `p`:
   - useless identity contribution: `+0.5 * p`
   - otherwise let `distance = rank - fireworks[color]`
   - expendable identity loss: `p * (6 - rank) / distance^2`
   - non-expendable identity loss: `6 - rank`
   - discarding a 5 adds an extra `0.5` loss term
   - the total discard score is the probability-weighted sum of those contributions, and the agent discards the highest-scoring slot

   This is intentionally close to the paper's stated principles:
   earlier-useful cards matter more, non-expendable cards matter more, and hints are worth half a point.

## Running The Project

The project uses only the Python standard library. Python 3.12+ was used for validation.

Run one game:

```bash
python -m experiments.run_single_game outer full --seed 0
```

Run all ordered pairings on shared shuffles:

```bash
python -m experiments.run_pairwise_simulations --games 1000 --seed 0
```

Run the small validation suite:

```bash
python -m experiments.validate_project
```

Launch the desktop UI:

```bash
python -m ui.hanabi_tk
```

Launch the web UI:

```bash
python -m webui.server --open-browser
```

If you prefer to open the browser yourself:

```bash
python -m webui.server
```

Then visit `http://127.0.0.1:8000/`.

The scripts also work when invoked by file path from the repository root, for example:

```bash
python experiments/run_pairwise_simulations.py --games 100 --seed 0
```

## Expected Output Format

Single-game runs print a final score plus a readable turn log.

The desktop UI shows:

- the AI's visible hand
- your hidden hand as knowledge summaries instead of revealed cards
- live discard heuristic scores for each of your slots
- partner intentions and legal hint scores under the Intentional heuristic
- a running turn log

The web UI shows the same information in the browser, with:

- a local HTTP server and single-page interface
- a `Human Play` tab for playing against an agent
- an `AI Match` tab for running face-up AI-vs-AI games and reviewing the full result log
- browser controls for play, discard, and hint actions
- a live heuristic inspector backed by the exact same shared scoring code used by the Intentional and Full agents

Pairwise simulations print a matrix with:

- ordered row agent
- ordered column partner agent
- average score
- sample standard deviation

Example shape:

```text
Games per pairing: 100
Shared deck seed: 0
Agent \ Partner Outer           Intentional     Full
Outer           14.10 (1.98)    12.57 (2.29)     7.39 (3.95)
Intentional     13.04 (2.26)    11.11 (2.34)    13.30 (2.83)
Full             8.95 (4.10)    12.90 (2.47)    16.57 (2.21)
```

## Validation Performed

Before finalizing this reproduction, the following checks were run locally:

- syntax compilation across `hanabi/`, `agents/`, `experiments/`, and `ui/`
- a legality check that illegal hints are rejected by the engine
- mental-state update checks after hints, plays, and discards
- smoke-test full games for all ordered pairings
- an in-process HTTP smoke test for the web UI API
- a safe Tkinter import smoke test for the UI entrypoint
- a 100-game shared-shuffle matrix run across all pairings

The paper's full 10,000-game setup is supported by the experiment runner, but was not run as part of the local quick validation pass because it is slower.

## Faithfulness Notes And Limitations

- This is a research reproduction, not a performance-optimized Hanabi engine.
- The implementation intentionally avoids RL, deep learning, MCTS, and unrelated heuristic systems.
- The strongest source of unavoidable ambiguity is the paper's underspecification around tie-breaking, the exact baseline hint policy, and the numeric discard approximation.
- The qualitative interaction pattern in small validation runs matches the paper well:
  `Full/Full` is strongest, `Outer/Full` is fragile, and `Intentional/Intentional` can stall because hint-giving and hint-interpretation are mismatched.
- Exact Table II numbers may differ from the paper because of those underspecified details and deterministic tie-breaking choices, especially in the Outer baseline inherited from Osawa.
