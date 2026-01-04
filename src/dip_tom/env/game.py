"""Game loop helpers for simplified Diplomacy experiments."""

from __future__ import annotations

from typing import Dict, Mapping

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Order
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = tuple[Power, UnitId]


def active_powers(state: GameState) -> list[Power]:
    """Return a list of powers that still have units."""
    return [power for power, units in state.units.items() if units]


def _supply_center_owners(state: GameState, map_def: MapDef) -> dict[str, Power | None]:
    owners: dict[str, Power | None] = {center: None for center in map_def.supply_centers}
    for center, owner in state.center_owner.items():
        if center in owners and owner is not None:
            owners[center] = owner

    unit_by_node: dict[str, Power] = {}
    for power, units in state.units.items():
        for _, location in units.items():
            unit_by_node[location] = power

    for center in owners:
        if owners[center] is None:
            owners[center] = unit_by_node.get(center)

    return owners


def winning_power(state: GameState, map_def: MapDef) -> Power | None:
    """Return the power that controls a majority of supply centers, if any."""
    total_centers = len(map_def.supply_centers)
    if total_centers == 0:
        return None
    threshold = total_centers / 2
    counts: dict[Power, int] = {}
    for owner in _supply_center_owners(state, map_def).values():
        if owner is None:
            continue
        counts[owner] = counts.get(owner, 0) + 1
    for power, count in counts.items():
        if count > threshold:
            return power
    return None


def is_game_over(state: GameState, map_def: MapDef) -> bool:
    """Return True when a power controls more than half of supply centers."""
    return winning_power(state, map_def) is not None


def run_game(
    state: GameState,
    map_def: MapDef,
    agents: Mapping[Power, "OrderAgent"],
    max_turns: int = 100,
) -> GameState:
    """Run the game until completion or max_turns and return the final state."""
    current = state.clone()
    while current.turn < max_turns and not is_game_over(current, map_def):
        orders: Dict[UnitKey, Order] = {}
        for power in active_powers(current):
            agent = agents[power]
            orders.update(agent.select_orders(current, map_def, power))
        current = adjudicate_orders(current, orders)
        current.turn += 1
    return current


class OrderAgent:
    """Protocol for order-selecting agents."""

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        raise NotImplementedError
