from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Mapping

from problem2.config import G2Config
from problem2.domain import (
    Action,
    EpisodeState,
    Event,
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleMode,
)
from problem2.dynamics.motion import (
    IllegalActionError,
    move_uav,
    move_vehicle,
    uav_action_mask,
    validate_vehicle_road_state,
    vehicle_action_mask,
)
from problem2.resources.ledger import (
    ResourceInvariantError,
    ResourceLedger,
    apply_spray,
    assert_conserved,
)
from problem2.road.models import RasterRoadGraph
from problem2.road.search import NoPathError, astar_distance
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


class StepTransactionError(ValueError):
    """Raised when a simulation step cannot be committed atomically."""


@dataclass(frozen=True)
class StoredMasks:
    uavs: tuple[tuple[str, tuple[bool, ...]], ...]
    vehicle: tuple[bool, ...]

    def for_uav(self, uav_id: str) -> tuple[bool, ...]:
        for observed_id, mask in self.uavs:
            if observed_id == uav_id:
                return mask
        raise KeyError(uav_id)


def build_action_masks(
    state: EpisodeState, graph: RasterRoadGraph, config: G2Config
) -> StoredMasks:
    try:
        validate_vehicle_road_state(state.vehicle, graph, config.tolerance)
    except ValueError as exc:
        raise StepTransactionError(f"invalid vehicle road state: {exc}") from exc
    return StoredMasks(
        uavs=tuple(
            (
                uav.uav_id,
                tuple(
                    bool(value)
                    for value in uav_action_mask(
                        uav, config, graph.aoi_bounds_m
                    ).tolist()
                ),
            )
            for uav in sorted(state.uavs, key=lambda item: item.uav_id)
        ),
        vehicle=tuple(
            bool(value)
            for value in vehicle_action_mask(
                state.vehicle, graph, config.tolerance
            )
        ),
    )


def _primary_nodes(graph: RasterRoadGraph) -> list[int]:
    return [
        node
        for node, (row, col) in enumerate(zip(graph.node_rows, graph.node_cols))
        if int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
    ]


def estimate_service_delay_s(
    uav: UavState,
    state: EpisodeState,
    graph: RasterRoadGraph,
    config: G2Config,
) -> float:
    vehicle = state.vehicle
    try:
        validate_vehicle_road_state(vehicle, graph, config.tolerance)
    except ValueError as exc:
        raise ServiceStateError(str(exc)) from exc
    committed_inventory = (
        vehicle.planned_transfer_l if vehicle.mode is VehicleMode.SERVING else 0.0
    )
    available_inventory = max(0.0, vehicle.inventory_l - committed_inventory)
    transferable = min(
        max(0.0, config.usable_capacity_l - uav.pesticide_l),
        config.service_cap_l,
        available_inventory,
    )
    if transferable <= config.tolerance:
        return math.inf
    candidates = [
        node
        for node in _primary_nodes(graph)
        if math.hypot(
            float(graph.node_x_m[node]) - uav.x_m,
            float(graph.node_y_m[node]) - uav.y_m,
        )
        <= config.rendezvous_radius_m
    ]
    if not candidates:
        return math.inf

    queue_delay = 0.0
    base_distance = 0.0
    if vehicle.mode is VehicleMode.TRANSIT:
        if vehicle.target_node is None:
            raise ServiceStateError("transit vehicle has no target node")
        edge_length = next(
            length
            for neighbor, _, length in graph.neighbors(vehicle.current_node)
            if neighbor == vehicle.target_node
        )
        base_distance = edge_length - vehicle.edge_progress_m
        origin = vehicle.target_node
    else:
        origin = vehicle.current_node
    if vehicle.mode is VehicleMode.SERVING:
        queue_delay = max(
            0, vehicle.service_steps_required - vehicle.service_steps_elapsed
        ) * config.dt_s

    shortest = math.inf
    for candidate in candidates:
        try:
            route = astar_distance(graph, origin, candidate)
        except NoPathError:
            continue
        shortest = min(shortest, base_distance + route)
    if not math.isfinite(shortest):
        return math.inf
    transfer_delay = transferable / (config.transfer_rate_lpm / 60.0)
    return queue_delay + shortest / config.vehicle_speed_mps + config.setup_time_s + transfer_delay


def _replace_request(
    requests: list[ServiceRequest], updated: ServiceRequest
) -> None:
    for index, request in enumerate(requests):
        if request.request_id == updated.request_id:
            requests[index] = updated
            return
    raise ServiceStateError(f"request {updated.request_id} is missing from episode state")


def _validate_masks(
    state: EpisodeState,
    stored: StoredMasks,
    graph: RasterRoadGraph,
    config: G2Config,
) -> None:
    expected = build_action_masks(state, graph, config)
    if stored.vehicle != expected.vehicle:
        raise StepTransactionError(
            f"stored vehicle mask {stored.vehicle} does not match state mask {expected.vehicle}"
        )
    if stored.uavs != expected.uavs:
        raise StepTransactionError("stored UAV masks do not match state masks")


