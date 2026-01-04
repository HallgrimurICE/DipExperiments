from dip_tom.env.map import validate_map
from dip_tom.env.orders import legal_orders
from dip_tom.env.state import GameState
from dip_tom.maps import sample4, triangle3


def test_maps_validate():
    for map_def in (triangle3.MAP_DEF, sample4.MAP_DEF):
        validate_map(map_def)


def test_legal_orders_exist_for_all_units_turn0():
    for map_module in (triangle3, sample4):
        state = GameState(
            units={
                power: dict(units)
                for power, units in map_module.STARTING_UNITS.items()
            }
        )
        for power, units in map_module.STARTING_UNITS.items():
            orders_by_unit = legal_orders(state, map_module.MAP_DEF, power)
            for unit_id in units:
                assert unit_id in orders_by_unit
                assert orders_by_unit[unit_id]
