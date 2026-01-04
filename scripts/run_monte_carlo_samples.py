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
            winner = _center_count_winner(final_state, map_def)
        results[winner] += 1
    return results


def _center_count_winner(state: GameState, map_def) -> str:
    counts = _center_counts(state, map_def)
    best_count = max(counts.values()) if counts else 0
    leaders = [power for power, count in counts.items() if count == best_count]
    if len(leaders) != 1:
        return "draw"
    return leaders[0]


def _center_counts(state: GameState, map_def) -> Counter:
    owners = {center: None for center in map_def.supply_centers}
    for center, owner in state.center_owner.items():
        if center in owners and owner is not None:
            owners[center] = owner

    unit_by_node: dict[str, str] = {}
    for owner_power, units in state.units.items():
        for _, location in units.items():
            unit_by_node[location] = owner_power

    for center in owners:
        if owners[center] is None:
            owners[center] = unit_by_node.get(center)

    counts: Counter[str] = Counter()
    for owner in owners.values():
        if owner is not None:
            counts[owner] += 1
    return counts


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
