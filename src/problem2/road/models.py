from __future__ import annotations

from dataclasses import dataclass
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

    def node_index(self, row: int, col: int) -> int:
        matches = np.flatnonzero((self.node_rows == row) & (self.node_cols == col))
        if len(matches) != 1:
            raise KeyError(f"road cell ({row}, {col}) is not a unique node")
        return int(matches[0])

    def neighbors(self, node: int) -> list[tuple[int, Action, float]]:
        row, col = int(self.node_rows[node]), int(self.node_cols[node])
        results: list[tuple[int, Action, float]] = []
        for edge_index, (left, right) in enumerate(self.edges):
            if int(left) == node:
                neighbor = int(right)
            elif int(right) == node:
                neighbor = int(left)
            else:
                continue
            dr = int(self.node_rows[neighbor]) - row
            dc = int(self.node_cols[neighbor]) - col
            action = {
                (-1, 0): Action.UP,
                (1, 0): Action.DOWN,
                (0, -1): Action.LEFT,
                (0, 1): Action.RIGHT,
            }[(dr, dc)]
            results.append((neighbor, action, float(self.edge_lengths_m[edge_index])))
        return sorted(results, key=lambda item: (int(item[1]), item[0]))
