"""Sample 4-player map with two units per power."""

from __future__ import annotations

from dip_tom.env.map import MapDef

POWERS = ("A", "B", "C", "D")

MAP_DEF = MapDef(
    name="sample4",
    nodes=(
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "D1",
        "D2",
        "N1",
        "N2",
        "N3",
        "N4",
        "X",
        "Y",
    ),
    edges=(
        ("A1", "A2"),
        ("A1", "N1"),
        ("A1", "N4"),
        ("A2", "N1"),
        ("B1", "B2"),
        ("B1", "N1"),
        ("B1", "N2"),
        ("B2", "N2"),
        ("C1", "C2"),
        ("C1", "N2"),
        ("C1", "N3"),
        ("C2", "N3"),
        ("D1", "D2"),
        ("D1", "N3"),
        ("D1", "N4"),
        ("D2", "N4"),
        ("N1", "N2"),
        ("N2", "N3"),
        ("N3", "N4"),
        ("N4", "N1"),
        ("N1", "X"),
        ("N2", "X"),
        ("N3", "X"),
        ("N4", "X"),
        ("X", "Y"),
    ),
    supply_centers=(
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "D1",
        "D2",
        "N1",
        "N2",
        "N3",
        "N4",
        "X",
        "Y",
    ),
    home_centers={
        "A": ("A1", "A2"),
        "B": ("B1", "B2"),
        "C": ("C1", "C2"),
        "D": ("D1", "D2"),
    },
)

STARTING_UNITS = {
    "A": {"A1": "A1", "A2": "A2"},
    "B": {"B1": "B1", "B2": "B2"},
    "C": {"C1": "C1", "C2": "C2"},
    "D": {"D1": "D1", "D2": "D2"},
}

NEUTRAL_CENTERS = ("N1", "N2", "N3", "N4", "Y")

CONTESTED_CENTER = "X"
