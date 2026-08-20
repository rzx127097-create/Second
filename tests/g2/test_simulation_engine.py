from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from problem2.config import load_g2_config
from problem2.domain import (
    Action,
    EpisodeState,
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleMode,
    VehicleState,
)
from problem2.resources.ledger import new_ledger
from problem2.simulation.engine import (
    StepTransactionError,
    build_action_masks,
    step_episode,
)
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")


def _initial_fixture() -> tuple:
    graph = make_raster_graph([(0, 0), (0, 1)], [(0, 1)])
    uav = UavState(
        "u0",
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        pesticide_l=0.02,
    )
    vehicle = VehicleState(
        "v0",
        current_node=0,
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        inventory_l=1.06,
    )
    state = EpisodeState(
        step=0,
        uavs=(uav,),
        vehicle=vehicle,
        ledger=new_ledger([uav], vehicle.inventory_l),
    )
    masks = build_action_masks(state, graph, CONFIG)
    return state, graph, masks


def test_step_emits_frozen_phase_order_and_starts_service() -> None:
    state, graph, masks = _initial_fixture()

    next_state = step_episode(
        state,
        {"u0": Action.SPRAY},
        Action.STAY,
        masks,
        graph,
        CONFIG,
        max_steps=40,
    )

    phases = [event.phase for event in next_state.last_step_events]
    assert phases == [
        "action",
        "action",
        "spray",
        "request",
        "reserve",
        "service",
        "service",
        "environment",
        "conservation",
    ]
    assert next_state.requests[0].status is RequestStatus.SERVING
    assert next_state.vehicle.mode is VehicleMode.SERVING
    assert next_state.vehicle.service_steps_elapsed == 1


def test_bad_stored_mask_fails_without_partial_state() -> None:
    state, graph, masks = _initial_fixture()
    bad_masks = replace(masks, vehicle=(False, False, False, False, False))

    with pytest.raises(StepTransactionError, match="stored vehicle mask"):
        step_episode(
            state,
            {"u0": Action.SPRAY},
            Action.STAY,
            bad_masks,
            graph,
            CONFIG,
            max_steps=40,
        )

    assert state.step == 0
    assert state.uavs[0].pesticide_l == 0.02
    assert state.requests == ()


def _serving_fixture(required_steps: int) -> tuple:
    graph = make_raster_graph([(0, 0), (0, 1)], [(0, 1)])
    request = ServiceRequest(
        "req-000000-u0",
        "u0",
        0,
        requested_l=1.0,
        status=RequestStatus.SERVING,
        reserved_vehicle_id="v0",
    )
    uav = UavState(
        "u0",
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        pesticide_l=0.08,
        active_request_id=request.request_id,
        service_locked=True,
    )
    vehicle = VehicleState(
        "v0",
        0,
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        inventory_l=1.0,
        mode=VehicleMode.SERVING,
        active_request_id=request.request_id,
        service_steps_elapsed=0,
        service_steps_required=required_steps,
        planned_transfer_l=1.0,
    )
    state = EpisodeState(
        0,
        (uav,),
        vehicle,
        (request,),
        new_ledger([replace(uav, active_request_id=None, service_locked=False)], 1.0),
    )
    return state, graph, build_action_masks(state, graph, CONFIG)


def test_final_service_boundary_transfers_before_episode_termination() -> None:
    state, graph, masks = _serving_fixture(required_steps=1)

    final = step_episode(
        state,
        {"u0": Action.STAY},
        Action.STAY,
        masks,
        graph,
        CONFIG,
        max_steps=1,
    )

    kinds = [event.kind for event in final.last_step_events]
    assert kinds.index("transfer") < kinds.index("episode_terminated")
    assert "request_cancelled" not in kinds
    assert final.requests[0].status is RequestStatus.COMPLETED
    assert final.uavs[0].pesticide_l == pytest.approx(1.08)


def test_terminal_before_completion_cancels_without_transfer() -> None:
    state, graph, masks = _serving_fixture(required_steps=2)

    final = step_episode(
        state,
        {"u0": Action.STAY},
        Action.STAY,
        masks,
        graph,
        CONFIG,
        max_steps=1,
    )

    kinds = [event.kind for event in final.last_step_events]
    assert "transfer" not in kinds
    assert kinds.index("request_cancelled") < kinds.index("episode_terminated")
    assert final.requests[0].status is RequestStatus.CANCELLED
    assert final.vehicle.inventory_l == 1.0
