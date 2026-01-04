"""Order adjudication for simplified Diplomacy-like moves."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .orders import Hold, Move, Order, Support
from .state import GameState, Node, Power, UnitId

UnitKey = Tuple[Power, UnitId]


def adjudicate_orders(
    state: GameState, orders: Dict[UnitKey, Order]
) -> GameState:
    """Resolve orders and return the next state.

    Simplifications:
    - Supports add strength for matching move or hold orders.
    - Support cutting and support-hold are ignored.
    - Dislodged units are removed from the board.
    """

    normalized_orders = _normalize_orders(state, orders)
    move_orders = {
        unit_key: order
        for unit_key, order in normalized_orders.items()
        if isinstance(order, Move)
    }

    move_strengths = _compute_move_strengths(state, normalized_orders, move_orders)
    hold_strengths = _compute_hold_strengths(state, normalized_orders)
    candidate_moves = _determine_candidate_moves(move_orders, move_strengths)
    successful_moves = _resolve_move_success(
        state,
        normalized_orders,
        move_orders,
        move_strengths,
        hold_strengths,
        candidate_moves,
    )

    return _apply_moves(state, move_orders, successful_moves)


def _normalize_orders(
    state: GameState, orders: Dict[UnitKey, Order]
) -> Dict[UnitKey, Order]:
    normalized: Dict[UnitKey, Order] = {}
    for power, unit_id in state.all_units():
        normalized[(power, unit_id)] = orders.get(
            (power, unit_id), Hold(power=power, unit_id=unit_id)
        )
    return normalized


def _compute_move_strengths(
    state: GameState,
    orders: Dict[UnitKey, Order],
    move_orders: Dict[UnitKey, Move],
) -> Dict[UnitKey, int]:
    support_counts: Dict[UnitKey, int] = {unit_key: 0 for unit_key in move_orders}
    for order in orders.values():
        if not isinstance(order, Support):
            continue
        if order.to_node is None:
            continue
        supported_key = (order.supported_power, order.supported_unit_id)
        supported_order = move_orders.get(supported_key)
        if supported_order is None:
            continue
        supported_location = state.units.get(order.supported_power, {}).get(
            order.supported_unit_id
        )
        if supported_location != order.from_node:
            continue
        if supported_order.to_node != order.to_node:
            continue
        support_counts[supported_key] += 1

    return {
        unit_key: 1 + support_counts.get(unit_key, 0) for unit_key in move_orders
    }


def _compute_hold_strengths(
    state: GameState, orders: Dict[UnitKey, Order]
) -> Dict[UnitKey, int]:
    hold_support_counts: Dict[UnitKey, int] = {}
    for order in orders.values():
        if not isinstance(order, Support):
            continue
        if order.to_node is not None:
            continue
        supported_key = (order.supported_power, order.supported_unit_id)
        supported_order = orders.get(supported_key)
        if not isinstance(supported_order, Hold):
            continue
        supported_location = state.units.get(order.supported_power, {}).get(
            order.supported_unit_id
        )
        if supported_location != order.from_node:
            continue
        hold_support_counts[supported_key] = hold_support_counts.get(supported_key, 0) + 1

    return {
        unit_key: 1 + support_count
        for unit_key, support_count in hold_support_counts.items()
    }


def _determine_candidate_moves(
    move_orders: Dict[UnitKey, Move], move_strengths: Dict[UnitKey, int]
) -> set[UnitKey]:
    moves_by_target: Dict[Node, list[UnitKey]] = defaultdict(list)
    for unit_key, order in move_orders.items():
        moves_by_target[order.to_node].append(unit_key)

    candidates: set[UnitKey] = set()
    for unit_keys in moves_by_target.values():
        max_strength = max(move_strengths[unit_key] for unit_key in unit_keys)
        strongest = [
            unit_key
            for unit_key in unit_keys
            if move_strengths[unit_key] == max_strength
        ]
        if len(strongest) == 1:
            candidates.add(strongest[0])
    return candidates


def _resolve_move_success(
    state: GameState,
    orders: Dict[UnitKey, Order],
    move_orders: Dict[UnitKey, Move],
    move_strengths: Dict[UnitKey, int],
    hold_strengths: Dict[UnitKey, int],
    candidate_moves: Iterable[UnitKey],
) -> set[UnitKey]:
    successful_moves = set(candidate_moves)
    while True:
        removals: set[UnitKey] = set()
        for unit_key in successful_moves:
            target = move_orders[unit_key].to_node
            defender_key = _unit_at_node(state, target)
            if defender_key is None or defender_key == unit_key:
                continue
            defender_order = orders.get(defender_key)
            defender_is_moving = isinstance(defender_order, Move)
            defender_success = defender_key in successful_moves
            if defender_is_moving and defender_success:
                continue
            defender_strength = 1
            if isinstance(defender_order, Hold):
                defender_strength = hold_strengths.get(defender_key, 1)
            if move_strengths[unit_key] <= defender_strength:
                removals.add(unit_key)
        if not removals:
            break
        successful_moves.difference_update(removals)
    return successful_moves


def _apply_moves(
    state: GameState,
    move_orders: Dict[UnitKey, Move],
    successful_moves: set[UnitKey],
) -> GameState:
    new_state = state.clone()
    new_units = {power: dict(units) for power, units in state.units.items()}

    dislodged: set[UnitKey] = set()
    for unit_key in successful_moves:
        target = move_orders[unit_key].to_node
        defender_key = _unit_at_node(state, target)
        if defender_key and defender_key not in successful_moves:
            dislodged.add(defender_key)

    for power, unit_id in dislodged:
        if power in new_units and unit_id in new_units[power]:
            del new_units[power][unit_id]

    for power, unit_id in successful_moves:
        if power in new_units and unit_id in new_units[power]:
            new_units[power][unit_id] = move_orders[(power, unit_id)].to_node

    new_state.units = new_units
    return new_state


def _unit_at_node(state: GameState, node: Node) -> UnitKey | None:
    for power, units in state.units.items():
        for unit_id, location in units.items():
            if location == node:
                return power, unit_id
    return None
