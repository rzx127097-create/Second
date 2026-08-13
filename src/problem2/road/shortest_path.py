"""Deterministic Dijkstra shortest paths."""

from __future__ import annotations

import heapq
from math import inf
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .graph import RoadGraph


def shortest_path(graph: "RoadGraph", source: str, target: str) -> tuple[list[str], float]:
    """Return ``(node path, metric distance_m)`` or explicitly report unreachable nodes."""

    if not graph.has_node(source) or not graph.has_node(target):
        raise ValueError(f"unreachable road path from {source!r} to {target!r}")
    if source == target:
        return [source], 0.0
    distances = {node: inf for node in graph.nodes}
    previous: dict[str, str | None] = {node: None for node in graph.nodes}
    distances[source] = 0.0
    queue: list[tuple[float, str]] = [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance > distances[node] + 1e-12:
            continue
        if node == target:
            break
        for neighbour, weight in graph.neighbors(node):
            candidate = distance + weight
            if candidate < distances[neighbour] - 1e-12:
                distances[neighbour] = candidate
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
            elif abs(candidate - distances[neighbour]) <= 1e-12 and node < (previous[neighbour] or "~"):
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
    if distances[target] == inf:
        raise ValueError(f"unreachable road path from {source!r} to {target!r}")
    path = [target]
    while path[-1] != source:
        parent = previous[path[-1]]
        if parent is None:  # Defensive guard for malformed graphs.
            raise ValueError(f"unreachable road path from {source!r} to {target!r}")
        path.append(parent)
    path.reverse()
    return path, distances[target]


def dijkstra(graph: "RoadGraph", source: str, target: str) -> tuple[list[str], float]:
    """Compatibility alias for :func:`shortest_path`."""

    return shortest_path(graph, source, target)

