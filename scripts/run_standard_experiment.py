"""Run standard Diplomacy experiments with random vs heuristic agents."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dip_tom.agents.heuristic_agent import HeuristicAgent
from dip_tom.agents.random_agent import RandomAgent
from dip_tom.env.game import run_game, winning_power
from dip_tom.env.state import GameState
from dip_tom.maps import standard


def _initial_state() -> GameState:
    center_owner = {
        center: power
        for power, centers in standard.MAP_DEF.home_centers.items()
        for center in centers
    }
    return GameState(units=deepcopy(standard.STARTING_UNITS), center_owner=center_owner)


def _build_agents(seed: int) -> dict[str, object]:
    random_powers = {"England", "Russia", "Turkey"}
    agents: dict[str, object] = {}
    for power in standard.POWERS:
        if power in random_powers:
            agents[power] = RandomAgent(seed=seed + hash(power) % 1000)
        else:
            agents[power] = HeuristicAgent(seed=seed + hash(power) % 1000)
    return agents


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run random vs heuristic agents on the standard Diplomacy map."
    )
    parser.add_argument("--games", type=int, default=5, help="Number of games to run")
    parser.add_argument("--turns", type=int, default=100, help="Max turns per game")
    parser.add_argument("--seed", type=int, default=1, help="Base RNG seed")
    args = parser.parse_args()

    winner_counts: Counter[str] = Counter()
    for idx in range(args.games):
        state = _initial_state()
        agents = _build_agents(args.seed + idx * 10)
        final_state = run_game(state, standard.MAP_DEF, agents, max_turns=args.turns)
        winner = winning_power(final_state, standard.MAP_DEF)
        winner_counts[winner or "none"] += 1
        print(
            f"Game {idx + 1}: turns={final_state.turn}, "
            f"winner={winner or 'none'}"
        )

    print("\nSummary:")
    for power, count in winner_counts.items():
        print(f"  {power}: {count}")


if __name__ == "__main__":
    main()
