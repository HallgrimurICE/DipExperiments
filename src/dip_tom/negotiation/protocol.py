"""Pairwise negotiation protocol for proposing and accepting deals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Protocol

from dip_tom.env.state import GameState, Power
from dip_tom.negotiation.deal import Deal


class NegotiationParticipant(Protocol):
    """Interface for proposing and accepting negotiation deals."""

    def propose_deal(self, state: GameState, power: Power, target: Power) -> Deal | None:
        """Return a deal proposal from power to target, or None to skip."""

    def accept_deal(self, state: GameState, power: Power, proposer: Power, deal: Deal) -> bool:
        """Return True if the deal is accepted by power, False otherwise."""


@dataclass
class NegotiationProtocol:
    """Run a turn-by-turn pairwise negotiation protocol."""

    participants: Mapping[Power, NegotiationParticipant]
    accepted_deals_by_power: Dict[Power, List[Deal]] = field(default_factory=dict)

    def run_turn(self, state: GameState, powers: Iterable[Power] | None = None) -> Dict[Power, List[Deal]]:
        """Run the proposal/acceptance protocol and record accepted deals.

        The protocol runs for each ordered pair of distinct powers i -> j,
        allowing i to propose at most one deal and j to accept or reject it.
        """
        ordered_powers = list(powers) if powers is not None else list(self.participants.keys())
        accepted: Dict[Power, List[Deal]] = {power: [] for power in ordered_powers}
        for proposer in ordered_powers:
            proposer_participant = self.participants.get(proposer)
            if proposer_participant is None:
                continue
            for responder in ordered_powers:
                if proposer == responder:
                    continue
                responder_participant = self.participants.get(responder)
                if responder_participant is None:
                    continue
                deal = proposer_participant.propose_deal(state, proposer, responder)
                if deal is None:
                    continue
                if responder_participant.accept_deal(state, responder, proposer, deal):
                    accepted[proposer].append(deal)
                    accepted[responder].append(deal)
        self.accepted_deals_by_power = accepted
        return accepted

    def accepted_deals(self, power: Power) -> List[Deal]:
        """Return accepted deals for the requested power for the current turn."""
        return list(self.accepted_deals_by_power.get(power, []))

    def expire_deals(self) -> None:
        """Expire deals after the action phase."""
        self.accepted_deals_by_power = {
            power: [] for power in self.participants.keys()
        }
