"""Run a full triangle3 game with two units per power."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dip_tom.agents.heuristic_agent import HeuristicAgent
from dip_tom.agents.random_agent import RandomAgent
from dip_tom.env.game import active_powers, run_game, winning_power
from dip_tom.env.state import GameState
from dip_tom.maps import triangle3


def main() -> None:
    state = GameState(
        units={
            "A": {"A1": "A1", "A2": "A2"},
            "B": {"B1": "B1", "B2": "B2"},
            "C": {"C1": "C1", "C2": "C2"},
        }
    )
    agents = {
        "A": HeuristicAgent(),
        "B": RandomAgent(seed=2),
        "C": RandomAgent(seed=3),
    }

    final_state = run_game(state, triangle3.MAP_DEF, agents, max_turns=200)
    survivors = active_powers(final_state)
    winner = winning_power(final_state, triangle3.MAP_DEF)
    print(f"Game finished after {final_state.turn} turns.")
    if winner:
        print(f"Winning power: {winner}")
    print(f"Remaining powers: {', '.join(survivors) if survivors else 'none'}")
    print(final_state.units)


if __name__ == "__main__":
    main()
