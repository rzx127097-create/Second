from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from problem2.config import ScaleConfig, load_g2_config
from problem2.domain import Action
from problem2.road.models import (
    ProjectedRoadEdge,
    ProjectedRoadNode,
    ProjectedRoadSource,
)
from problem2.road.raster import rasterize_road_source


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")


def _source(
    edges: list[tuple[str, tuple[tuple[float, float], ...]]],
    nodes: dict[str, tuple[float, float]] | None = None,
) -> ProjectedRoadSource:
    projected_nodes = {
        node_id: ProjectedRoadNode(node_id, 0.0, 0.0, x_m, y_m)
        for node_id, (x_m, y_m) in (nodes or {}).items()
    }
    projected_edges = tuple(
        ProjectedRoadEdge(edge_id, edge_id, f"{edge_id}-u", f"{edge_id}-v", coords)
        for edge_id, coords in edges
    )
    return ProjectedRoadSource(
        source_path="fixture.graphml",
        source_sha256="A" * 64,
        source_crs="EPSG:4326",
        target_crs="EPSG:32643",
        source_bbox_lonlat=(0.0, 0.0, 1.0, 1.0),
        aoi_bounds_m=(0.0, 0.0, 100.0, 100.0),
        aoi_bbox_lonlat=(0.0, 0.0, 1.0, 1.0),
        nodes=projected_nodes,
        edges=projected_edges,
    )


def _scale(height: int = 10, width: int = 10) -> ScaleConfig:
    return ScaleConfig("fixture", (height, width), 10)


def test_diagonal_source_segment_becomes_logged_four_connected_path() -> None:
    source = _source([("diagonal", ((5.0, 95.0), (15.0, 85.0)))])

    graph = rasterize_road_source(source, _scale(), max_segment_m=5.0)

    for u, v in graph.edges:
        dr = abs(int(graph.node_rows[u]) - int(graph.node_rows[v]))
        dc = abs(int(graph.node_cols[u]) - int(graph.node_cols[v]))
        assert dr + dc == 1
    assert graph.repairs
    assert {repair.reason for repair in graph.repairs} == {
        "same_source_edge_diagonal_bridge"
    }
    assert {repair.source_edge_id for repair in graph.repairs} == {"diagonal"}


def test_nearby_independent_components_are_not_repaired() -> None:
    source = _source(
        [
            ("west", ((5.0, 95.0), (15.0, 95.0))),
            ("east", ((25.0, 85.0), (35.0, 85.0))),
        ]
    )

    graph = rasterize_road_source(source, _scale(), max_segment_m=5.0)

    assert sorted(graph.component_sizes, reverse=True) == [2, 2]
    assert graph.repairs == ()
    assert graph.primary_component_id == int(graph.component_id[0, 0])
    assert graph.component_id[1, 2] != graph.primary_component_id


def test_action_masks_and_metric_edge_lengths_follow_four_connected_geometry() -> None:
    source = _source(
        [("corner", ((10.0, 95.0), (30.0, 95.0), (30.0, 85.0)))]
    )

    graph = rasterize_road_source(source, _scale(height=10, width=5), 5.0)
    corner_node = graph.node_index(0, 1)

    assert graph.action_mask[0, 1].tolist() == [True, False, True, True, False]
    assert sorted(graph.edge_lengths_m.tolist()) == pytest.approx([10.0, 20.0])
    assert [action for _, action, _ in graph.neighbors(corner_node)] == [
        Action.DOWN,
        Action.LEFT,
    ]


def test_preserves_source_node_and_edge_cell_mappings() -> None:
    source = _source(
        [("mapped", ((5.0, 95.0), (25.0, 95.0)))],
        nodes={"n0": (5.0, 95.0), "n1": (25.0, 95.0)},
    )

    graph = rasterize_road_source(source, _scale(), 5.0)

    assert graph.source_node_to_cell == {"n0": (0, 0), "n1": (0, 2)}
    assert graph.source_edge_to_cells["mapped"] == ((0, 0), (0, 1), (0, 2))


@pytest.mark.parametrize(
    ("scale_id", "shape"),
    [(scale.scale_id, scale.grid_shape) for scale in CONFIG.scales],
)
def test_each_frozen_scale_produces_exact_array_shapes(
    scale_id: str, shape: tuple[int, int]
) -> None:
    source = _source([("road", ((1.0, 50.0), (99.0, 50.0)))])
    scale = next(scale for scale in CONFIG.scales if scale.scale_id == scale_id)

    graph = rasterize_road_source(source, scale, CONFIG.max_segment_m)

    assert graph.road_mask.shape == shape
    assert graph.action_mask.shape == (*shape, 5)
    assert graph.component_id.shape == shape
    assert graph.road_mask.dtype == np.bool_
    assert graph.action_mask.dtype == np.bool_
