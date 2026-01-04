"""Game loop helpers for simplified Diplomacy experiments."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Order
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = tuple[Power, UnitId]


def active_powers(state: GameState) -> list[Power]:
    """Return a list of powers that still have units."""
    return [power for power, units in state.units.items() if units]


def is_game_over(state: GameState) -> bool:
    """Return True when only one (or zero) powers still have units."""
    return len(active_powers(state)) <= 1


def run_game(
    state: GameState,
    map_def: MapDef,
    agents: Mapping[Power, "OrderAgent"],
    max_turns: int = 100,
) -> GameState:
    """Run the game until completion or max_turns and return the final state."""
    current = state.clone()
    while current.turn < max_turns and not is_game_over(current):
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
