from __future__ import annotations

import heapq
import math

import networkx as nx

from problem2.road.models import RasterRoadGraph


class NoPathError(ValueError):
    """Raised when a requested road path does not exist."""


def _validate_node(graph: RasterRoadGraph, node: int) -> None:
    if isinstance(node, bool) or not isinstance(node, int) or not (0 <= node < len(graph.node_rows)):
        raise IndexError(f"road node {node!r} is outside the graph")


def _heuristic(graph: RasterRoadGraph, node: int, goal: int) -> float:
    row_distance = abs(int(graph.node_rows[node]) - int(graph.node_rows[goal]))
    col_distance = abs(int(graph.node_cols[node]) - int(graph.node_cols[goal]))
    return row_distance * graph.cell_height_m + col_distance * graph.cell_width_m


def astar_distance(graph: RasterRoadGraph, start: int, goal: int) -> float:
    _validate_node(graph, start)
    _validate_node(graph, goal)
    if start == goal:
        return 0.0
    distances = {start: 0.0}
    queue: list[tuple[float, float, int]] = [(_heuristic(graph, start, goal), 0.0, start)]
    while queue:
        _, distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node == goal:
            return distance
        for neighbor, _, edge_length in graph.neighbors(node):
            candidate = distance + edge_length
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                heapq.heappush(
                    queue,
                    (candidate + _heuristic(graph, neighbor, goal), candidate, neighbor),
                )
    raise NoPathError(f"no path from road node {start} to {goal}")


def dijkstra_distance(graph: RasterRoadGraph, start: int, goal: int) -> float:
    _validate_node(graph, start)
    _validate_node(graph, goal)
    oracle = nx.Graph()
    oracle.add_nodes_from(range(len(graph.node_rows)))
    for edge_index, (left, right) in enumerate(graph.edges):
        oracle.add_edge(
            int(left),
            int(right),
            weight=float(graph.edge_lengths_m[edge_index]),
        )
    try:
        return float(nx.dijkstra_path_length(oracle, start, goal, weight="weight"))
    except nx.NetworkXNoPath as exc:
        raise NoPathError(f"no path from road node {start} to {goal}") from exc
