"""Simple heuristic agent that prefers higher-value moves."""

from __future__ import annotations

import random
from typing import Dict, Tuple

from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, Order, Support, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class HeuristicAgent:
    """Pick the highest-scoring legal order for each unit."""

    def __init__(self, seed: int | None = None, rng: random.Random | None = None) -> None:
        if seed is not None and rng is not None:
            raise ValueError("Provide either a seed or an rng, not both.")
        self._rng = rng or random.Random(seed)

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        if not orders_by_unit:
            return {}

        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            scored = [
                (
                    _order_score(
                        state,
                        map_def,
                        power,
                        unit_id,
                        order,
                        node_values,
                        occupancy,
                    ),
                    order,
                )
                for order in unit_orders
            ]
            max_score = max(score for score, _ in scored)
            best_orders = [order for score, order in scored if score == max_score]
            selected[(power, unit_id)] = self._rng.choice(best_orders)
        return selected


def _node_values(map_def: MapDef) -> Dict[str, float]:
    degrees = {node: 0 for node in map_def.nodes}
    for left, right in map_def.edges:
        degrees[left] = degrees.get(left, 0) + 1
        degrees[right] = degrees.get(right, 0) + 1
    supply_centers = set(map_def.supply_centers)
    return {
        node: degrees.get(node, 0) + (2.0 if node in supply_centers else 0.0)
        for node in map_def.nodes
    }


def _unit_occupancy(state: GameState) -> Dict[str, Power]:
    occupancy: Dict[str, Power] = {}
    for power, units in state.units.items():
        for location in units.values():
            occupancy[location] = power
    return occupancy


def _supply_center_owners(state: GameState, map_def: MapDef) -> Dict[str, Power | None]:
    owners: Dict[str, Power | None] = {center: None for center in map_def.supply_centers}
    for center, owner in state.center_owner.items():
        if center in owners and owner is not None:
            owners[center] = owner

    unit_by_node: Dict[str, Power] = {}
    for owner_power, units in state.units.items():
        for _, location in units.items():
            unit_by_node[location] = owner_power

    for center in owners:
        if owners[center] is None:
            owners[center] = unit_by_node.get(center)
    return owners


def _order_score(
    state: GameState,
    map_def: MapDef,
    power: Power,
    unit_id: UnitId,
    order: Order,
    node_values: Dict[str, float],
    occupancy: Dict[str, Power],
) -> float:
    center_owners = _supply_center_owners(state, map_def)
    if isinstance(order, Move):
        base = node_values.get(order.to_node, 0.0)
        occupant = occupancy.get(order.to_node)
        if occupant is None:
            base += 0.4
        elif occupant == power:
            base -= 1.2
        else:
            base += 0.8
        if order.to_node in center_owners:
            owner = center_owners.get(order.to_node)
            if owner is None:
                base += 1.2
            elif owner != power:
                base += 1.5
        return base + 0.1

    if isinstance(order, Hold):
        location = state.unit_position(power, unit_id)
        return node_values.get(location, 0.0) * 0.35

    if isinstance(order, Support):
        target = order.to_node or order.from_node
        base = node_values.get(target, 0.0) * 0.2
        if order.supported_power == power:
            base += 0.3
        else:
            base -= 0.2
        return base

    return 0.0
