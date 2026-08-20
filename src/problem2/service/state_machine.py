from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable, Mapping

from problem2.config import G2Config
from problem2.domain import (
    Event,
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleMode,
    VehicleState,
)
from problem2.resources.ledger import (
    ResourceInvariantError,
    ResourceLedger,
    apply_transfer,
)
from problem2.dynamics.motion import validate_vehicle_road_state
from problem2.road.models import RasterRoadGraph


class ServiceStateError(ValueError):
    """Raised before an invalid request or service transition is published."""


def _finite_nonnegative(value: float, name: str, *, allow_infinity: bool = False) -> float:
    if isinstance(value, bool):
        raise ServiceStateError(f"{name} must be nonnegative")
    number = float(value)
    if math.isnan(number) or number < 0.0 or (math.isinf(number) and not allow_infinity):
        raise ServiceStateError(f"{name} must be finite and nonnegative")
    return number


def should_request(
    pesticide_l: float,
    spray_flow_lps: float,
    estimated_time_to_service_s: float,
    safety_margin_s: float,
) -> bool:
    pesticide = _finite_nonnegative(pesticide_l, "pesticide_l")
    flow = _finite_nonnegative(spray_flow_lps, "spray_flow_lps")
    margin = _finite_nonnegative(safety_margin_s, "safety_margin_s")
    if flow == 0.0:
        return False
    delay = _finite_nonnegative(
        estimated_time_to_service_s,
        "estimated_time_to_service_s",
        allow_infinity=True,
    )
    return pesticide / flow <= delay + margin


def create_request(
    uav: UavState,
    step: int,
    estimated_time_to_service_s: float,
    config: G2Config,
) -> tuple[UavState, ServiceRequest, Event]:
    if step < 0:
        raise ServiceStateError("request step must be nonnegative")
    if uav.active_request_id is not None:
        raise ServiceStateError(f"UAV {uav.uav_id} already has an active request")
    if not should_request(
        uav.pesticide_l,
        config.spray_flow_lpm / 60.0,
        estimated_time_to_service_s,
        config.request_margin_s,
    ):
        raise ServiceStateError(f"UAV {uav.uav_id} has not reached request threshold")
    requested = min(config.usable_capacity_l - uav.pesticide_l, config.service_cap_l)
    if requested <= config.tolerance:
        raise ServiceStateError(f"UAV {uav.uav_id} has no positive pesticide gap")
    request_id = f"req-{step:06d}-{uav.uav_id}"
    request = ServiceRequest(
        request_id=request_id,
        uav_id=uav.uav_id,
        created_step=step,
        requested_l=requested,
    )
    updated_uav = replace(uav, active_request_id=request_id)
    event = Event(
        step=step,
        phase="request",
        kind="request_created",
        entity_id=uav.uav_id,
        payload=(("request_id", request_id), ("requested_l", requested)),
    )
    return updated_uav, request, event


def select_serviceable_request(
    requests: Iterable[ServiceRequest],
    vehicle: VehicleState,
    uavs: Mapping[str, UavState],
    rendezvous_radius_m: float,
    graph: RasterRoadGraph,
    tolerance: float,
) -> ServiceRequest | None:
    radius = _finite_nonnegative(rendezvous_radius_m, "rendezvous_radius_m")
    try:
        validate_vehicle_road_state(vehicle, graph, tolerance)
    except ValueError as exc:
        raise ServiceStateError(str(exc)) from exc
    if (
        vehicle.mode is not VehicleMode.IDLE
        or vehicle.target_node is not None
        or vehicle.inventory_l <= 0.0
        or vehicle.inventory_depleted
        or vehicle.active_request_id is not None
    ):
        return None
    eligible: list[ServiceRequest] = []
    for request in requests:
        if request.status is not RequestStatus.PENDING or request.reserved_vehicle_id is not None:
            continue
        uav = uavs.get(request.uav_id)
        if uav is None or uav.service_locked:
            continue
        distance = math.hypot(uav.x_m - vehicle.x_m, uav.y_m - vehicle.y_m)
        if distance <= radius:
            eligible.append(request)
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda request: (request.created_step, request.uav_id, request.request_id),
    )


def reserve_request(
    request: ServiceRequest,
    vehicle: VehicleState,
    step: int,
) -> tuple[ServiceRequest, Event]:
    if request.status is not RequestStatus.PENDING:
        raise ServiceStateError("only a pending request can be reserved")
    if request.reserved_vehicle_id is not None:
        raise ServiceStateError("request is already reserved")
    if vehicle.mode is not VehicleMode.IDLE or vehicle.active_request_id is not None:
        raise ServiceStateError("vehicle is not idle for reservation")
    reserved_request = replace(
        request,
        status=RequestStatus.RESERVED,
        reserved_vehicle_id=vehicle.vehicle_id,
    )
    event = Event(
        step,
        "reserve",
        "request_reserved",
        request.request_id,
        (("uav_id", request.uav_id), ("vehicle_id", vehicle.vehicle_id)),
    )
    return reserved_request, event


