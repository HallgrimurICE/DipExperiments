"""Random agent that selects a legal order for each unit."""

from __future__ import annotations

import random
from typing import Dict, Tuple

from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Order, legal_orders
from dip_tom.env.state import GameState, Power, UnitId

UnitKey = Tuple[Power, UnitId]


class RandomAgent:
    """Pick a random legal order for every unit a power controls."""

    def __init__(self, seed: int | None = None, rng: random.Random | None = None) -> None:
        if seed is not None and rng is not None:
            raise ValueError("Provide either a seed or an rng, not both.")
        self._rng = rng or random.Random(seed)

    def select_orders(
        self, state: GameState, map_def: MapDef, power: Power
    ) -> Dict[UnitKey, Order]:
        """Return one random legal order per unit for the given power."""
        orders_by_unit = legal_orders(state, map_def, power)
        selected_orders: Dict[UnitKey, Order] = {}
        for unit_id, unit_orders in orders_by_unit.items():
            if unit_orders:
                selected_orders[(power, unit_id)] = self._rng.choice(unit_orders)
            else:
                selected_orders[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
        return selected_orders
