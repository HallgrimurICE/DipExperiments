"""Sampled best-response heuristic agent."""

from __future__ import annotations

import itertools
import random
from collections import OrderedDict
from typing import Dict, Iterable, List, Sequence, Tuple

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.game import active_powers
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Order, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class HeuristicAgent:
    """Approximate best-response agent using sampled joint orders."""

    def __init__(
        self,
        *,
        seed: int | None = None,
        rng: random.Random | None = None,
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
        candidate_map: "OrderedDict[UnitKey, List[Order]]" = OrderedDict()
        for unit_id in sorted(orders_by_unit.keys()):
            candidate_map[(power, unit_id)] = list(orders_by_unit[unit_id])
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
        baseline: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
                baseline[(power, unit_id)] = unit_orders[0]
            else:
                baseline[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return baseline

    def _sample_opponent_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
                selected[(power, unit_id)] = self._rng.choice(unit_orders)
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