def start_service(
    request: ServiceRequest,
    vehicle: VehicleState,
    uav: UavState,
    config: G2Config,
    step: int,
    graph: RasterRoadGraph,
) -> tuple[ServiceRequest, VehicleState, UavState, Event]:
    try:
        validate_vehicle_road_state(vehicle, graph, config.tolerance)
    except ValueError as exc:
        raise ServiceStateError(str(exc)) from exc
    if request.status is not RequestStatus.RESERVED:
        raise ServiceStateError("only a reserved request can start service")
    if request.reserved_vehicle_id != vehicle.vehicle_id:
        raise ServiceStateError("reserved request belongs to a different vehicle")
    if request.uav_id != uav.uav_id:
        raise ServiceStateError("request UAV does not match service UAV")
    if uav.active_request_id not in (None, request.request_id):
        raise ServiceStateError("UAV has a different active request")
    if vehicle.mode is not VehicleMode.IDLE or vehicle.active_request_id is not None:
        raise ServiceStateError("vehicle is not idle for service")
    if vehicle.target_node is not None:
        raise ServiceStateError("vehicle must be stopped at a road node")
    if vehicle.inventory_depleted:
        raise ServiceStateError("vehicle inventory is marked depleted")
    distance = math.hypot(uav.x_m - vehicle.x_m, uav.y_m - vehicle.y_m)
    if distance > config.rendezvous_radius_m:
        raise ServiceStateError("UAV is outside the rendezvous radius")
    planned = min(
        config.usable_capacity_l - uav.pesticide_l,
        config.service_cap_l,
        vehicle.inventory_l,
    )
    if planned <= config.tolerance:
        raise ServiceStateError("service has no positive transferable pesticide")
    transfer_rate_lps = config.transfer_rate_lpm / 60.0
    required_steps = int(
        math.ceil((config.setup_time_s + planned / transfer_rate_lps) / config.dt_s)
    )
    serving_request = replace(
        request,
        status=RequestStatus.SERVING,
    )
    serving_vehicle = replace(
        vehicle,
        mode=VehicleMode.SERVING,
        active_request_id=request.request_id,
        service_steps_elapsed=0,
        service_steps_required=required_steps,
        planned_transfer_l=planned,
    )
    serving_uav = replace(
        uav, active_request_id=request.request_id, service_locked=True
    )
    started = Event(
        step,
        "service",
        "service_started",
        request.request_id,
        (("planned_transfer_l", planned), ("required_steps", required_steps)),
    )
    return serving_request, serving_vehicle, serving_uav, started


def advance_service(
    request: ServiceRequest,
    vehicle: VehicleState,
    uav: UavState,
    ledger: ResourceLedger,
    config: G2Config,
    step: int,
) -> tuple[ServiceRequest, VehicleState, UavState, ResourceLedger, tuple[Event, ...]]:
    if request.status is not RequestStatus.SERVING:
        raise ServiceStateError("request is not serving")
    if vehicle.mode is not VehicleMode.SERVING:
        raise ServiceStateError("vehicle is not serving")
    if vehicle.active_request_id != request.request_id or uav.active_request_id != request.request_id:
        raise ServiceStateError("service lock ownership is inconsistent")
    elapsed = vehicle.service_steps_elapsed + 1
    if elapsed < vehicle.service_steps_required:
        advanced_vehicle = replace(vehicle, service_steps_elapsed=elapsed)
        event = Event(
            step,
            "service",
            "service_advanced",
            request.request_id,
            (("elapsed_steps", elapsed), ("required_steps", vehicle.service_steps_required)),
        )
        return request, advanced_vehicle, uav, ledger, (event,)

    try:
        filled_uav, inventory, updated_ledger, transfer_event = apply_transfer(
            uav,
            vehicle.inventory_l,
            ledger,
            config.service_cap_l,
            config.usable_capacity_l,
            step=step,
        )
    except ResourceInvariantError as exc:
        raise ServiceStateError(f"service transfer failed: {exc}") from exc
    actual = float(dict(transfer_event.payload)["delta_l"])
    if abs(actual - vehicle.planned_transfer_l) > config.tolerance:
        raise ServiceStateError(
            "completion transfer differs from locked plan: "
            f"planned {vehicle.planned_transfer_l}, actual {actual}"
        )
    completed_request = replace(request, status=RequestStatus.COMPLETED)
    completed_uav = replace(
        filled_uav, active_request_id=None, service_locked=False
    )
    completed_vehicle = replace(
        vehicle,
        inventory_l=inventory,
        inventory_depleted=inventory <= config.tolerance,
        mode=VehicleMode.IDLE,
        active_request_id=None,
        service_steps_elapsed=0,
        service_steps_required=0,
        planned_transfer_l=0.0,
    )
    completed_event = Event(
        step,
        "service",
        "service_completed",
        request.request_id,
        (("transferred_l", actual),),
    )
    return (
        completed_request,
        completed_vehicle,
        completed_uav,
        updated_ledger,
        (transfer_event, completed_event),
    )


def cancel_terminal_requests(
    requests: Iterable[ServiceRequest],
    vehicle: VehicleState,
    uavs: Mapping[str, UavState],
    step: int,
) -> tuple[tuple[ServiceRequest, ...], VehicleState, dict[str, UavState], tuple[Event, ...]]:
    updated_uavs = dict(uavs)
    updated_vehicle = vehicle
    updated_requests: list[ServiceRequest] = []
    events: list[Event] = []
    for request in requests:
        if request.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
            updated_requests.append(request)
            continue
        updated_requests.append(replace(request, status=RequestStatus.CANCELLED))
        uav = updated_uavs.get(request.uav_id)
        if uav is not None and uav.active_request_id == request.request_id:
            updated_uavs[request.uav_id] = replace(
                uav, active_request_id=None, service_locked=False
            )
        if updated_vehicle.active_request_id == request.request_id:
            updated_vehicle = replace(
                updated_vehicle,
                mode=VehicleMode.IDLE,
                active_request_id=None,
                service_steps_elapsed=0,
                service_steps_required=0,
                planned_transfer_l=0.0,
            )
        events.append(
            Event(
                step,
                "termination",
                "request_cancelled",
                request.request_id,
                (("reason", "episode_terminated"),),
            )
        )
    return tuple(updated_requests), updated_vehicle, updated_uavs, tuple(events)
