from dip_tom.env.adjudicator import adjudicate_orders
from dip_tom.env.orders import Hold, Move, Support
from dip_tom.env.state import GameState


def test_supported_move_beats_unsupported_hold():
    # Attacker has one support, defender holds with base strength.
    # Supported attack should dislodge the defender and move into the province.
    state = GameState(
        units={
            "p1": {"u1": "A", "s1": "C"},
            "p2": {"u2": "B"},
        }
    )
    orders = {
        ("p1", "u1"): Move("p1", "u1", "B"),
        ("p1", "s1"): Support("p1", "s1", "p1", "u1", "A", "B"),
        ("p2", "u2"): Hold("p2", "u2"),
    }

    next_state = adjudicate_orders(state, orders)

    assert next_state.units["p1"]["u1"] == "B"
    assert "u2" not in next_state.units.get("p2", {})


def test_supported_hold_blocks_unsupported_attack():
    # Defender holds with support, raising defense strength above the attacker.
    # Attacker should bounce and both units remain in place.
    state = GameState(
        units={
            "p1": {"u1": "A"},
            "p2": {"u2": "B", "s1": "C"},
        }
    )
    orders = {
        ("p1", "u1"): Move("p1", "u1", "B"),
        ("p2", "u2"): Hold("p2", "u2"),
        ("p2", "s1"): Support("p2", "s1", "p2", "u2", "B", None),
    }

    next_state = adjudicate_orders(state, orders)

    assert next_state.units["p1"]["u1"] == "A"
    assert next_state.units["p2"]["u2"] == "B"


def test_two_supported_moves_tie_and_bounce():
    # Two attackers with equal supported strength target the same node.
    # Equal strength means a bounce, so both moves fail.
    state = GameState(
        units={
            "p1": {"u1": "A", "s1": "C"},
            "p2": {"u2": "D", "s2": "E"},
        }
    )
    orders = {
        ("p1", "u1"): Move("p1", "u1", "B"),
        ("p1", "s1"): Support("p1", "s1", "p1", "u1", "A", "B"),
        ("p2", "u2"): Move("p2", "u2", "B"),
        ("p2", "s2"): Support("p2", "s2", "p2", "u2", "D", "B"),
    }

    next_state = adjudicate_orders(state, orders)

    assert next_state.units["p1"]["u1"] == "A"
    assert next_state.units["p2"]["u2"] == "D"


def test_head_to_head_equal_strength_bounces():
    # Two units swap targets with equal strength, so both moves should bounce.
    state = GameState(
        units={
            "p1": {"u1": "A"},
            "p2": {"u2": "B"},
        }
    )
    orders = {
        ("p1", "u1"): Move("p1", "u1", "B"),
        ("p2", "u2"): Move("p2", "u2", "A"),
    }

    next_state = adjudicate_orders(state, orders)

    assert next_state.units["p1"]["u1"] == "A"
    assert next_state.units["p2"]["u2"] == "B"


def test_swap_with_strength_advantage_succeeds():
    # Head-to-head swap attempt where one mover has support and the other does not.
    # The supported move succeeds; the weaker move is dislodged and removed.
    state = GameState(
        units={
            "p1": {"u1": "A", "s1": "C"},
            "p2": {"u2": "B"},
        }
    )
    orders = {
        ("p1", "u1"): Move("p1", "u1", "B"),
        ("p1", "s1"): Support("p1", "s1", "p1", "u1", "A", "B"),
        ("p2", "u2"): Move("p2", "u2", "A"),
    }

    next_state = adjudicate_orders(state, orders)

    assert next_state.units["p1"]["u1"] == "B"
    assert "u2" not in next_state.units.get("p2", {})
