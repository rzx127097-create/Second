from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from problem2.config import load_g2_config
from problem2.domain import (
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleMode,
    VehicleState,
)
from problem2.resources.ledger import assert_conserved, new_ledger
from problem2.service.state_machine import (
    ServiceStateError,
    advance_service,
    cancel_terminal_requests,
    create_request,
    reserve_request,
    select_serviceable_request,
    should_request,
    start_service,
)
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
GRAPH = make_raster_graph([(0, 0), (0, 1)], [(0, 1)])


def _uav(uav_id: str, pesticide_l: float, x_m: float = 0.0) -> UavState:
    return UavState(
        uav_id,
        x_m=float(GRAPH.node_x_m[0]) + x_m,
        y_m=float(GRAPH.node_y_m[0]),
        pesticide_l=pesticide_l,
    )


def _vehicle(inventory_l: float = 20.0, x_m: float = 0.0) -> VehicleState:
    return VehicleState(
        "v0",
        0,
        x_m=float(GRAPH.node_x_m[0]) + x_m,
        y_m=float(GRAPH.node_y_m[0]),
        inventory_l=inventory_l,
    )


def _pending(uav_id: str, step: int) -> ServiceRequest:
    return ServiceRequest(f"req-{step}-{uav_id}", uav_id, step, requested_l=1.0)


def test_request_threshold_includes_equality_and_zero_flow_never_triggers() -> None:
    assert should_request(
        pesticide_l=0.2,
        spray_flow_lps=0.02,
        estimated_time_to_service_s=0.0,
        safety_margin_s=10.0,
    )
    assert not should_request(0.2, 0.0, float("inf"), 10.0)


def test_create_request_is_deterministic_and_rejects_duplicate_active_request() -> None:
    uav = _uav("u0", 0.2)

    updated, request, event = create_request(
        uav, step=4, estimated_time_to_service_s=0.0, config=CONFIG
    )

    assert request.request_id == "req-000004-u0"
    assert request.requested_l == pytest.approx(0.88)
    assert updated.active_request_id == request.request_id
    assert event.kind == "request_created"
    with pytest.raises(ServiceStateError, match="active request"):
        create_request(updated, 5, 0.0, CONFIG)


def test_same_step_fifo_tie_breaks_by_uav_id() -> None:
    requests = [_pending("u2", 4), _pending("u1", 4)]
    uavs = {"u1": _uav("u1", 0.1), "u2": _uav("u2", 0.1)}

    chosen = select_serviceable_request(
        requests,
        _vehicle(),
        uavs,
        rendezvous_radius_m=15.0,
        graph=GRAPH,
        tolerance=CONFIG.tolerance,
    )

    assert chosen is not None
    assert chosen.uav_id == "u1"


def test_old_unreachable_request_does_not_block_new_serviceable_request() -> None:
    requests = [_pending("u0", 1), _pending("u1", 2)]
    uavs = {"u0": _uav("u0", 0.1, x_m=100.0), "u1": _uav("u1", 0.1)}

    chosen = select_serviceable_request(
        requests,
        _vehicle(),
        uavs,
        rendezvous_radius_m=15.0,
        graph=GRAPH,
        tolerance=CONFIG.tolerance,
    )

    assert chosen is not None
    assert chosen.uav_id == "u1"


def test_busy_or_depleted_vehicle_selects_no_request() -> None:
    request = _pending("u0", 1)
    uavs = {"u0": _uav("u0", 0.1)}

    assert (
        select_serviceable_request(
            [request],
            replace(_vehicle(), mode=VehicleMode.SERVING),
            uavs,
            15.0,
            GRAPH,
            CONFIG.tolerance,
        )
        is None
    )
    assert (
        select_serviceable_request(
            [request], _vehicle(0.0), uavs, 15.0, GRAPH, CONFIG.tolerance
        )
        is None
    )


def test_inventory_depleted_flag_rejects_tiny_positive_residual() -> None:
    request = _pending("u0", 1)
    uavs = {"u0": _uav("u0", 0.1)}
    depleted = replace(_vehicle(1e-12), inventory_depleted=True)

    assert (
        select_serviceable_request(
            [request], depleted, uavs, 15.0, GRAPH, CONFIG.tolerance
        )
        is None
    )


