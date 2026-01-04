"""Render a MapDef as Graphviz DOT output.

Example:
    python scripts/illustrate_map.py triangle3 --output triangle3.dot
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from dip_tom.env.map import MapDef


def _load_map(module_name: str) -> MapDef:
    module = importlib.import_module(f"dip_tom.maps.{module_name}")
    if not hasattr(module, "MAP_DEF"):
        raise SystemExit(f"Module dip_tom.maps.{module_name} does not define MAP_DEF")
    return module.MAP_DEF


def _dot_label(node: str) -> str:
    return node.replace("\"", "\\\"")


def map_to_dot(map_def: MapDef) -> str:
    home_nodes = {node for centers in map_def.home_centers.values() for node in centers}
    supply_nodes = set(map_def.supply_centers)

    lines = ["graph map {"]
    lines.append("  layout=neato;")
    lines.append("  overlap=false;")
    for node in map_def.nodes:
        attrs = []
        if node in supply_nodes:
            attrs.append("shape=doublecircle")
        else:
            attrs.append("shape=circle")
        if node in home_nodes:
            attrs.append("style=filled")
            attrs.append("fillcolor=lightgoldenrod1")
        line = f'  "{_dot_label(node)}" [{", ".join(attrs)}];'
        lines.append(line)

    for left, right in map_def.edges:
        lines.append(f'  "{_dot_label(left)}" -- "{_dot_label(right)}";')

    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render map to Graphviz DOT.")
    parser.add_argument("map", help="Map module name under dip_tom.maps (e.g. triangle3)")
    parser.add_argument("--output", "-o", type=Path, help="Write DOT output to file")
    args = parser.parse_args()

    map_def = _load_map(args.map)
    dot = map_to_dot(map_def)

    if args.output:
        args.output.write_text(dot)
    else:
        print(dot)


if __name__ == "__main__":
    main()
