from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapDef:
    name: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    supply_centers: tuple[str, ...]
    home_centers: dict[str, str]

    def neighbors(self, node: str) -> list[str]:
        neighbors: list[str] = []
        for left, right in self.edges:
            if left == node:
                neighbors.append(right)
            elif right == node:
                neighbors.append(left)
        return neighbors


def validate_map(map_def: MapDef) -> None:
    node_set = set(map_def.nodes)
    if len(node_set) != len(map_def.nodes):
        raise ValueError("map nodes contain duplicates")

    edge_set: set[tuple[str, str]] = set()
    for left, right in map_def.edges:
        if left not in node_set or right not in node_set:
            raise ValueError("map edge references unknown node")
        canonical = tuple(sorted((left, right)))
        if canonical in edge_set:
            raise ValueError("map edges contain duplicates")
        edge_set.add(canonical)

    if not set(map_def.supply_centers).issubset(node_set):
        raise ValueError("supply centers must be a subset of nodes")

    for home_center in map_def.home_centers.values():
        if home_center not in node_set:
            raise ValueError("home centers must reference valid nodes")
