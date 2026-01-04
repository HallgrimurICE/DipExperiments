"""Heuristic agent that scores and selects orders greedily per unit."""

from __future__ import annotations

from typing import Dict, Tuple

from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, Order, Support, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class HeuristicAgent:
    """Pick the highest scoring legal order for every unit a power controls."""

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        """Return one greedy legal order per unit for the given power."""
        orders_by_unit = legal_orders(state, map_def, power)
        selected_orders: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
                best_order = max(
                    unit_orders,
                    key=lambda order: self._score_order(order, state, map_def, power),
                )
                selected_orders[(power, unit_id)] = best_order
            else:
                selected_orders[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected_orders

    def _score_order(
        self, order: Order, state: GameState, map_def: MapDef, power: Power
    ) -> int:
        if isinstance(order, Move):
            return self._score_move(order, state, map_def, power)
        if isinstance(order, Support):
            return self._score_support(order, state, map_def)
        return 0

    @staticmethod
    def _score_move(order: Move, state: GameState, map_def: MapDef, power: Power) -> int:
        if order.to_node not in map_def.supply_centers:
            return 0
        occupant = _unit_owner_at(state, order.to_node)
        if occupant == power:
            return 0
        owner = _center_owner(state, map_def, order.to_node)
        if owner is None:
            return 3
        if owner != power:
            return 2
        return 1

    @staticmethod
    def _score_support(order: Support, state: GameState, map_def: MapDef) -> int:
        if order.to_node is None or order.to_node not in map_def.supply_centers:
            return 0
        owner = _center_owner(state, map_def, order.to_node)
        if owner == order.supported_power:
            return 0
        if _unit_owner_at(state, order.to_node) == order.supported_power:
            return 0
        return 2


def _center_owner(state: GameState, map_def: MapDef, center: str) -> Power | None:
    owner = state.center_owner.get(center)
    if owner is not None:
        return owner
    if center not in map_def.supply_centers:
        return None
    return _unit_owner_at(state, center)


def _unit_owner_at(state: GameState, node: str) -> Power | None:
    for power, units in state.units.items():
        for _, location in units.items():
            if location == node:
                return power
    return None
