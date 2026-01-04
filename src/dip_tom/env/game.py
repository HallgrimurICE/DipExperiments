"""Game loop and win conditions for DIP experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from dip_tom.utils.rng import make_rng

from .adjudicator import adjudicate_orders
from .map import MapDef, validate_map
from .orders import Hold, Move, Order, Support, legal_orders
from .state import GameState, Node, Power


@dataclass
class GameResult:
    winner: Optional[Power]
    draw: bool
    centers: Dict[Power, int]
    turn: int
    reason: str


def initialize_state(map_def: MapDef) -> GameState:
    """Create an initial state based on map home centers."""
    units: Dict[Power, Dict[str, Node]] = {}
    center_owner: Dict[Node, Optional[Power]] = {center: None for center in map_def.supply_centers}
    for power, home_center in map_def.home_centers.items():
        units[power] = {f"{power}_A": home_center}
        if home_center in center_owner:
            center_owner[home_center] = power
    return GameState(units=units, center_owner=center_owner, turn=0)


@dataclass
class Game:
    map_def: MapDef
    state: GameState
    target_centers: int
    max_turns: int
    seed: int = 0
    eliminated: set[Power] = field(default_factory=set)

    def __post_init__(self) -> None:
        validate_map(self.map_def)
        self.rng = make_rng(self.seed)

    def run(self) -> GameResult:
        while True:
            winner = self._check_target_centers()
            if winner is not None:
                centers = self._center_counts()
                return GameResult(
                    winner=winner,
                    draw=False,
                    centers=centers,
                    turn=self.state.turn,
                    reason="target_centers",
                )

            if self.state.turn >= self.max_turns:
                return self._resolve_max_turns()

            orders = self._select_orders()
            self.state = self.step(orders)

    def step(self, orders: Dict[tuple[Power, str], Order]) -> GameState:
        next_state = adjudicate_orders(self.state, orders)
        next_state = self._capture_centers(next_state)
        next_state = self._eliminate_powers(next_state)
        next_state.turn = self.state.turn + 1
        return next_state

    def _select_orders(self) -> Dict[tuple[Power, str], Order]:
        orders: Dict[tuple[Power, str], Order] = {}
        for power in sorted(self.state.units.keys()):
            if power in self.eliminated:
                continue
            unit_orders = legal_orders(self.state, self.map_def, power)
            for unit_id in sorted(unit_orders.keys()):
                options = unit_orders[unit_id]
                if not options:
                    orders[(power, unit_id)] = Hold(power=power, unit_id=unit_id)
                    continue
                ordered_options = sorted(options, key=_order_sort_key)
                orders[(power, unit_id)] = self.rng.choice(ordered_options)
        return orders

    def _capture_centers(self, state: GameState) -> GameState:
        new_state = state.clone()
        for center in self.map_def.supply_centers:
            owner = _unit_owner_at_node(new_state, center)
            if owner is not None:
                new_state.center_owner[center] = owner
        return new_state

    def _eliminate_powers(self, state: GameState) -> GameState:
        new_state = state.clone()
        for power in list(new_state.units.keys()):
            if new_state.units[power]:
                continue
            self.eliminated.add(power)
            del new_state.units[power]
        return new_state

    def _center_counts(self) -> Dict[Power, int]:
        counts: Dict[Power, int] = {}
        for owner in self.state.center_owner.values():
            if owner is None:
                continue
            counts[owner] = counts.get(owner, 0) + 1
        return counts

    def _check_target_centers(self) -> Optional[Power]:
        counts = self._center_counts()
        winners = [power for power, count in counts.items() if count >= self.target_centers]
        if len(winners) == 1:
            return winners[0]
        if len(winners) > 1:
            return None
        return None

    def _resolve_max_turns(self) -> GameResult:
        counts = self._center_counts()
        if not counts:
            return GameResult(
                winner=None,
                draw=True,
                centers=counts,
                turn=self.state.turn,
                reason="max_turns",
            )
        max_centers = max(counts.values())
        leaders = [power for power, count in counts.items() if count == max_centers]
        if len(leaders) == 1:
            winner = leaders[0]
            draw = False
        else:
            winner = None
            draw = True
        return GameResult(
            winner=winner,
            draw=draw,
            centers=counts,
            turn=self.state.turn,
            reason="max_turns",
        )


def _order_sort_key(order: Order) -> tuple:
    if isinstance(order, Hold):
        return ("hold",)
    if isinstance(order, Move):
        return ("move", order.to_node)
    if isinstance(order, Support):
        return (
            "support",
            order.supported_power,
            order.supported_unit_id,
            order.from_node,
            order.to_node or "",
        )
    return ("unknown",)


def _unit_owner_at_node(state: GameState, node: Node) -> Optional[Power]:
    for power, units in state.units.items():
        for location in units.values():
            if location == node:
                return power
    return None


def run_game(
    map_def: MapDef,
    *,
    target_centers: int,
    max_turns: int,
    seed: int = 0,
    initial_state: GameState | None = None,
) -> GameResult:
    state = initial_state or initialize_state(map_def)
    game = Game(
        map_def=map_def,
        state=state,
        target_centers=target_centers,
        max_turns=max_turns,
        seed=seed,
    )
    return game.run()


if __name__ == "__main__":
    map_def = MapDef(
        name="mini",
        nodes=("A", "B", "C"),
        edges=(("A", "B"), ("B", "C")),
        supply_centers=("A", "B", "C"),
        home_centers={"p1": "A", "p2": "C"},
    )


    #random seed
    import random
    seed = random.randint(0, 1000000)

    result = run_game(
        map_def,
        target_centers=2,
        max_turns=50,
        seed=seed,
    )

    print("winner:", result.winner)
    print("draw:", result.draw)
    print("centers:", result.centers)
    print("turn:", result.turn)
    print("reason:", result.reason)
