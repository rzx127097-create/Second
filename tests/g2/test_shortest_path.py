from __future__ import annotations

import pytest

from problem2.road.search import NoPathError, astar_distance, dijkstra_distance
from tests.g2.helpers import make_raster_graph


def test_astar_uses_hand_derived_anisotropic_metric_weights() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (1, 1)],
        [(0, 1), (1, 2)],
        cell_width_m=20.0,
        cell_height_m=15.0,
    )

    assert astar_distance(graph, 0, 2) == pytest.approx(35.0)


def test_astar_matches_independent_dijkstra_on_multiple_pairs() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)],
        [(0, 1), (1, 2), (1, 3), (3, 4)],
        cell_width_m=12.0,
        cell_height_m=7.0,
    )

    for start, goal in [(0, 2), (0, 4), (2, 4), (4, 0)]:
        assert astar_distance(graph, start, goal) == pytest.approx(
            dijkstra_distance(graph, start, goal), abs=1e-9
        )


def test_shortest_paths_reject_unreachable_and_invalid_nodes() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (3, 3)],
        [(0, 1)],
        component_ids=[0, 0, 1],
    )

    with pytest.raises(NoPathError, match="no path"):
        astar_distance(graph, 0, 2)
    with pytest.raises(IndexError, match="node"):
        dijkstra_distance(graph, -1, 1)
