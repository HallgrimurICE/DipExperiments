"""Triangle 3-player map with two units per power."""

from __future__ import annotations

from dip_tom.env.map import MapDef

POWERS = ("A", "B", "C")

MAP_DEF = MapDef(
    name="triangle3",
    nodes=(
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "N1",
        "N2",
        "N3",
        "N4",
        "X",
    ),
    edges=(
        ("A1", "A2"),
        ("A1", "N1"),
        ("A2", "N2"),
        ("N1", "N2"),
        ("N1", "X"),
        ("N2", "X"),
        ("B1", "B2"),
        ("B1", "N2"),
        ("B2", "N3"),
        ("N2", "N3"),
        ("N3", "X"),
        ("C1", "C2"),
        ("C1", "N3"),
        ("C2", "N4"),
        ("N3", "N4"),
        ("N4", "X"),
        ("N4", "N1"),
    ),
    supply_centers=(
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "N1",
        "N2",
        "N3",
        "N4",
        "X",
    ),
    home_centers={
        "A": ("A1", "A2"),
        "B": ("B1", "B2"),
        "C": ("C1", "C2"),
    },
)

STARTING_UNITS = {
    "A": {"A1": "A1", "A2": "A2"},
    "B": {"B1": "B1", "B2": "B2"},
    "C": {"C1": "C1", "C2": "C2"},
}

NEUTRAL_CENTERS = ("N1", "N2", "N3", "N4")

CONTESTED_CENTER = "X"
