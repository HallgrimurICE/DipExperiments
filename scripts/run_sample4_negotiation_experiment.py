"""Run sample4 games with negotiators vs heuristic agents."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dip_tom.agents.monte_carlo_agent import MonteCarloAgent
from dip_tom.agents.negotiator_baseline import BaselineNegotiatorAgent
from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.game import active_powers, winning_power
from dip_tom.env.state import GameState
from dip_tom.maps import sample4
from dip_tom.negotiation.protocol import NegotiationProtocol


class NoNegotiationParticipant:
    def propose_deal(self, state, power, target):
        return None

    def accept_deal(self, state, power, proposer, deal):
        return False


def _center_count_winner(state: GameState) -> str:
    owners = {center: None for center in sample4.MAP_DEF.supply_centers}
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
    if not counts:
        return "draw"
    best = max(counts.values())
    leaders = [power for power, count in counts.items() if count == best]
    if len(leaders) != 1:
        return "draw"
    return leaders[0]


def run_series(num_games: int, seed_offset: int, max_turns: int) -> Counter[str]:
    results: Counter[str] = Counter()
    for index in range(num_games):
        state = GameState(
            units={
                power: dict(units) for power, units in sample4.STARTING_UNITS.items()
            }
        )
        negotiators = {
            "A": BaselineNegotiatorAgent(sample4.MAP_DEF, seed=seed_offset + index),
            "B": BaselineNegotiatorAgent(
                sample4.MAP_DEF, seed=seed_offset + index + 50
            ),
        }
        heuristics = {
            "C": MonteCarloAgent(
                seed=seed_offset + index + 100,
                num_joint_samples=0,
            ),
            "D": MonteCarloAgent(
                seed=seed_offset + index + 150,
                num_joint_samples=0,
            ),
        }
        agents = {**negotiators, **heuristics}
        participants = {
            "A": negotiators["A"],
            "B": negotiators["B"],
            "C": NoNegotiationParticipant(),
            "D": NoNegotiationParticipant(),
        }
        protocol = NegotiationProtocol(participants)

        current = state.clone()
        while current.turn < max_turns:
            if winning_power(current, sample4.MAP_DEF) is not None:
                break
            protocol.run_turn(current, powers=sample4.POWERS)
            for power in ("A", "B"):
                agents[power].set_active_deals(protocol.accepted_deals(power))

            orders = {}
            for power in active_powers(current):
                orders.update(agents[power].select_orders(current, sample4.MAP_DEF, power))
            current = adjudicate_orders(current, orders)
            current.turn += 1
            protocol.expire_deals()

        winner = winning_power(current, sample4.MAP_DEF)
        if winner is None:
            winner = _center_count_winner(current)
        results[winner] += 1
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run sample4 games with negotiators vs heuristic agents."
    )
    parser.add_argument("--games", type=int, default=10, help="Number of games to run.")
    parser.add_argument("--seed", type=int, default=400, help="Seed offset.")
    parser.add_argument(
        "--max-turns", type=int, default=120, help="Maximum turns per game."
    )
    args = parser.parse_args()

    results = run_series(args.games, args.seed, args.max_turns)
    print(
        f\"Results for sample4 ({args.games} games, negotiators A/B, heuristic C/D)\"
    )
    for power, count in results.most_common():
        print(f\"  {power}: {count}\")


if __name__ == "__main__":
    main()