def test_reservation_is_explicit_and_pending_cannot_start_service() -> None:
    pending = _pending("u0", 1)
    vehicle = _vehicle(1.0)
    uav = _uav("u0", 0.08)

    with pytest.raises(ServiceStateError, match="reserved request"):
        start_service(pending, vehicle, uav, CONFIG, step=1, graph=GRAPH)

    reserved, event = reserve_request(pending, vehicle, step=1)

    assert reserved.status is RequestStatus.RESERVED
    assert reserved.reserved_vehicle_id == vehicle.vehicle_id
    assert event.kind == "request_reserved"


def test_service_selection_rejects_vehicle_node_coordinate_mismatch() -> None:
    invalid = replace(_vehicle(), x_m=float(GRAPH.node_x_m[0]) + 1.0)

    with pytest.raises(ServiceStateError, match="node coordinate"):
        select_serviceable_request(
            [_pending("u0", 1)],
            invalid,
            {"u0": _uav("u0", 0.1)},
            15.0,
            GRAPH,
            CONFIG.tolerance,
        )


def test_service_start_rejects_vehicle_node_outside_graph() -> None:
    vehicle = _vehicle(1.0)
    request, _ = reserve_request(_pending("u0", 1), vehicle, step=1)
    invalid = replace(vehicle, current_node=len(GRAPH.node_rows))

    with pytest.raises(ServiceStateError, match="outside road graph"):
        start_service(
            request, invalid, _uav("u0", 0.08), CONFIG, step=1, graph=GRAPH
        )


def test_transfer_occurs_only_on_atomic_completion_boundary() -> None:
    uav = _uav("u0", 0.08)
    request = _pending("u0", 1)
    vehicle = _vehicle(1.0)
    ledger = new_ledger([uav], vehicle.inventory_l)
    request, reserved_event = reserve_request(request, vehicle, step=1)
    request, vehicle, uav, started_event = start_service(
        request, vehicle, uav, CONFIG, step=1, graph=GRAPH
    )

    assert [reserved_event.kind, started_event.kind] == [
        "request_reserved",
        "service_started",
    ]
    assert vehicle.service_steps_required == 25
    for step in range(1, 25):
        request, vehicle, uav, ledger, events = advance_service(
            request, vehicle, uav, ledger, CONFIG, step=step
        )
        assert not any(event.kind == "transfer" for event in events)
    request, vehicle, uav, ledger, events = advance_service(
        request, vehicle, uav, ledger, CONFIG, step=25
    )

    assert [event.kind for event in events][-2:] == ["transfer", "service_completed"]
    assert request.status is RequestStatus.COMPLETED
    assert vehicle.mode is VehicleMode.IDLE
    assert vehicle.inventory_l == 0.0
    assert vehicle.inventory_depleted
    assert uav.pesticide_l == pytest.approx(1.08)
    assert not uav.service_locked
    assert_conserved([uav], vehicle.inventory_l, ledger, 1e-9)


def test_terminal_before_completion_cancels_without_transfer() -> None:
    uav = _uav("u0", 0.08)
    vehicle = _vehicle(1.0)
    request, _ = reserve_request(_pending("u0", 1), vehicle, step=1)
    request, vehicle, uav, _ = start_service(
        request, vehicle, uav, CONFIG, step=1, graph=GRAPH
    )
    ledger = new_ledger([_uav("u0", 0.08)], 1.0)
    for step in range(1, 25):
        request, vehicle, uav, ledger, _ = advance_service(
            request, vehicle, uav, ledger, CONFIG, step=step
        )

    requests, vehicle, uavs, events = cancel_terminal_requests(
        [request], vehicle, {"u0": uav}, step=25
    )

    assert requests[0].status is RequestStatus.CANCELLED
    assert vehicle.inventory_l == 1.0
    assert uavs["u0"].pesticide_l == pytest.approx(0.08)
    assert [event.kind for event in events] == ["request_cancelled"]
