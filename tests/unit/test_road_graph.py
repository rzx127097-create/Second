from __future__ import annotations

import pytest

from problem2.road.graph import RoadGraph
from problem2.road.shortest_path import shortest_path
from problem2.road.topology import connected_components, four_connected_edges


def test_four_connected_graph_and_shortest_path_use_metric_edge_weights() -> None:
    graph = RoadGraph.from_edges(
        nodes={"a": (0.0, 0.0), "b": (1.0, 0.0), "c": (1.0, 1.0)},
        edges=[("a", "b", 2.0), ("b", "c", 3.0)],
    )
    path, distance = shortest_path(graph, "a", "c")
    assert path == ["a", "b", "c"]
    assert distance == pytest.approx(5.0)


def test_components_and_four_connected_edges_are_deterministic() -> None:
    cells = {(0, 0), (0, 1), (2, 2)}
    edges = four_connected_edges(cells)
    assert edges == [((0, 0), (0, 1))]
    assert connected_components(cells) == [{(0, 0), (0, 1)}, {(2, 2)}]


def test_unreachable_path_is_explicit() -> None:
    graph = RoadGraph.from_edges(
        nodes={"a": (0.0, 0.0), "b": (1.0, 0.0)}, edges=[]
    )
    with pytest.raises(ValueError, match="unreachable"):
        shortest_path(graph, "a", "b")
