"""Game state representations for DIP experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


Power = str
UnitId = str
Node = str


@dataclass
class GameState:
    """Serializable game state with unit locations and center ownership."""

    units: Dict[Power, Dict[UnitId, Node]] = field(default_factory=dict)
    center_owner: Dict[Node, Optional[Power]] = field(default_factory=dict)
    turn: int = 0

    def all_units(self) -> List[Tuple[Power, UnitId]]:
        """Return all (power, unit_id) pairs present in the state."""
        return [
            (power, unit_id)
            for power, units in self.units.items()
            for unit_id in units
        ]

    def unit_position(self, power: Power, unit_id: UnitId) -> Node:
        """Return the node where the specified unit is currently located."""
        return self.units[power][unit_id]

    def clone(self) -> GameState:
        """Return a deep copy of the game state."""
        return GameState(
            units={power: dict(units) for power, units in self.units.items()},
            center_owner=dict(self.center_owner),
            turn=self.turn,
        )
