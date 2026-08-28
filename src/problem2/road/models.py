from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from problem2.domain import Action


@dataclass(frozen=True)
class ProjectedRoadNode:
    source_id: str
    lon: float
    lat: float
    x_m: float
    y_m: float


@dataclass(frozen=True)
class ProjectedRoadEdge:
    source_id: str
    source_osm_id: str
    source_u: str
    source_v: str
    coords_m: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ProjectedRoadSource:
    source_path: str
    source_sha256: str
    source_crs: str
    target_crs: str
    source_bbox_lonlat: tuple[float, float, float, float]
    aoi_bounds_m: tuple[float, float, float, float]
    aoi_bbox_lonlat: tuple[float, float, float, float]
    nodes: Mapping[str, ProjectedRoadNode]
    edges: tuple[ProjectedRoadEdge, ...]


@dataclass(frozen=True)
class RepairRecord:
    source_edge_id: str
    from_cell: tuple[int, int]
    inserted_cell: tuple[int, int]
    to_cell: tuple[int, int]
    metric_length_m: float
    reason: str


@dataclass(frozen=True)
class RasterRoadGraph:
    scale_id: str
    grid_shape: tuple[int, int]
    aoi_bounds_m: tuple[float, float, float, float]
    cell_width_m: float
    cell_height_m: float
    road_mask: np.ndarray
    action_mask: np.ndarray
    component_id: np.ndarray
    node_rows: np.ndarray
    node_cols: np.ndarray
    node_x_m: np.ndarray
    node_y_m: np.ndarray
    edges: np.ndarray
    edge_lengths_m: np.ndarray
    component_sizes: tuple[int, ...]
    primary_component_id: int
    source_node_to_cell: Mapping[str, tuple[int, int]]
    source_edge_to_cells: Mapping[str, tuple[tuple[int, int], ...]]
    repairs: tuple[RepairRecord, ...]
    _neighbor_index: tuple[tuple[tuple[int, Action, float], ...], ...] | None = field(
        init=False, default=None, repr=False, compare=False
    )

    def node_index(self, row: int, col: int) -> int:
        matches = np.flatnonzero((self.node_rows == row) & (self.node_cols == col))
        if len(matches) != 1:
            raise KeyError(f"road cell ({row}, {col}) is not a unique node")
        return int(matches[0])

    def neighbors(self, node: int) -> list[tuple[int, Action, float]]:
        index = self._neighbor_index
        if index is None:
            indexed: list[list[tuple[int, Action, float]]] = [
                [] for _ in range(len(self.node_rows))
            ]
            for edge_index, (left, right) in enumerate(self.edges):
                left_node, right_node = int(left), int(right)
                left_row, left_col = (
                    int(self.node_rows[left_node]),
                    int(self.node_cols[left_node]),
                )
                right_row, right_col = (
                    int(self.node_rows[right_node]),
                    int(self.node_cols[right_node]),
                )
                left_action = {
                    (-1, 0): Action.UP,
                    (1, 0): Action.DOWN,
                    (0, -1): Action.LEFT,
                    (0, 1): Action.RIGHT,
                }[(right_row - left_row, right_col - left_col)]
                right_action = {
                    (-1, 0): Action.UP,
                    (1, 0): Action.DOWN,
                    (0, -1): Action.LEFT,
                    (0, 1): Action.RIGHT,
                }[(left_row - right_row, left_col - right_col)]
                length = float(self.edge_lengths_m[edge_index])
                indexed[left_node].append((right_node, left_action, length))
                indexed[right_node].append((left_node, right_action, length))
            index = tuple(
                tuple(sorted(items, key=lambda item: (int(item[1]), item[0])))
                for items in indexed
            )
            object.__setattr__(self, "_neighbor_index", index)
        return list(index[node])
