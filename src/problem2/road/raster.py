from __future__ import annotations

import math

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point

from problem2.config import ScaleConfig
from problem2.domain import Action
from problem2.road.models import (
    ProjectedRoadSource,
    RasterRoadGraph,
    RepairRecord,
)


Cell = tuple[int, int]


def _cell_for_point(
    point: tuple[float, float],
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
) -> Cell:
    x_m, y_m = point
    min_x, min_y, max_x, max_y = bounds
    height, width = shape
    col = min(width - 1, max(0, int(math.floor((x_m - min_x) / (max_x - min_x) * width))))
    row = min(height - 1, max(0, int(math.floor((max_y - y_m) / (max_y - min_y) * height))))
    return row, col


def _cell_center(
    cell: Cell,
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
) -> tuple[float, float]:
    row, col = cell
    min_x, min_y, max_x, max_y = bounds
    height, width = shape
    cell_width = (max_x - min_x) / width
    cell_height = (max_y - min_y) / height
    return (
        min_x + (col + 0.5) * cell_width,
        max_y - (row + 0.5) * cell_height,
    )


def _densified_points(
    coords: tuple[tuple[float, float], ...], max_segment_m: float
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for start, end in zip(coords, coords[1:]):
        distance = math.hypot(end[0] - start[0], end[1] - start[1])
        subdivisions = max(1, int(math.ceil(distance / max_segment_m)))
        for index in range(subdivisions):
            fraction = index / subdivisions
            point = (
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            )
            if not points or point != points[-1]:
                points.append(point)
    points.append(coords[-1])
    return points


def _ordered_cells_for_edge(
    source_edge_id: str,
    points: list[tuple[float, float]],
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
    cell_width_m: float,
    cell_height_m: float,
) -> tuple[list[Cell], list[RepairRecord]]:
    ordered: list[Cell] = []
    repairs: list[RepairRecord] = []
    last_point = points[0]
    for point in points:
        target = _cell_for_point(point, bounds, shape)
        if not ordered:
            ordered.append(target)
            last_point = point
            continue
        current = ordered[-1]
        if target == current:
            last_point = point
            continue
        segment = LineString([last_point, point])
        while current != target:
            row_delta = target[0] - current[0]
            col_delta = target[1] - current[1]
            row_step = 0 if row_delta == 0 else (1 if row_delta > 0 else -1)
            col_step = 0 if col_delta == 0 else (1 if col_delta > 0 else -1)
            if row_step and col_step:
                candidates = [
                    (current[0] + row_step, current[1]),
                    (current[0], current[1] + col_step),
                ]
                inserted = min(
                    candidates,
                    key=lambda cell: (
                        segment.distance(Point(_cell_center(cell, bounds, shape))),
                        cell,
                    ),
                )
                metric_length = (
                    cell_height_m if inserted[0] != current[0] else cell_width_m
                )
                repairs.append(
                    RepairRecord(
                        source_edge_id=source_edge_id,
                        from_cell=current,
                        inserted_cell=inserted,
                        to_cell=target,
                        metric_length_m=metric_length,
                        reason="same_source_edge_diagonal_bridge",
                    )
                )
                current = inserted
            elif row_step:
                current = (current[0] + row_step, current[1])
            else:
                current = (current[0], current[1] + col_step)
            if current != ordered[-1]:
                ordered.append(current)
        last_point = point
    return ordered, repairs


def rasterize_road_source(
    source: ProjectedRoadSource,
    scale: ScaleConfig,
    max_segment_m: float = 5.0,
) -> RasterRoadGraph:
    if not math.isfinite(max_segment_m) or max_segment_m <= 0.0:
        raise ValueError("max_segment_m must be finite and positive")
    height, width = scale.grid_shape
    min_x, min_y, max_x, max_y = source.aoi_bounds_m
    cell_width_m = (max_x - min_x) / width
    cell_height_m = (max_y - min_y) / height

    source_edge_to_cells: dict[str, tuple[Cell, ...]] = {}
    repairs: list[RepairRecord] = []
    road_cells: set[Cell] = set()
    cell_edges: set[tuple[Cell, Cell]] = set()
    for source_edge in sorted(source.edges, key=lambda edge: edge.source_id):
        points = _densified_points(source_edge.coords_m, max_segment_m)
        ordered, edge_repairs = _ordered_cells_for_edge(
            source_edge.source_id,
            points,
            source.aoi_bounds_m,
            scale.grid_shape,
            cell_width_m,
            cell_height_m,
        )
        deduplicated = tuple(
            cell for index, cell in enumerate(ordered) if index == 0 or cell != ordered[index - 1]
        )
        source_edge_to_cells[source_edge.source_id] = deduplicated
        repairs.extend(edge_repairs)
        road_cells.update(deduplicated)
        for left, right in zip(deduplicated, deduplicated[1:]):
            if abs(left[0] - right[0]) + abs(left[1] - right[1]) != 1:
                raise ValueError(
                    f"source edge {source_edge.source_id} produced a non-four-connected edge"
                )
            cell_edges.add(tuple(sorted((left, right))))

    if not road_cells:
        raise ValueError("rasterization produced no road cells")
    canonical_cells = sorted(road_cells)
    cell_to_index = {cell: index for index, cell in enumerate(canonical_cells)}
    canonical_cell_edges = sorted(cell_edges)
    edges = np.asarray(
        [(cell_to_index[left], cell_to_index[right]) for left, right in canonical_cell_edges],
        dtype=np.int32,
    ).reshape((-1, 2))

    topology = nx.Graph()
    topology.add_nodes_from(range(len(canonical_cells)))
    topology.add_edges_from((int(left), int(right)) for left, right in edges)
    component_sets = sorted(
        (set(component) for component in nx.connected_components(topology)),
        key=lambda component: min(canonical_cells[node] for node in component),
    )
    component_sizes = tuple(len(component) for component in component_sets)
    primary_component_id = min(
        range(len(component_sets)),
        key=lambda index: (
            -len(component_sets[index]),
            min(canonical_cells[node] for node in component_sets[index]),
        ),
    )

    road_mask = np.zeros(scale.grid_shape, dtype=np.bool_)
    action_mask = np.zeros((*scale.grid_shape, 5), dtype=np.bool_)
    component_id = np.full(scale.grid_shape, -1, dtype=np.int32)
    for component_index, component in enumerate(component_sets):
        for node in component:
            row, col = canonical_cells[node]
            road_mask[row, col] = True
            action_mask[row, col, int(Action.STAY)] = True
            component_id[row, col] = component_index

    edge_lengths: list[float] = []
    for left, right in edges:
        left_cell = canonical_cells[int(left)]
        right_cell = canonical_cells[int(right)]
        dr = right_cell[0] - left_cell[0]
        dc = right_cell[1] - left_cell[1]
        if abs(dr) + abs(dc) != 1:
            raise ValueError("runtime road graph is not four-connected")
        action_left = {
            (-1, 0): Action.UP,
            (1, 0): Action.DOWN,
            (0, -1): Action.LEFT,
            (0, 1): Action.RIGHT,
        }[(dr, dc)]
        action_right = {
            Action.UP: Action.DOWN,
            Action.DOWN: Action.UP,
            Action.LEFT: Action.RIGHT,
            Action.RIGHT: Action.LEFT,
        }[action_left]
        action_mask[left_cell[0], left_cell[1], int(action_left)] = True
        action_mask[right_cell[0], right_cell[1], int(action_right)] = True
        edge_lengths.append(cell_height_m if dr else cell_width_m)

    source_node_to_cell = {
        node_id: _cell_for_point((node.x_m, node.y_m), source.aoi_bounds_m, scale.grid_shape)
        for node_id, node in sorted(source.nodes.items())
    }
    node_rows = np.asarray([cell[0] for cell in canonical_cells], dtype=np.int32)
    node_cols = np.asarray([cell[1] for cell in canonical_cells], dtype=np.int32)
    centers = [_cell_center(cell, source.aoi_bounds_m, scale.grid_shape) for cell in canonical_cells]
    node_x_m = np.asarray([center[0] for center in centers], dtype=np.float64)
    node_y_m = np.asarray([center[1] for center in centers], dtype=np.float64)
    for array in (
        road_mask,
        action_mask,
        component_id,
        node_rows,
        node_cols,
        node_x_m,
        node_y_m,
        edges,
    ):
        array.flags.writeable = False
    edge_lengths_m = np.asarray(edge_lengths, dtype=np.float64)
    edge_lengths_m.flags.writeable = False
    return RasterRoadGraph(
        scale_id=scale.scale_id,
        grid_shape=scale.grid_shape,
        aoi_bounds_m=source.aoi_bounds_m,
        cell_width_m=cell_width_m,
        cell_height_m=cell_height_m,
        road_mask=road_mask,
        action_mask=action_mask,
        component_id=component_id,
        node_rows=node_rows,
        node_cols=node_cols,
        node_x_m=node_x_m,
        node_y_m=node_y_m,
        edges=edges,
        edge_lengths_m=edge_lengths_m,
        component_sizes=component_sizes,
        primary_component_id=primary_component_id,
        source_node_to_cell=source_node_to_cell,
        source_edge_to_cells=source_edge_to_cells,
        repairs=tuple(repairs),
    )
