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


def _center_owners(state: GameState) -> dict[str, str | None]:
    supply_centers = set(standard.MAP_DEF.supply_centers)
    owners: dict[str, str | None] = {center: None for center in supply_centers}
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

    return owners


def _final_score(state: GameState, power: str) -> float:
    supply_centers = set(standard.MAP_DEF.supply_centers)
    owners = _center_owners(state)

    centers_owned = sum(1 for owner in owners.values() if owner == power)
    unit_count = len(state.units.get(power, {}))
    threatened = 0
    for center, owner in owners.items():
        if owner != power:
            continue
        for neighbor in standard.MAP_DEF.neighbors(center):
            for enemy_power, units in state.units.items():
                if enemy_power == power:
                    continue
                if neighbor in units.values():
                    threatened += 1
                    break
            else:
                continue
            break

    return unit_count + centers_owned * 5.0 - threatened * 2.0


def _final_scores(state: GameState) -> dict[str, float]:
    owners = _center_owners(state)
    scores: dict[str, float] = {}
    for power in standard.POWERS:
        centers_owned = sum(1 for owner in owners.values() if owner == power)
        unit_count = len(state.units.get(power, {}))
        threatened = 0
        for center, owner in owners.items():
            if owner != power:
                continue
            for neighbor in standard.MAP_DEF.neighbors(center):
                for enemy_power, units in state.units.items():
                    if enemy_power == power:
                        continue
                    if neighbor in units.values():
                        threatened += 1
                        break
                else:
                    continue
                break
        scores[power] = unit_count + centers_owned * 5.0 - threatened * 2.0
    return scores


def _build_agents(seed: int) -> dict[str, object]:
    random_powers = {"England", "Russia", "Turkey"}
    agents: dict[str, object] = {}
    for power in standard.POWERS:
        if power in random_powers:
            agents[power] = RandomAgent(seed=seed + hash(power) % 1000)
            print(f"Assigned RandomAgent to {power}.")
        else:
            agents[power] = HeuristicAgent(seed=seed + hash(power) % 1000)
            print(f"Assigned HeuristicAgent to {power}.")
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
        print(f"\nStarting game {idx + 1}/{args.games}...")
        state = _initial_state()
        total_units = sum(len(units) for units in state.units.values())
        print(
            f"Initial units: {', '.join(sorted(state.units.keys()))} "
            f"({total_units} total)"
        )
        agents = _build_agents(args.seed + idx * 10)
        print("Running game simulation...")
        final_state = run_game(state, standard.MAP_DEF, agents, max_turns=args.turns)
        winner = winning_power(final_state, standard.MAP_DEF)
        winner_counts[winner or "none"] += 1
        scores = _final_scores(final_state)
        winner_score = _final_score(final_state, winner) if winner is not None else None
        print(
            f"Game {idx + 1}: turns={final_state.turn}, "
            f"winner={winner or 'none'}, "
            f"final_score={winner_score if winner_score is not None else 'n/a'}"
        )
        print("Final scores:")
        for power in standard.POWERS:
            print(f"  {power}: {scores[power]:.1f}")

    print("\nSummary:")
    for power, count in winner_counts.items():
        print(f"  {power}: {count}")


if __name__ == "__main__":
    main()
