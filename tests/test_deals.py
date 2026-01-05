from dip_tom.env.orders import Hold, Move, Support
from dip_tom.env.state import GameState
from dip_tom.negotiation.deal import NoEnterDeal, PeaceDeal, SupportDeal, UnitRef


def test_peace_deal_restricts_orders_and_flags_violations():
    state = GameState(
        units={
            "A": {"A1": "N1"},
            "B": {"B1": "N2"},
        }
    )
    deal = PeaceDeal.from_state("A", "B", state)
    legal_orders = {
        "A1": [
            Hold("A", "A1"),
            Move("A", "A1", "N2"),
            Move("A", "A1", "N3"),
        ]
    }

    restricted = deal.allowed_orders("A", legal_orders)

    assert all(
        not (isinstance(order, Move) and order.to_node == "N2")
        for order in restricted["A1"]
    )

    submitted = {"A1": Move("A", "A1", "N2")}
    violations = deal.violations("A", submitted, state)

    assert len(violations) == 1
    assert violations[0].unit_id == "A1"


def test_support_deal_restricts_orders_and_flags_violations():
    state = GameState(
        units={
            "A": {"A1": "N1"},
            "B": {"B1": "N2"},
        }
    )
    deal = SupportDeal(
        i="A",
        j="B",
        supported_unit=UnitRef(power="A", unit_id="A1"),
        from_node="N1",
        to_node="N3",
        supporter_unit=UnitRef(power="B", unit_id="B1"),
    )
    legal_orders = {
        "B1": [
            Hold("B", "B1"),
            Support(
                power="B",
                unit_id="B1",
                supported_power="A",
                supported_unit_id="A1",
                from_node="N1",
                to_node="N3",
            ),
        ]
    }

    restricted = deal.allowed_orders("B", legal_orders)

    assert restricted["B1"] == [
        Support(
            power="B",
            unit_id="B1",
            supported_power="A",
            supported_unit_id="A1",
            from_node="N1",
            to_node="N3",
        )
    ]

    submitted = {"B1": Hold("B", "B1")}
    violations = deal.violations("B", submitted, state)

    assert len(violations) == 1
    assert violations[0].unit_id == "B1"


def test_no_enter_deal_restricts_orders_and_flags_violations():
    state = GameState(
        units={
            "A": {"A1": "N1"},
            "B": {"B1": "N2"},
        }
    )
    deal = NoEnterDeal(i="A", j="B", node="N3")
    legal_orders = {
        "A1": [
            Hold("A", "A1"),
            Move("A", "A1", "N3"),
            Move("A", "A1", "N4"),
        ]
    }

    restricted = deal.allowed_orders("A", legal_orders)

    assert all(
        not (isinstance(order, Move) and order.to_node == "N3")
        for order in restricted["A1"]
    )

    submitted = {"A1": Move("A", "A1", "N3")}
    violations = deal.violations("A", submitted, state)

    assert len(violations) == 1
    assert violations[0].unit_id == "A1"
