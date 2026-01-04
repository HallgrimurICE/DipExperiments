"""Run sampled games to compare Monte Carlo agent outcomes across maps."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dip_tom.agents.monte_carlo_agent import MonteCarloAgent
from dip_tom.agents.random_agent import RandomAgent
from dip_tom.env.game import run_game, winning_power
from dip_tom.env.state import GameState
from dip_tom.maps import sample4, triangle3


def _run_series(
    map_def,
    starting_units,
    powers: Iterable[str],
    num_games: int,
    seed_offset: int,
) -> Counter:
    results: Counter[str] = Counter()
    for index in range(num_games):
        state = GameState(units={power: dict(units) for power, units in starting_units.items()})
        agents = {
            "A": MonteCarloAgent(seed=seed_offset + index),
        }
        for power in powers:
            if power == "A":
                continue
            agents[power] = RandomAgent(seed=seed_offset + index + ord(power))

        final_state = run_game(state, map_def, agents, max_turns=120)
        winner = winning_power(final_state, map_def)
        if winner is None:
            results["draw"] += 1
        else:
            results[winner] += 1
    return results


def _print_summary(map_name: str, results: Counter, num_games: int) -> None:
    print(f"\nResults for {map_name} ({num_games} games)")
    for power, count in results.most_common():
        print(f"  {power}: {count}")


def main() -> None:
    triangle_results = _run_series(
        triangle3.MAP_DEF,
        triangle3.STARTING_UNITS,
        triangle3.POWERS,
        num_games=20,
        seed_offset=100,
    )
    sample4_results = _run_series(
        sample4.MAP_DEF,
        sample4.STARTING_UNITS,
        sample4.POWERS,
        num_games=20,
        seed_offset=200,
    )
    _print_summary("triangle3", triangle_results, 20)
    _print_summary("sample4", sample4_results, 20)


if __name__ == "__main__":
    main()
