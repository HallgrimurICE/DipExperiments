from dip_tom.env.map import MapDef
from dip_tom.env.orders import Hold, Move, SupportMove, legal_orders
from dip_tom.env.state import GameState


def test_legal_orders_include_hold_and_moves():
    map_def = MapDef(
        name="mini",
        nodes=("A", "B", "C"),
        edges=(("A", "B"), ("B", "C")),
        supply_centers=(),
        home_centers={},
    )
    state = GameState(units={"p1": {"u1": "B"}})

    orders = legal_orders(state, map_def, "p1")["u1"]

    assert Hold("p1", "u1") in orders
    assert Move("p1", "u1", "A") in orders
    assert Move("p1", "u1", "C") in orders
    assert Move("p1", "u1", "B") not in orders


def test_support_move_requires_adjacent_target_and_legal_supported_move():
    map_def = MapDef(
        name="triangle",
        nodes=("A", "B", "C"),
        edges=(("A", "B"), ("B", "C"), ("A", "C")),
        supply_centers=(),
        home_centers={},
    )
    state = GameState(
        units={
            "p1": {"s1": "A"},
            "p2": {"u2": "B"},
        }
    )

    orders = legal_orders(state, map_def, "p1")["s1"]

    assert SupportMove("p1", "s1", "p2", "u2", "B", "C") in orders
    assert SupportMove("p1", "s1", "p2", "u2", "B", "A") not in orders
