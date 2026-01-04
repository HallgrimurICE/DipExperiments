"""Run a full triangle3 game with one unit per power."""

from __future__ import annotations

from dip_tom.agents.random_agent import RandomAgent
from dip_tom.env.game import active_powers, run_game
from dip_tom.env.state import GameState
from dip_tom.maps import triangle3


def main() -> None:
    state = GameState(
        units={
            "A": {"A1": "A1"},
            "B": {"B1": "B1"},
            "C": {"C1": "C1"},
        }
    )
    agents = {
        "A": RandomAgent(seed=1),
        "B": RandomAgent(seed=2),
        "C": RandomAgent(seed=3),
    }

    final_state = run_game(state, triangle3.MAP_DEF, agents, max_turns=200)
    survivors = active_powers(final_state)
    print(f"Game finished after {final_state.turn} turns.")
    print(f"Remaining powers: {', '.join(survivors) if survivors else 'none'}")
    print(final_state.units)


if __name__ == "__main__":
    main()