def step_episode(
    state: EpisodeState,
    uav_actions: Mapping[str, Action],
    vehicle_action: Action,
    stored_masks: StoredMasks,
    graph: RasterRoadGraph,
    config: G2Config,
    *,
    max_steps: int,
) -> EpisodeState:
    if state.terminated:
        raise StepTransactionError("cannot step a terminated episode")
    if max_steps <= 0:
        raise StepTransactionError("max_steps must be positive")
    if not isinstance(state.ledger, ResourceLedger):
        raise StepTransactionError("episode state has no pesticide ledger")
    _validate_masks(state, stored_masks, graph, config)
    expected_uav_ids = {uav.uav_id for uav in state.uavs}
    if set(uav_actions) != expected_uav_ids:
        raise StepTransactionError(
            f"UAV action IDs must equal {sorted(expected_uav_ids)}"
        )

    try:
        step = state.step
        uavs = {uav.uav_id: uav for uav in state.uavs}
        ledger = state.ledger
        action_events: list[Event] = []
        spray_events: list[Event] = []
        for uav_id in sorted(uavs):
            action = Action(uav_actions[uav_id])
            moved, motion_event = move_uav(
                uavs[uav_id], action, config, graph.aoi_bounds_m, step=step
            )
            uavs[uav_id] = moved
            action_events.append(motion_event)
            if action is Action.SPRAY:
                sprayed, ledger, spray_event = apply_spray(
                    moved, ledger, config.spray_per_step_l, step=step
                )
                uavs[uav_id] = sprayed
                spray_events.append(spray_event)
        vehicle, vehicle_event = move_vehicle(
            state.vehicle,
            vehicle_action,
            graph,
            config.vehicle_speed_mps * config.dt_s,
            step=step,
        )
        action_events.append(vehicle_event)
        requests = list(state.requests)
        request_events: list[Event] = []
        provisional_state = replace(
            state,
            uavs=tuple(uavs[key] for key in sorted(uavs)),
            vehicle=vehicle,
            requests=tuple(requests),
            ledger=ledger,
        )
        for uav_id in sorted(uavs):
            uav = uavs[uav_id]
            if uav.active_request_id is not None:
                continue
            delay = estimate_service_delay_s(uav, provisional_state, graph, config)
            if should_request(
                uav.pesticide_l,
                config.spray_flow_lpm / 60.0,
                delay,
                config.request_margin_s,
            ):
                updated_uav, request, event = create_request(
                    uav, step, delay, config
                )
                uavs[uav_id] = updated_uav
                requests.append(request)
                request_events.append(event)

        service_events: list[Event] = []
        if vehicle.mode is VehicleMode.SERVING:
            active = next(
                request
                for request in requests
                if request.request_id == vehicle.active_request_id
            )
            active_uav = uavs[active.uav_id]
            active, vehicle, active_uav, ledger, events = advance_service(
                active, vehicle, active_uav, ledger, config, step
            )
            _replace_request(requests, active)
            uavs[active.uav_id] = active_uav
            service_events.extend(events)
        else:
            selected = select_serviceable_request(
                requests,
                vehicle,
                uavs,
                config.rendezvous_radius_m,
                graph,
                config.tolerance,
            )
            if selected is not None:
                selected_uav = uavs[selected.uav_id]
                selected, reserve_event = reserve_request(selected, vehicle, step)
                _replace_request(requests, selected)
                service_events.append(reserve_event)
                selected, vehicle, selected_uav, started_event = start_service(
                    selected, vehicle, selected_uav, config, step, graph
                )
                _replace_request(requests, selected)
                uavs[selected.uav_id] = selected_uav
                service_events.append(started_event)
                selected, vehicle, selected_uav, ledger, events = advance_service(
                    selected, vehicle, selected_uav, ledger, config, step
                )
                _replace_request(requests, selected)
                uavs[selected.uav_id] = selected_uav
                service_events.extend(events)

        environment_event = Event(
            step,
            "environment",
            "g2_environment_hook",
            "environment",
            (("operation", "no_op"),),
        )
        ordered_uavs = tuple(uavs[key] for key in sorted(uavs))
        assert_conserved(ordered_uavs, vehicle.inventory_l, ledger, config.tolerance)
        observed_total = math.fsum(uav.pesticide_l for uav in ordered_uavs) + vehicle.inventory_l
        expected_total = ledger.initial_total_l - ledger.cumulative_sprayed_l
        conservation_event = Event(
            step,
            "conservation",
            "conservation_checked",
            "pesticide",
            (
                ("error_l", abs(observed_total - expected_total)),
                ("expected_l", expected_total),
                ("observed_l", observed_total),
            ),
        )
        events = (
            action_events
            + spray_events
            + request_events
            + service_events
            + [environment_event, conservation_event]
        )
        next_step = step + 1
        terminated = next_step >= max_steps
        if terminated:
            requests_tuple, vehicle, uavs, cancellation_events = cancel_terminal_requests(
                requests, vehicle, uavs, step
            )
            requests = list(requests_tuple)
            ordered_uavs = tuple(uavs[key] for key in sorted(uavs))
            events.extend(cancellation_events)
            events.append(
                Event(
                    step,
                    "termination",
                    "episode_terminated",
                    "episode",
                    (("reason", "max_steps"), ("step", next_step)),
                )
            )
        return EpisodeState(
            step=next_step,
            uavs=ordered_uavs,
            vehicle=vehicle,
            requests=tuple(requests),
            ledger=ledger,
            last_step_events=tuple(events),
            terminated=terminated,
        )
    except StepTransactionError:
        raise
    except (
        IllegalActionError,
        ResourceInvariantError,
        ServiceStateError,
        StopIteration,
        ValueError,
    ) as exc:
        raise StepTransactionError(
            f"G2 step {state.step} failed before commit: {exc}"
        ) from exc
