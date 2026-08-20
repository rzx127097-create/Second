from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from problem2.config import G2Config
from problem2.domain import Action, Event, UavState, VehicleMode, VehicleState
from problem2.road.models import RasterRoadGraph


class IllegalActionError(ValueError):
    """Raised before state mutation when an action is not in the stored mask."""


def masked_probabilities(logits: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = np.asarray(logits, dtype=np.float64)
    legal = np.asarray(mask, dtype=np.bool_)
    if values.ndim != 1 or legal.shape != values.shape:
        raise ValueError("logits and mask must be equal-length vectors")
    if not np.all(np.isfinite(values)):
        raise ValueError("logits must be finite")
    if not np.any(legal):
        raise ValueError("action mask must allow at least one action")
    probabilities = np.zeros_like(values)
    shifted = values[legal] - np.max(values[legal])
    weights = np.exp(shifted)
    probabilities[legal] = weights / weights.sum()
    return probabilities


def uav_action_mask(
    state: UavState,
    config: G2Config,
    aoi_bounds_m: tuple[float, float, float, float],
) -> np.ndarray:
    mask = np.zeros(6, dtype=np.bool_)
    mask[int(Action.STAY)] = True
    if state.service_locked:
        return mask
    min_x, min_y, max_x, max_y = aoi_bounds_m
    tolerance = config.tolerance
    mask[int(Action.UP)] = state.y_m < max_y - tolerance
    mask[int(Action.DOWN)] = state.y_m > min_y + tolerance
    mask[int(Action.LEFT)] = state.x_m > min_x + tolerance
    mask[int(Action.RIGHT)] = state.x_m < max_x - tolerance
    mask[int(Action.SPRAY)] = state.pesticide_l > tolerance
    return mask


def _motion_event(
    step: int,
    entity_id: str,
    kind: str,
    action: Action,
    distance_m: float,
    unused_distance_m: float = 0.0,
) -> Event:
    return Event(
        step=step,
        phase="action",
        kind=kind,
        entity_id=entity_id,
        payload=(
            ("action", action.name),
            ("distance_m", float(distance_m)),
            ("unused_distance_m", float(unused_distance_m)),
        ),
    )


def move_uav(
    state: UavState,
    action: Action,
    config: G2Config,
    aoi_bounds_m: tuple[float, float, float, float],
    *,
    step: int = 0,
) -> tuple[UavState, Event]:
    try:
        action = Action(action)
    except ValueError as exc:
        raise IllegalActionError(f"unknown UAV action {action!r}") from exc
    mask = uav_action_mask(state, config, aoi_bounds_m)
    if not bool(mask[int(action)]):
        raise IllegalActionError(f"UAV {state.uav_id} action {action.name} is illegal")
    if action in (Action.STAY, Action.SPRAY):
        return state, _motion_event(step, state.uav_id, "uav_motion", action, 0.0)
    dx, dy = {
        Action.UP: (0.0, config.uav_speed_mps * config.dt_s),
        Action.DOWN: (0.0, -config.uav_speed_mps * config.dt_s),
        Action.LEFT: (-config.uav_speed_mps * config.dt_s, 0.0),
        Action.RIGHT: (config.uav_speed_mps * config.dt_s, 0.0),
    }[action]
    min_x, min_y, max_x, max_y = aoi_bounds_m
    x_m = min(max_x, max(min_x, state.x_m + dx))
    y_m = min(max_y, max(min_y, state.y_m + dy))
    distance = math.hypot(x_m - state.x_m, y_m - state.y_m)
    moved = replace(state, x_m=x_m, y_m=y_m)
    return moved, _motion_event(step, state.uav_id, "uav_motion", action, distance)


def vehicle_action_mask(state: VehicleState, graph: RasterRoadGraph) -> np.ndarray:
    mask = np.zeros(5, dtype=np.bool_)
    if state.mode is VehicleMode.SERVING:
        mask[int(Action.STAY)] = True
        return mask
    if state.mode is VehicleMode.TRANSIT:
        if state.target_node is None or state.direction is None:
            raise ValueError("transit vehicle must have target_node and direction")
        mask[int(state.direction)] = True
        return mask
    row = int(graph.node_rows[state.current_node])
    col = int(graph.node_cols[state.current_node])
    return graph.action_mask[row, col].copy()


def _edge_to_action(
    graph: RasterRoadGraph, node: int, action: Action
) -> tuple[int, float]:
    matches = [
        (neighbor, length)
        for neighbor, neighbor_action, length in graph.neighbors(node)
        if neighbor_action is action
    ]
    if len(matches) != 1:
        raise IllegalActionError(
            f"vehicle action {action.name} has {len(matches)} matching road edges"
        )
    return matches[0]


def move_vehicle(
    state: VehicleState,
    action: Action,
    graph: RasterRoadGraph,
    distance_budget_m: float,
    *,
    step: int = 0,
) -> tuple[VehicleState, Event]:
    if not math.isfinite(distance_budget_m) or distance_budget_m < 0.0:
        raise ValueError("distance_budget_m must be finite and nonnegative")
    try:
        action = Action(action)
    except ValueError as exc:
        raise IllegalActionError(f"unknown vehicle action {action!r}") from exc
    if action is Action.SPRAY:
        raise IllegalActionError("vehicle action SPRAY is illegal")
    mask = vehicle_action_mask(state, graph)
    if not bool(mask[int(action)]):
        raise IllegalActionError(
            f"vehicle {state.vehicle_id} action {action.name} is illegal"
        )
    if action is Action.STAY:
        return state, _motion_event(step, state.vehicle_id, "vehicle_motion", action, 0.0)

    current = state.current_node
    target = state.target_node
    direction = state.direction
    progress = state.edge_progress_m
    x_m, y_m = state.x_m, state.y_m
    remaining = distance_budget_m
    travelled = 0.0
    mode = state.mode
    while remaining > 0.0:
        if target is None:
            target, _ = _edge_to_action(graph, current, action)
            direction = action
            progress = 0.0
            mode = VehicleMode.TRANSIT
        edge_length = next(
            length
            for neighbor, _, length in graph.neighbors(current)
            if neighbor == target
        )
        available = edge_length - progress
        delta = min(remaining, available)
        progress += delta
        travelled += delta
        remaining -= delta
        fraction = progress / edge_length
        x_m = float(graph.node_x_m[current]) + fraction * (
            float(graph.node_x_m[target]) - float(graph.node_x_m[current])
        )
        y_m = float(graph.node_y_m[current]) + fraction * (
            float(graph.node_y_m[target]) - float(graph.node_y_m[current])
        )
        if progress < edge_length - 1e-12:
            break

        previous = current
        current = target
        x_m, y_m = float(graph.node_x_m[current]), float(graph.node_y_m[current])
        target = None
        direction = None
        progress = 0.0
        mode = VehicleMode.IDLE
        if remaining <= 1e-12:
            remaining = 0.0
            break
        onward = [item for item in graph.neighbors(current) if item[0] != previous]
        if len(onward) != 1 or onward[0][1] is not action:
            break
        target = onward[0][0]
        direction = action
        mode = VehicleMode.TRANSIT

    moved = replace(
        state,
        current_node=current,
        target_node=target,
        direction=direction,
        edge_progress_m=progress,
        x_m=x_m,
        y_m=y_m,
        route_distance_m=state.route_distance_m + travelled,
        mode=mode,
    )
    return moved, _motion_event(
        step,
        state.vehicle_id,
        "vehicle_motion",
        action,
        travelled,
        remaining,
    )
