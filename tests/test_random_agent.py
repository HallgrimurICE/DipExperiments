from dip_tom.agents.random_agent import RandomAgent
from dip_tom.env.orders import legal_orders
from dip_tom.env.state import GameState
from dip_tom.maps import triangle3


def test_random_agent_returns_order_for_each_unit():
    state = GameState(
        units={power: dict(units) for power, units in triangle3.STARTING_UNITS.items()}
    )
    agent = RandomAgent(seed=13)

    orders = agent.select_orders(state, triangle3.MAP_DEF, "A")

    expected_unit_ids = set(triangle3.STARTING_UNITS["A"].keys())
    assert {unit_id for _, unit_id in orders.keys()} == expected_unit_ids

    legal = legal_orders(state, triangle3.MAP_DEF, "A")
    for unit_id in expected_unit_ids:
        assert orders[("A", unit_id)] in legal[unit_id]
