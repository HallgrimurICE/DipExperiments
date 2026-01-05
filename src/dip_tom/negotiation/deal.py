"""Deal types and enforcement for one-turn negotiation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from dip_tom.env.orders import Move, Order, Support
from dip_tom.env.state import GameState, Node, Power, UnitId


OrdersByUnit = Dict[UnitId, Order]
LegalOrders = Dict[UnitId, List[Order]]


@dataclass(frozen=True)
class Violation:
    """Represents a deal violation by a power."""

    power: Power
    deal: "Deal"
    unit_id: Optional[UnitId]
    order: Optional[Order]
    reason: str


@dataclass(frozen=True)
class UnitRef:
    """Reference to a unit by power and unit id."""

    power: Power
    unit_id: UnitId


class Deal:
    """Base class for one-turn deals."""

    def allowed_orders(self, power: Power, legal_orders: LegalOrders) -> LegalOrders:
        return legal_orders

    def violations(self, power: Power, submitted_orders: OrdersByUnit, state: GameState) -> List[Violation]:
        return []


@dataclass
class PeaceDeal(Deal):
    """Mutual promise not to enter each other's current provinces."""

    i: Power
    j: Power
    current_positions: Optional[Dict[Power, List[Node]]] = None

    @classmethod
    def from_state(cls, i: Power, j: Power, state: GameState) -> "PeaceDeal":
        positions = {
            i: list(state.units.get(i, {}).values()),
            j: list(state.units.get(j, {}).values()),
        }
        return cls(i=i, j=j, current_positions=positions)

    def allowed_orders(self, power: Power, legal_orders: LegalOrders) -> LegalOrders:
        if power not in (self.i, self.j):
            return legal_orders
        if not self.current_positions:
            return legal_orders
        opponent = self.j if power == self.i else self.i
        prohibited_nodes = set(self.current_positions.get(opponent, []))
        if not prohibited_nodes:
            return legal_orders

        restricted: LegalOrders = {}
        for unit_id, orders in legal_orders.items():
            restricted[unit_id] = [
                order
                for order in orders
                if not (isinstance(order, Move) and order.to_node in prohibited_nodes)
            ]
        return restricted

    def violations(self, power: Power, submitted_orders: OrdersByUnit, state: GameState) -> List[Violation]:
        if power not in (self.i, self.j):
            return []
        opponent = self.j if power == self.i else self.i
        opponent_nodes = set(state.units.get(opponent, {}).values())
        violations: List[Violation] = []
        for unit_id, order in submitted_orders.items():
            if isinstance(order, Move) and order.to_node in opponent_nodes:
                violations.append(
                    Violation(
                        power=power,
                        deal=self,
                        unit_id=unit_id,
                        order=order,
                        reason=(
                            f"PeaceDeal prohibits entering {opponent}'s current provinces"
                        ),
                    )
                )
        return violations


@dataclass(frozen=True)
class SupportDeal(Deal):
    """Promise to support a specific move for another unit."""

    i: Power
    j: Power
    supported_unit: UnitRef
    from_node: Node
    to_node: Node
    supporter_unit: UnitRef

    def allowed_orders(self, power: Power, legal_orders: LegalOrders) -> LegalOrders:
        if power != self.supporter_unit.power:
            return legal_orders

        restricted: LegalOrders = {}
        for unit_id, orders in legal_orders.items():
            if unit_id != self.supporter_unit.unit_id:
                restricted[unit_id] = orders
                continue
            restricted[unit_id] = [
                order
                for order in orders
                if self._is_required_support(order)
            ]
        return restricted

    def violations(self, power: Power, submitted_orders: OrdersByUnit, state: GameState) -> List[Violation]:
        if power != self.supporter_unit.power:
            return []
        if self.supporter_unit.unit_id not in state.units.get(power, {}):
            return []

        order = submitted_orders.get(self.supporter_unit.unit_id)
        if order is not None and self._is_required_support(order):
            return []
        return [
            Violation(
                power=power,
                deal=self,
                unit_id=self.supporter_unit.unit_id,
                order=order,
                reason="SupportDeal requires a support-move order",
            )
        ]

    def _is_required_support(self, order: Order) -> bool:
        return (
            isinstance(order, Support)
            and order.supported_power == self.supported_unit.power
            and order.supported_unit_id == self.supported_unit.unit_id
            and order.from_node == self.from_node
            and order.to_node == self.to_node
        )


@dataclass(frozen=True)
class NoEnterDeal(Deal):
    """Promise not to enter a specific node this turn."""

    i: Power
    j: Power
    node: Node

    def allowed_orders(self, power: Power, legal_orders: LegalOrders) -> LegalOrders:
        if power not in (self.i, self.j):
            return legal_orders
        restricted: LegalOrders = {}
        for unit_id, orders in legal_orders.items():
            restricted[unit_id] = [
                order
                for order in orders
                if not (isinstance(order, Move) and order.to_node == self.node)
            ]
        return restricted

    def violations(self, power: Power, submitted_orders: OrdersByUnit, state: GameState) -> List[Violation]:
        if power not in (self.i, self.j):
            return []
        violations: List[Violation] = []
        for unit_id, order in submitted_orders.items():
            if isinstance(order, Move) and order.to_node == self.node:
                violations.append(
                    Violation(
                        power=power,
                        deal=self,
                        unit_id=unit_id,
                        order=order,
                        reason=f"NoEnterDeal prohibits entering {self.node}",
                    )
                )
        return violations
