"""Monte Carlo agent that samples joint orders and evaluates rollouts."""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Tuple

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.game import active_powers
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, Order, Support, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class MonteCarloAgent:
    """Sample joint orders and evaluate them with short rollouts."""

    def __init__(
        self,
        seed: int | None = None,
        rng: random.Random | None = None,
        top_k: int = 3,
        num_joint_samples: int = 30,
        rollout_horizon: int = 4,
        rollout_samples: int = 3,
        opponent_heuristic_prob: float = 0.0,
    ) -> None:
        if seed is not None and rng is not None:
            raise ValueError("Provide either a seed or an rng, not both.")
        self._rng = rng or random.Random(seed)
        self._top_k = top_k
        self._num_joint_samples = num_joint_samples
        self._rollout_horizon = rollout_horizon
        self._rollout_samples = rollout_samples
        self._opponent_heuristic_prob = opponent_heuristic_prob

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        """Return the best sampled joint order for the given power."""
        orders_by_unit = legal_orders(state, map_def, power)
        if not orders_by_unit:
            return {}

        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        top_orders = {
            unit_id: self._top_orders_for_unit(
                state,
                map_def,
                power,
                unit_id,
                unit_orders,
                node_values,
                occupancy,
            )
            for unit_id, unit_orders in orders_by_unit.items()
        }

        candidate_orders = self._sample_joint_orders(power, top_orders)
        if not candidate_orders:
            return self._heuristic_orders(state, map_def, power, node_values)

        best_score = float("-inf")
        best_orders: Dict[UnitKey, Order] | None = None
        for candidate in candidate_orders:
            score = self._evaluate_joint_orders(
                state,
                map_def,
                power,
                candidate,
                node_values,
            )
            if score > best_score:
                best_score = score
                best_orders = candidate

        return best_orders or self._heuristic_orders(state, map_def, power, node_values)

    def _top_orders_for_unit(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        unit_id: UnitId,
        unit_orders: Iterable[Order],
        node_values: Dict[str, float],
        occupancy: Dict[str, Power],
    ) -> List[Order]:
        scored_orders = [
            (
                self._order_score(
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
        scored_orders.sort(key=lambda item: item[0], reverse=True)
        return [order for _, order in scored_orders[: max(1, self._top_k)]]

    def _order_score(
        self,
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

    def _sample_joint_orders(
        self, power: Power, top_orders: Dict[UnitId, List[Order]]
    ) -> List[Dict[UnitKey, Order]]:
        unit_ids = list(top_orders.keys())
        if not unit_ids:
            return []

        samples: List[Dict[UnitKey, Order]] = []
        seen: set[Tuple[Order, ...]] = set()
        max_attempts = self._num_joint_samples * 3
        attempts = 0
        while len(samples) < self._num_joint_samples and attempts < max_attempts:
            attempts += 1
            orders: Dict[UnitKey, Order] = {}
            signature: List[Order] = []
            for unit_id in unit_ids:
                choice = self._rng.choice(top_orders[unit_id])
                orders[(power, unit_id)] = choice
                signature.append(choice)
            sig_tuple = tuple(signature)
            if sig_tuple in seen:
                continue
            seen.add(sig_tuple)
            samples.append(orders)

        if not samples:
            fallback = {
                (power, unit_id): self._rng.choice(unit_orders)
                for unit_id, unit_orders in top_orders.items()
            }
            samples.append(fallback)
        return samples

    def _evaluate_joint_orders(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        candidate: Dict[UnitKey, Order],
        node_values: Dict[str, float],
    ) -> float:
        total_reward = 0.0
        for _ in range(max(1, self._rollout_samples)):
            rollout_state = state.clone()
            for step in range(max(1, self._rollout_horizon)):
                orders: Dict[UnitKey, Order] = {}
                for current_power in active_powers(rollout_state):
                    if current_power == power:
                        if step == 0:
                            orders.update(candidate)
                        else:
                            orders.update(
                                self._heuristic_orders(
                                    rollout_state, map_def, current_power, node_values
                                )
                            )
                    else:
                        if self._rng.random() < self._opponent_heuristic_prob:
                            orders.update(
                                self._heuristic_orders(
                                    rollout_state, map_def, current_power, node_values
                                )
                            )
                        else:
                            orders.update(
                                self._random_orders(rollout_state, map_def, current_power)
                            )
                rollout_state = adjudicate_orders(rollout_state, orders)
                rollout_state.turn += 1
            total_reward += self._reward(rollout_state, map_def, power)
        return total_reward / max(1, self._rollout_samples)

    def _heuristic_orders(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        node_values: Dict[str, float],
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        occupancy = _unit_occupancy(state)
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            best_order = max(
                unit_orders,
                key=lambda order: self._order_score(
                    state,
                    map_def,
                    power,
                    unit_id,
                    order,
                    node_values,
                    occupancy,
                ),
            )
            selected[(power, unit_id)] = best_order
        return selected

    def _random_orders(
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

    def _reward(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
    ) -> float:
        center_counts = _center_counts(state, map_def)
        centers_owned = center_counts.get(power, 0)
        unit_locations = list(state.units.get(power, {}).values())
        unit_count = len(unit_locations)
        threatened = _centers_threatened(state, map_def, power)
        return unit_count + centers_owned * 5.0 - threatened * 2.0


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
