"""Order types and legal order generation for DIP experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .map import MapDef
from .state import GameState, Node, Power, UnitId


@dataclass(frozen=True)
class Hold:
    power: Power
    unit_id: UnitId


@dataclass(frozen=True)
class Move:
    power: Power
    unit_id: UnitId
    to_node: Node


@dataclass(frozen=True)
class Support:
    power: Power
    unit_id: UnitId
    supported_power: Power
    supported_unit_id: UnitId
    from_node: Node
    to_node: Node | None = None


Order = Hold | Move | Support


def legal_orders(state: GameState, map_def: MapDef, power: Power) -> Dict[UnitId, List[Order]]:
    orders: Dict[UnitId, List[Order]] = {}
    if power not in state.units:
        return orders

    neighbors = {node: map_def.neighbors(node) for node in map_def.nodes}

    for unit_id, location in state.units[power].items():
        unit_orders: List[Order] = [Hold(power, unit_id)]
        for to_node in neighbors.get(location, []):
            unit_orders.append(Move(power, unit_id, to_node))

        supporter_neighbors = set(neighbors.get(location, []))
        for supported_power, units in state.units.items():
            for supported_unit_id, from_node in units.items():
                if supported_power == power and supported_unit_id == unit_id:
                    continue
                if from_node in supporter_neighbors:
                    unit_orders.append(
                        Support(
                            power=power,
                            unit_id=unit_id,
                            supported_power=supported_power,
                            supported_unit_id=supported_unit_id,
                            from_node=from_node,
                        )
                    )
                for to_node in neighbors.get(from_node, []):
                    if to_node in supporter_neighbors:
                        unit_orders.append(
                            Support(
                                power=power,
                                unit_id=unit_id,
                                supported_power=supported_power,
                                supported_unit_id=supported_unit_id,
                                from_node=from_node,
                                to_node=to_node,
                            )
                        )

        orders[unit_id] = unit_orders

    return orders
