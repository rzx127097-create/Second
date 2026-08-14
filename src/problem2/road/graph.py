"""Weighted undirected road graph with metre-based edge lengths."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable, Mapping


@dataclass
class RoadGraph:
    nodes: dict[str, tuple[float, float]]
    adjacency: dict[str, dict[str, float]]

    @classmethod
    def from_edges(
        cls,
        nodes: Mapping[str, tuple[float, float]],
        edges: Iterable[tuple[str, str] | tuple[str, str, float]],
    ) -> "RoadGraph":
        positions = {str(node_id): (float(xy[0]), float(xy[1])) for node_id, xy in nodes.items()}
        adjacency = {node_id: {} for node_id in positions}
        for edge in edges:
            if len(edge) == 2:
                left, right = edge
                weight = hypot(
                    positions[str(right)][0] - positions[str(left)][0],
                    positions[str(right)][1] - positions[str(left)][1],
                )
            elif len(edge) == 3:
                left, right, weight = edge
                weight = float(weight)
            else:
                raise ValueError("road edge must contain two endpoints and optionally a weight")
            left, right = str(left), str(right)
            if left not in positions or right not in positions:
                raise KeyError("road edge references an unknown node")
            if left == right:
                raise ValueError("self-loops are not valid road edges")
            if weight < 0:
                raise ValueError("road edge weight must be non-negative")
            # Parallel edges collapse to their shortest metric edge.
            adjacency[left][right] = min(weight, adjacency[left].get(right, weight))
            adjacency[right][left] = min(weight, adjacency[right].get(left, weight))
        return cls(positions, adjacency)

    @classmethod
    def from_grid(
        cls, cells: Iterable[tuple[int, int]], cell_size_m: float | tuple[float, float] = 1.0
    ) -> "RoadGraph":
        if isinstance(cell_size_m, tuple):
            row_size, col_size = (float(cell_size_m[0]), float(cell_size_m[1]))
        else:
            row_size = col_size = float(cell_size_m)
        if row_size <= 0 or col_size <= 0:
            raise ValueError("cell_size_m must be positive")
        occupied = {tuple(cell) for cell in cells}
        nodes = {str(cell): (float(cell[1]) * col_size, float(cell[0]) * row_size) for cell in occupied}
        edges = []
        for row, col in occupied:
            for neighbour in ((row, col + 1), (row + 1, col)):
                if neighbour in occupied:
                    edge_size = col_size if neighbour[0] == row else row_size
                    edges.append((str((row, col)), str(neighbour), edge_size))
        return cls.from_edges(nodes, edges)

    def neighbors(self, node_id: str) -> tuple[tuple[str, float], ...]:
        if node_id not in self.adjacency:
            raise KeyError(node_id)
        return tuple(sorted(self.adjacency[node_id].items(), key=lambda item: item[0]))

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def edge_weight(self, source: str, target: str) -> float:
        try:
            return self.adjacency[source][target]
        except KeyError as exc:
            raise KeyError(f"no road edge between {source!r} and {target!r}") from exc

    def component(self, source: str) -> set[str]:
        if source not in self.nodes:
            raise KeyError(source)
        seen = {source}
        stack = [source]
        while stack:
            node = stack.pop()
            for neighbour in self.adjacency[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        return seen
