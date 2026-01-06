"""Baseline negotiator agent that proposes deals based on self value gains."""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Tuple

from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.game import active_powers
from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, Order, Support, legal_orders
from dip_tom.env.state import GameState, Power, UnitId
from dip_tom.negotiation.deal import Deal, NoEnterDeal, PeaceDeal, SupportDeal, UnitRef

UnitKey = Tuple[Power, UnitId]


class BaselineNegotiatorAgent:
    """Propose and accept deals based on Monte Carlo value improvements."""

    def __init__(
        self,
        map_def: MapDef,
        seed: int | None = None,
        rng: random.Random | None = None,
        epsilon: float = 0.1,
        num_deal_samples: int = 4,
        rollout_horizon: int = 4,
        rollout_samples: int = 8,
        opponent_heuristic_prob: float = 0.0,
    ) -> None:
        if seed is not None and rng is not None:
            raise ValueError("Provide either a seed or an rng, not both.")
        self._rng = rng or random.Random(seed)
        self._map_def = map_def
        self._epsilon = epsilon
        self._num_deal_samples = num_deal_samples
        self._rollout_horizon = rollout_horizon
        self._rollout_samples = rollout_samples
        self._opponent_heuristic_prob = opponent_heuristic_prob
        self._active_deals: List[Deal] = []

    def set_active_deals(self, deals: Iterable[Deal]) -> None:
        """Store accepted deals to respect during order selection."""
        self._active_deals = list(deals)

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        """Select orders for the tactical phase while respecting active deals."""
        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        orders_by_unit = legal_orders(state, map_def, power)
        restricted = self._apply_deal_restrictions(power, orders_by_unit, self._active_deals)
        if restricted is None:
            restricted = orders_by_unit
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in restricted.items():
            if unit_orders:
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
            else:
                selected[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected

    def propose_deal(self, state: GameState, power: Power, target: Power) -> Deal | None:
        """Propose a deal if it improves the expected value for the proposer."""
        base_value = self._estimate_value(state, power, None)
        best_deal: Deal | None = None
        best_value = base_value

        for deal in self._candidate_deals(state, power, target):
            value = self._estimate_value(state, power, deal)
            if value > best_value + self._epsilon:
                best_value = value
                best_deal = deal

        return best_deal

    def accept_deal(
        self, state: GameState, power: Power, proposer: Power, deal: Deal
    ) -> bool:
        """Accept a deal if it improves expected value for the responder."""
        base_value = self._estimate_value(state, power, None)
        deal_value = self._estimate_value(state, power, deal)
        return deal_value > base_value

    def _candidate_deals(
        self, state: GameState, power: Power, target: Power
    ) -> List[Deal]:
        deals: List[Deal] = [PeaceDeal.from_state(power, target, state)]
        protected_nodes = set(state.units.get(power, {}).values())
        protected_nodes.update(
            node
            for node, owner in _supply_center_owners(state, self._map_def).items()
            if owner == power
        )
        candidate_nodes = list(protected_nodes)
        if candidate_nodes:
            sample_count = min(self._num_deal_samples, len(candidate_nodes))
            sampled = self._rng.sample(candidate_nodes, sample_count)
            deals.extend(
                NoEnterDeal(i=power, j=target, node=node) for node in sampled
            )
        deals.extend(self._support_deals(state, power, target))
        return deals

    def _support_deals(
        self, state: GameState, power: Power, target: Power
    ) -> List[Deal]:
        support_deals: List[Deal] = []
        orders_by_unit = legal_orders(state, self._map_def, power)
        for supporter_unit_id, orders in orders_by_unit.items():
            for order in orders:
                if not isinstance(order, Support):
                    continue
                if order.supported_power != target:
                    continue
                if order.to_node is None:
                    continue
                support_deals.append(
                    SupportDeal(
                        i=power,
                        j=target,
                        supported_unit=UnitRef(
                            power=order.supported_power,
                            unit_id=order.supported_unit_id,
                        ),
                        from_node=order.from_node,
                        to_node=order.to_node,
                        supporter_unit=UnitRef(power=power, unit_id=supporter_unit_id),
                    )
                )
        if not support_deals:
            return []
        sample_count = min(self._num_deal_samples, len(support_deals))
        return self._rng.sample(support_deals, sample_count)

    def _estimate_value(
        self, state: GameState, power: Power, deal: Deal | None
    ) -> float:
        if deal is not None and not self._deal_has_valid_orders(state, deal):
            return float("-inf")

        total_reward = 0.0
        for _ in range(max(1, self._rollout_samples)):
            rollout_state = state.clone()
            for step in range(max(1, self._rollout_horizon)):
                orders: Dict[UnitKey, Order] = {}
                for current_power in active_powers(rollout_state):
                    current_deals = [deal] if deal is not None and step == 0 else []
                    if current_power == power:
                        orders.update(
                            self._heuristic_orders(
                                rollout_state, self._map_def, current_power, current_deals
                            )
                        )
                    else:
                        if self._rng.random() < self._opponent_heuristic_prob:
                            orders.update(
                                self._heuristic_orders(
                                    rollout_state,
                                    self._map_def,
                                    current_power,
                                    current_deals,
                                )
                            )
                        else:
                            orders.update(
                                self._random_orders(
                                    rollout_state,
                                    self._map_def,
                                    current_power,
                                    current_deals,
                                )
                            )
                rollout_state = adjudicate_orders(rollout_state, orders)
                rollout_state.turn += 1
            total_reward += self._reward(rollout_state, self._map_def, power)

        return total_reward / max(1, self._rollout_samples)

    def _deal_has_valid_orders(self, state: GameState, deal: Deal) -> bool:
        for power in active_powers(state):
            orders_by_unit = legal_orders(state, self._map_def, power)
            restricted = self._apply_deal_restrictions(power, orders_by_unit, [deal])
            if restricted is None:
                return False
        return True

    def _heuristic_orders(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        deals: Iterable[Deal],
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        restricted = self._apply_deal_restrictions(power, orders_by_unit, deals)
        if restricted is None:
            restricted = orders_by_unit
        node_values = _node_values(map_def)
        occupancy = _unit_occupancy(state)
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in restricted.items():
            if unit_orders:
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
            else:
                selected[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected

    def _random_orders(
        self,
        state: GameState,
        map_def: MapDef,
        power: Power,
        deals: Iterable[Deal],
    ) -> Dict[UnitKey, Order]:
        orders_by_unit = legal_orders(state, map_def, power)
        restricted = self._apply_deal_restrictions(power, orders_by_unit, deals)
        if restricted is None:
            restricted = orders_by_unit
        selected: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in restricted.items():
            if unit_orders:
                selected[(power, unit_id)] = self._rng.choice(unit_orders)
            else:
                selected[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected

    def _apply_deal_restrictions(
        self,
        power: Power,
        orders_by_unit: Dict[UnitId, List[Order]],
        deals: Iterable[Deal],
    ) -> Dict[UnitId, List[Order]] | None:
        restricted = orders_by_unit
        for deal in deals:
            restricted = deal.allowed_orders(power, restricted)
        if any(not orders for orders in restricted.values()):
            return None
        return restricted

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

    def _reward(self, state: GameState, map_def: MapDef, power: Power) -> float:
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
