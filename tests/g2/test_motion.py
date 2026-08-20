from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from problem2.config import load_g2_config
from problem2.domain import Action, UavState, VehicleMode, VehicleState
from problem2.dynamics.motion import (
    IllegalActionError,
    masked_probabilities,
    move_uav,
    move_vehicle,
    uav_action_mask,
    vehicle_action_mask,
)
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")


def _vehicle_at_node(graph, node: int = 0) -> VehicleState:
    return VehicleState(
        "v0",
        current_node=node,
        x_m=float(graph.node_x_m[node]),
        y_m=float(graph.node_y_m[node]),
        inventory_l=20.0,
    )


@pytest.mark.parametrize("scale_id", [scale.scale_id for scale in CONFIG.scales])
def test_uav_metric_displacement_is_scale_independent(scale_id: str) -> None:
    state = UavState("u0", x_m=250.0, y_m=150.0, pesticide_l=1.08)

    moved, event = move_uav(state, Action.RIGHT, CONFIG, (0.0, 0.0, 500.0, 300.0))

    assert moved.x_m - state.x_m == pytest.approx(5.0)
    assert dict(event.payload)["distance_m"] == pytest.approx(5.0)


def test_uav_boundary_clips_actual_distance_and_masks_outward_action() -> None:
    state = UavState("u0", x_m=498.0, y_m=150.0, pesticide_l=1.08)

    moved, event = move_uav(state, Action.RIGHT, CONFIG, (0.0, 0.0, 500.0, 300.0))

    assert moved.x_m == pytest.approx(500.0)
    assert dict(event.payload)["distance_m"] == pytest.approx(2.0)
    assert not uav_action_mask(moved, CONFIG, (0.0, 0.0, 500.0, 300.0))[Action.RIGHT]


def test_vehicle_carries_unfinished_edge_progress_across_steps() -> None:
    graph = make_raster_graph([(0, 0), (0, 1), (0, 2)], [(0, 1), (1, 2)])
    state = _vehicle_at_node(graph)

    first, _ = move_vehicle(state, Action.RIGHT, graph, distance_budget_m=8.0)
    second, event = move_vehicle(first, Action.RIGHT, graph, distance_budget_m=8.0)

    assert first.mode is VehicleMode.TRANSIT
    assert first.edge_progress_m == pytest.approx(8.0)
    assert second.current_node == 1
    assert second.target_node == 2
    assert second.edge_progress_m == pytest.approx(6.0)
    assert second.route_distance_m == pytest.approx(16.0)
    assert dict(event.payload)["distance_m"] == pytest.approx(8.0)


def test_vehicle_discards_unused_step_distance_at_branch() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 2), (1, 3)],
    )
    state = _vehicle_at_node(graph)

    moved, event = move_vehicle(state, Action.RIGHT, graph, distance_budget_m=18.0)

    assert moved.mode is VehicleMode.IDLE
    assert moved.current_node == 1
    assert moved.target_node is None
    assert moved.route_distance_m == pytest.approx(10.0)
    assert dict(event.payload)["unused_distance_m"] == pytest.approx(8.0)


def test_vehicle_service_lock_allows_only_stay() -> None:
    graph = make_raster_graph([(0, 0), (0, 1)], [(0, 1)])
    serving = replace(_vehicle_at_node(graph), mode=VehicleMode.SERVING)

    assert vehicle_action_mask(serving, graph).tolist() == [True, False, False, False, False]
    stayed, event = move_vehicle(serving, Action.STAY, graph, 8.0)
    assert stayed == serving
    assert dict(event.payload)["distance_m"] == 0.0


def test_illegal_action_has_zero_probability_and_cannot_change_state() -> None:
    graph = make_raster_graph([(0, 0), (0, 1)], [(0, 1)])
    state = _vehicle_at_node(graph)
    mask = vehicle_action_mask(state, graph)
    probabilities = masked_probabilities(np.zeros(5), mask)

    assert probabilities[Action.UP] == 0.0
    assert probabilities[Action.RIGHT] == pytest.approx(0.5)
    with pytest.raises(IllegalActionError, match="UP"):
        move_vehicle(state, Action.UP, graph, 8.0)
    assert state == _vehicle_at_node(graph)
