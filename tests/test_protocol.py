from __future__ import annotations

from dataclasses import dataclass

from dip_tom.env.state import GameState
from dip_tom.negotiation.deal import Deal
from dip_tom.negotiation.protocol import NegotiationParticipant, NegotiationProtocol


@dataclass(frozen=True)
class DummyDeal(Deal):
    label: str


class DummyParticipant(NegotiationParticipant):
    def __init__(self, deal_label: str, accept: bool = True, propose: bool = True) -> None:
        self.deal_label = deal_label
        self.accept = accept
        self.propose = propose

    def propose_deal(self, state: GameState, power: str, target: str) -> Deal | None:
        if not self.propose:
            return None
        return DummyDeal(f"{self.deal_label}:{power}->{target}")

    def accept_deal(self, state: GameState, power: str, proposer: str, deal: Deal) -> bool:
        return self.accept


def test_protocol_records_and_expires_deals():
    state = GameState()
    participants = {
        "A": DummyParticipant("A"),
        "B": DummyParticipant("B"),
        "C": DummyParticipant("C", accept=False, propose=False),
    }
    protocol = NegotiationProtocol(participants)

    accepted = protocol.run_turn(state)

    assert [deal.label for deal in accepted["A"]] == ["A:A->B", "B:B->A"]
    assert [deal.label for deal in accepted["B"]] == ["A:A->B", "B:B->A"]
    assert accepted["C"] == []

    protocol.expire_deals()

    assert protocol.accepted_deals("A") == []
    assert protocol.accepted_deals("B") == []
