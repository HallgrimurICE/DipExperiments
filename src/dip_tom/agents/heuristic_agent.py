"""Sampled best-response heuristic agent."""

from __future__ import annotations

import itertools
import random
from collections import OrderedDict
from typing import Dict, List, Sequence, Tuple

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.game import active_powers
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, Order, Support, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class HeuristicAgent:
    """Approximate best-response agent using sampled joint orders."""

    def __init__(
        self,
        *,
        seed: int | None = None,
        rng: random.Random | None = None,
        top_k: int = 3,
        rollout_limit: int = 64,
        rollout_depth: int = 1,
        rollout_discount: float = 0.9,
        base_profile_count: int = 8,
        unit_weight: float = 1.0,
        supply_center_weight: float = 5.0,
        threatened_penalty: float = 2.0,
    ) -> None:
        if seed is not None and rng is not None:
            raise ValueError("Provide either a seed or an rng, not both.")
        self._rng = rng or random.Random(seed)
        self._top_k = max(1, top_k)
        self._rollout_limit = max(1, rollout_limit)
        self._rollout_depth = max(1, rollout_depth)
        self._rollout_discount = max(0.0, min(1.0, rollout_discount))
        self._base_profile_count = max(1, base_profile_count)
        self._unit_weight = unit_weight
        self._supply_center_weight = supply_center_weight
        self._threatened_penalty = threatened_penalty

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        candidate_map = self._build_candidate_order_map(state, map_def, power)
        if not candidate_map:
            return {}
        best_orders, _ = self._select_best_orders(
            state, map_def, power, candidate_map, depth=self._rollout_depth
        )
        unit_order = list(candidate_map.keys())
        return {unit_key: order for unit_key, order in zip(unit_order, best_orders)}

    def _build_candidate_order_map(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> "OrderedDict[UnitKey, List[Order]]":
        orders_by_unit = legal_orders(state, map_def, power)
        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        candidate_map: "OrderedDict[UnitKey, List[Order]]" = OrderedDict()
        for unit_id in sorted(orders_by_unit.keys()):
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
                for order in orders_by_unit[unit_id]
            ]
            scored.sort(key=lambda item: item[0], reverse=True)
            best_orders = [order for _, order in scored[: self._top_k]]
            candidate_map[(power, unit_id)] = best_orders
        return candidate_map

    def _select_best_orders(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        candidate_map: "OrderedDict[UnitKey, List[Order]]",
        *,
        depth: int,
    ) -> Tuple[List[Order], float]:
        combos = self._enumerate_combos(candidate_map)
        if not combos:
            base_score = self._evaluate_state(state, map_def, power)
            return [], base_score

        base_profiles = self._sample_base_profiles(state, map_def, power)
        unit_order = list(candidate_map.keys())

        best_score = float("-inf")
        best_orders: Sequence[Order] | None = None
        for combo in combos:
            score = self._estimate_combo_value(
                state, map_def, power, unit_order, combo, base_profiles, depth
            )
            if score > best_score:
                best_score = score
                best_orders = combo

        if best_orders is None:
            return [], self._evaluate_state(state, map_def, power)
        return list(best_orders), best_score

    def _enumerate_combos(
        self, candidate_map: "OrderedDict[UnitKey, List[Order]]"
    ) -> List[Tuple[Order, ...]]:
        candidate_lists = list(candidate_map.values())
        if not candidate_lists:
            return []

        total = 1
        for options in candidate_lists:
            total *= len(options)
            if total > self._rollout_limit:
                break

        if total <= self._rollout_limit:
            return list(itertools.product(*candidate_lists))

        samples = set()
        baseline = tuple(options[0] for options in candidate_lists)
        samples.add(baseline)
        while len(samples) < self._rollout_limit:
            selection = tuple(self._rng.choice(options) for options in candidate_lists)
            samples.add(selection)
        return list(samples)

    def _sample_base_profiles(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> List[Dict[UnitKey, Order]]:
        opponents = [opponent for opponent in active_powers(state) if opponent != power]
        if not opponents:
            return [{}]

        profiles: List[Dict[UnitKey, Order]] = []
        baseline: Dict[UnitKey, Order] = {}
        for opponent in opponents:
            baseline.update(self._baseline_orders(state, map_def, opponent))
        profiles.append(baseline)

        while len(profiles) < self._base_profile_count:
            orders: Dict[UnitKey, Order] = {}
            for opponent in opponents:
                orders.update(self._sample_opponent_orders(state, map_def, opponent))
            profiles.append(orders)
        return profiles

    def _baseline_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        baseline: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
                baseline[(power, unit_id)] = max(
                    unit_orders,
                    key=lambda order: _order_score(
                        state,
                        map_def,
                        power,
                        unit_id,
                        order,
                        node_values,
                        occupancy,
                    ),
                )
            else:
                baseline[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return baseline

    def _sample_opponent_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
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
                scored.sort(key=lambda item: item[0], reverse=True)
                top_orders = [order for _, order in scored[: self._top_k]]
                selected[(power, unit_id)] = self._rng.choice(top_orders)
            else:
                selected[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected

    def _estimate_combo_value(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        unit_order: Sequence[UnitKey],
        combo: Sequence[Order],
        base_profiles: Sequence[Dict[UnitKey, Order]],
        depth: int,
    ) -> float:
        if not base_profiles:
            return self._resolve_and_score(
                state, map_def, power, unit_order, combo, {}, depth
            )

        total = 0.0
        for profile in base_profiles:
            total += self._resolve_and_score(
                state, map_def, power, unit_order, combo, profile, depth
            )
        return total / float(len(base_profiles))

    def _resolve_and_score(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        unit_order: Sequence[UnitKey],
        combo: Sequence[Order],
        opponent_orders: Dict[UnitKey, Order],
        depth: int,
    ) -> float:
        orders: Dict[UnitKey, Order] = dict(opponent_orders)
        for unit_key, order in zip(unit_order, combo):
            orders[unit_key] = order

        next_state = adjudicate_orders(state, orders)
        next_state.turn += 1
        current_score = self._evaluate_state(next_state, map_def, power)

        if depth <= 1:
            return current_score

        candidate_map = self._build_candidate_order_map(next_state, map_def, power)
        if not candidate_map:
            return current_score

        _, future_score = self._select_best_orders(
            next_state, map_def, power, candidate_map, depth=depth - 1
        )
        return current_score + self._rollout_discount * future_score

    def _evaluate_state(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> float:
        center_counts = _center_counts(state, map_def)
        centers_owned = center_counts.get(power, 0)
        unit_count = len(state.units.get(power, {}))
        threatened = _centers_threatened(state, map_def, power)
        return (
            self._unit_weight * unit_count
            + self._supply_center_weight * centers_owned
            - self._threatened_penalty * threatened
        )


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


def _center_counts(state: GameState, map_def: MapDef) -> Dict[Power, int]:
    owners = _supply_center_owners(state, map_def)
    counts: Dict[Power, int] = {}
    for owner in owners.values():
        if owner is None:
            continue
        counts[owner] = counts.get(owner, 0) + 1
    return counts


def _centers_threatened(state: GameState, map_def: MapDef, power: Power) -> int:
    owners = _supply_center_owners(state, map_def)
    threatened = 0
    for center, owner in owners.items():
        if owner != power:
            continue
        for neighbor in map_def.neighbors(center):
            for enemy_power, units in state.units.items():
                if enemy_power == power:
                    continue
                if neighbor in units.values():
                    threatened += 1
                    break
            else:
                continue
            break
    return threatened
