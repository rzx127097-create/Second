from __future__ import annotations

import numpy as np

from problem2.domain import Action
from problem2.road.models import RasterRoadGraph


def make_raster_graph(
    cells: list[tuple[int, int]],
    edge_pairs: list[tuple[int, int]],
    *,
    shape: tuple[int, int] = (4, 4),
    cell_width_m: float = 10.0,
    cell_height_m: float = 10.0,
    component_ids: list[int] | None = None,
) -> RasterRoadGraph:
    road_mask = np.zeros(shape, dtype=np.bool_)
    action_mask = np.zeros((*shape, 5), dtype=np.bool_)
    component_id = np.full(shape, -1, dtype=np.int32)
    component_ids = component_ids or [0] * len(cells)
    for node, ((row, col), component) in enumerate(zip(cells, component_ids)):
        road_mask[row, col] = True
        action_mask[row, col, int(Action.STAY)] = True
        component_id[row, col] = component
    edge_lengths: list[float] = []
    for left, right in edge_pairs:
        left_cell, right_cell = cells[left], cells[right]
        dr = right_cell[0] - left_cell[0]
        dc = right_cell[1] - left_cell[1]
        left_action = {
            (-1, 0): Action.UP,
            (1, 0): Action.DOWN,
            (0, -1): Action.LEFT,
            (0, 1): Action.RIGHT,
        }[(dr, dc)]
        right_action = {
            Action.UP: Action.DOWN,
            Action.DOWN: Action.UP,
            Action.LEFT: Action.RIGHT,
            Action.RIGHT: Action.LEFT,
        }[left_action]
        action_mask[left_cell[0], left_cell[1], int(left_action)] = True
        action_mask[right_cell[0], right_cell[1], int(right_action)] = True
        edge_lengths.append(cell_height_m if dr else cell_width_m)
    rows = np.asarray([cell[0] for cell in cells], dtype=np.int32)
    cols = np.asarray([cell[1] for cell in cells], dtype=np.int32)
    x_values = np.asarray([(col + 0.5) * cell_width_m for _, col in cells])
    max_y = shape[0] * cell_height_m
    y_values = np.asarray([max_y - (row + 0.5) * cell_height_m for row, _ in cells])
    sizes = tuple(component_ids.count(index) for index in sorted(set(component_ids)))
    return RasterRoadGraph(
        scale_id="fixture",
        grid_shape=shape,
        aoi_bounds_m=(0.0, 0.0, shape[1] * cell_width_m, max_y),
        cell_width_m=cell_width_m,
        cell_height_m=cell_height_m,
        road_mask=road_mask,
        action_mask=action_mask,
        component_id=component_id,
        node_rows=rows,
        node_cols=cols,
        node_x_m=x_values,
        node_y_m=y_values,
        edges=np.asarray(edge_pairs, dtype=np.int32).reshape((-1, 2)),
        edge_lengths_m=np.asarray(edge_lengths, dtype=np.float64),
        component_sizes=sizes,
        primary_component_id=0,
        source_node_to_cell={},
        source_edge_to_cells={},
        repairs=(),
    )
