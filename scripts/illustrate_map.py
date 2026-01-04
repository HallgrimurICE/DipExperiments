"""Render a MapDef as a plotted graph image.

Example:
    python -m scripts.illustrate_map triangle3 --output triangle3.png
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import importlib.util

import networkx as nx

if TYPE_CHECKING:
    from dip_tom.env.map import MapDef


def _ensure_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    src_path = repo_root / "src"
    if src_path.is_dir() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def _load_map(module_name: str) -> MapDef:
    module = importlib.import_module(f"dip_tom.maps.{module_name}")
    if not hasattr(module, "MAP_DEF"):
        raise SystemExit(f"Module dip_tom.maps.{module_name} does not define MAP_DEF")
    return module.MAP_DEF


def _require_matplotlib() -> None:
    if importlib.util.find_spec("matplotlib") is None:
        raise SystemExit(
            "matplotlib is required for plotting. Install it with "
            "`pip install matplotlib`."
        )


def plot_map(map_def: MapDef, output: Path | None) -> None:
    graph = nx.Graph()
    graph.add_nodes_from(map_def.nodes)
    graph.add_edges_from(map_def.edges)

    home_nodes = {node for centers in map_def.home_centers.values() for node in centers}
    supply_nodes = set(map_def.supply_centers)
    _require_matplotlib()
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")

    pos = nx.spring_layout(graph, seed=42)
    node_colors = []
    node_sizes = []
    for node in graph.nodes:
        if node in home_nodes:
            node_colors.append("#ffec8b")
            node_sizes.append(900)
        elif node in supply_nodes:
            node_colors.append("#8ecae6")
            node_sizes.append(700)
        else:
            node_colors.append("#d9d9d9")
            node_sizes.append(500)

    nx.draw_networkx_edges(graph, pos, width=1.5)
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_labels(graph, pos, font_size=9)

    plt.axis("off")
    if output:
        plt.savefig(output, bbox_inches="tight")
    else:
        fallback = Path("map.png")
        plt.savefig(fallback, bbox_inches="tight")
        print(f"Saved plot to {fallback.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render map as a plotted graph.")
    parser.add_argument("map", help="Map module name under dip_tom.maps (e.g. triangle3)")
    parser.add_argument("--output", "-o", type=Path, help="Write image output to file")
    args = parser.parse_args()

    _ensure_src_on_path()
    map_def = _load_map(args.map)
    plot_map(map_def, args.output)


if __name__ == "__main__":
    main()
