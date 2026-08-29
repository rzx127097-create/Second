"""Physical G2-to-G3 cooperative environment adapter for G5."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any, Iterable, Mapping

import numpy as np

from problem2.algorithms.protocol import ActionResult
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
from problem2.dynamics.motion import move_uav, move_vehicle, uav_action_mask
from problem2.environment.action_masks import convert_g2_uav_mask
from problem2.environment.observations import (
    build_role_observations,
    build_structured_critic_state,
)
from problem2.evaluation.metrics import EpisodeMetrics, EpisodeRecord
from problem2.heuristics.astar import astar_path_and_distance
from problem2.heuristics import ControllerDecision, DispatchObservation, ObservableRequest
from problem2.resources.ledger import apply_spray, assert_conserved
from problem2.road.models import RasterRoadGraph
from problem2.road.search import NoPathError
from problem2.service.state_machine import (
    advance_service,
    cancel_terminal_requests,
    create_request,
    reserve_request,
    should_request,
    start_service,
)
from problem2.simulation.engine import estimate_service_delay_s


G3_TO_G2_UAV_ACTION = (
    Action.UP,
    Action.DOWN,
    Action.LEFT,
    Action.RIGHT,
    Action.STAY,
    Action.SPRAY,
)


@dataclass(frozen=True)
class _Dispatch:
    request_id: str
    sampled_slot: int
    candidate_mapping: tuple[str | None, ...]
    selected_service_node: int
    route_length_m: float


def _replace_request(requests: list[ServiceRequest], updated: ServiceRequest) -> None:
    for index, request in enumerate(requests):
        if request.request_id == updated.request_id:
            requests[index] = updated
            return
    raise ValueError(f"request {updated.request_id} is absent from the episode")


class Problem2CooperativeEnv:
    """Execute preserved semantic slots through verified physical components."""

    def __init__(
        self,
        initial_state: EpisodeState,
        graph: RasterRoadGraph,
        config: G2Config,
        *,
        max_steps: int,
        scenario_id: int,
        field_summary: Iterable[float] = (),
        initial_total_pest: float | None = None,
        final_total_pest: float | None = None,
        vehicle_controller: Any | None = None,
    ) -> None:
        if not isinstance(initial_state, EpisodeState):
            raise TypeError("initial_state must be an EpisodeState")
        if initial_state.terminated:
            raise ValueError("initial_state cannot already be terminated")
        if initial_state.ledger is None:
            raise ValueError("initial_state must carry the G2 pesticide ledger")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= initial_state.step:
            raise ValueError("max_steps must exceed the initial state step")
        if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
            raise ValueError("scenario_id must be an integer")
        field = tuple(float(value) for value in field_summary)
        if any(not math.isfinite(value) for value in field):
            raise ValueError("field_summary values must be finite")
        self.initial_state = initial_state
        self.graph = graph
        self.config = config
        self.max_steps = max_steps
        self.scenario_id = scenario_id
        self.field_summary = field
        self.initial_total_pest = initial_total_pest
        self.final_total_pest = final_total_pest
        if vehicle_controller is not None and not callable(getattr(vehicle_controller, "decide", None)):
            raise TypeError("vehicle_controller must implement decide(observation)")
        self.vehicle_controller = vehicle_controller
        self.ecology_global_context: tuple[float, ...] = ()
        self.uav_ecology_context: dict[str, tuple[float, ...]] = {}
        self._initial_vehicle_inventory_l = initial_state.vehicle.inventory_l
        self._state = initial_state
        self._dispatch: _Dispatch | None = None
        self._metrics = EpisodeMetrics(
            initial_state,
            tolerance=config.tolerance,
        )
        self._current_view: dict[str, Any] | None = None
        self._candidate_nodes: dict[str, tuple[int, float]] = {}

    @property
    def state(self) -> EpisodeState:
        return self._state

    def _primary_nodes_within_radius(self, uav: UavState) -> tuple[int, ...]:
        nodes: list[int] = []
        for node, (row, col) in enumerate(zip(self.graph.node_rows, self.graph.node_cols)):
            if int(self.graph.component_id[int(row), int(col)]) != self.graph.primary_component_id:
                continue
            if math.hypot(
                float(self.graph.node_x_m[node]) - uav.x_m,
                float(self.graph.node_y_m[node]) - uav.y_m,
            ) <= self.config.rendezvous_radius_m + self.config.tolerance:
                nodes.append(node)
        return tuple(nodes)

    def _best_service_node(self, request: ServiceRequest) -> tuple[int, float] | None:
        uav = next(item for item in self._state.uavs if item.uav_id == request.uav_id)
        transferable = min(
            request.requested_l,
            max(0.0, self.config.usable_capacity_l - uav.pesticide_l),
            self.config.service_cap_l,
            self._state.vehicle.inventory_l,
        )
        if transferable <= self.config.tolerance:
            return None
        candidates: list[tuple[float, int]] = []
        for node in self._primary_nodes_within_radius(uav):
            try:
                _, distance = astar_path_and_distance(
                    self.graph, self._state.vehicle.current_node, node
                )
            except NoPathError:
                continue
            candidates.append((distance, node))
        if not candidates:
            return None
        distance, node = min(candidates, key=lambda item: (item[0], item[1]))
        return node, distance

    def _candidate_requests(self) -> tuple[list[ServiceRequest], list[str | None]]:
        if self._dispatch is not None:
            request = next(
                item for item in self._state.requests if item.request_id == self._dispatch.request_id
            )
            self._candidate_nodes = {
                request.request_id: (
                    self._dispatch.selected_service_node,
                    self._dispatch.route_length_m,
                )
            }
            return [request], list(self._dispatch.candidate_mapping)
        eligible: list[tuple[ServiceRequest, int, float]] = []
        for request in self._state.requests:
            if request.status is not RequestStatus.PENDING or request.reserved_vehicle_id is not None:
                continue
            selected = self._best_service_node(request)
            if selected is None:
                continue
            node, distance = selected
            eligible.append((request, node, distance))
        eligible.sort(key=lambda item: (item[0].created_step, item[0].uav_id, item[0].request_id))
        eligible = eligible[:4]
        mapping: list[str | None] = [None, None, None, None]
        self._candidate_nodes = {}
        requests: list[ServiceRequest] = []
        for slot, (request, node, distance) in enumerate(eligible):
            mapping[slot] = request.request_id
            self._candidate_nodes[request.request_id] = (node, distance)
            requests.append(request)
        return requests, mapping

    def _snapshot(self, candidates: list[ServiceRequest], mapping: list[str | None]) -> dict:
        request_by_id = {request.request_id: request for request in self._state.requests}
        uavs = []
        for uav in sorted(self._state.uavs, key=lambda item: item.uav_id):
            request = request_by_id.get(uav.active_request_id)
            uavs.append(
                {
                    "id": uav.uav_id,
                    "x": uav.x_m,
                    "y": uav.y_m,
                    "pesticide_l": uav.pesticide_l,
                    "capacity_l": self.config.usable_capacity_l,
                    "service_locked": uav.service_locked,
                    "active_request_id": uav.active_request_id,
                    "request_remaining_l": request.requested_l if request else 0.0,
                    "spray_flow_lps": self.config.spray_flow_lpm / 60.0,
                }
            )
        request_rows = []
        for request in self._state.requests:
            if request.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
                continue
            selected = self._candidate_nodes.get(request.request_id)
            request_rows.append(
                {
                    "id": request.request_id,
                    "uav_id": request.uav_id,
                    "remaining_l": request.requested_l,
                    "urgency": float(self._state.step - request.created_step),
                    "road_distance_m": selected[1] if selected else 0.0,
                    "valid": selected is not None,
                }
            )
        candidate_rows = []
        for slot, request_id in enumerate(mapping):
            if request_id is None:
                continue
            request = request_by_id[request_id]
            selected = self._candidate_nodes[request_id]
            candidate_rows.append(
                {
                    "slot": slot,
                    "request_id": request_id,
                    "uav_id": request.uav_id,
                    "remaining_l": request.requested_l,
                    "urgency": float(self._state.step - request.created_step),
                    "road_distance_m": selected[1],
                    "valid": True,
                }
            )
        return {
            "step": self._state.step,
            "max_steps": self.max_steps,
            "field_summary": self.field_summary,
            "uavs": uavs,
            "vehicle": {
                "id": self._state.vehicle.vehicle_id,
                "x": self._state.vehicle.x_m,
                "y": self._state.vehicle.y_m,
                "inventory_l": self._state.vehicle.inventory_l,
                "capacity_l": self._initial_vehicle_inventory_l,
                "mode": self._state.vehicle.mode.value,
                "active_request_id": (
                    self._dispatch.request_id if self._dispatch else None
                ),
            },
            "requests": request_rows,
            "candidate_slots": candidate_rows,
            "critic_only": (),
        }

    def _make_view(self, *, events: tuple[Event, ...] = ()) -> dict[str, Any]:
        candidates, mapping = self._candidate_requests()
        snapshot = self._snapshot(candidates, mapping)
        uav_masks = np.asarray(
            [
                convert_g2_uav_mask(
                    uav_action_mask(uav, self.config, self.graph.aoi_bounds_m)
                )
                for uav in sorted(self._state.uavs, key=lambda item: item.uav_id)
            ],
            dtype=bool,
        )
        if self._dispatch is None:
            vehicle_mask = np.asarray(
                [[True] + [request_id is not None for request_id in mapping]], dtype=bool
            )
        else:
            vehicle_mask = np.zeros((1, 5), dtype=bool)
            vehicle_mask[0, self._dispatch.sampled_slot] = True
        view = {
            "observations": build_role_observations(
                snapshot, len(self._state.uavs), 4
            ),
            "critic_state": build_structured_critic_state(
                snapshot, len(self._state.uavs), 4
            ),
            "masks": {"uav": uav_masks, "vehicle": vehicle_mask},
            "candidate_mapping": {"vehicle": mapping},
            "agent_ids": {
                "uav": [uav.uav_id for uav in sorted(self._state.uavs, key=lambda item: item.uav_id)],
                "vehicle": [self._state.vehicle.vehicle_id],
            },
            "episode_id": f"development-{self.scenario_id}",
            "scenario_id": self.scenario_id,
            "step": self._state.step,
            "events": events,
            "terminated": False,
            "truncated": self._state.terminated,
        }
        self._current_view = view
        return view

    def reset(self, *, scenario_id: int | None = None) -> dict[str, Any]:
        if scenario_id is not None and scenario_id != self.scenario_id:
            raise ValueError("environment scenario_id does not match requested evaluation")
        self._state = self.initial_state
        self._dispatch = None
        self._metrics = EpisodeMetrics(
            self.initial_state,
            tolerance=self.config.tolerance,
        )
        return self._make_view()

    def _validate_action_result(self, result: ActionResult) -> None:
        if self._current_view is None:
            raise RuntimeError("environment must be reset before stepping")
        if not isinstance(result, ActionResult):
            raise TypeError("environment step requires the exact ActionResult")
        for role in ("uav", "vehicle"):
            if not np.array_equal(result.masks[role], self._current_view["masks"][role]):
                raise ValueError(f"{role} ActionResult does not match stored role mask")
        if result.actions["uav"].shape != (len(self._state.uavs),):
            raise ValueError("UAV action count does not match fleet")
        if result.actions["vehicle"].shape != (1,):
            raise ValueError("vehicle action count must equal one")

    def _commit_dispatch(
        self,
        requests: list[ServiceRequest],
        sampled_slot: int,
        mapping: tuple[str | None, ...],
        events: list[Event],
    ) -> _Dispatch:
        request_id = mapping[sampled_slot - 1]
        if request_id is None:
            raise ValueError("sampled vehicle slot has no stored request mapping")
        request = next(item for item in requests if item.request_id == request_id)
        selected_node, route_length = self._candidate_nodes[request_id]
        reserved, reserve_event = reserve_request(request, self._state.vehicle, self._state.step)
        _replace_request(requests, reserved)
        events.append(reserve_event)
        dispatch = _Dispatch(
            request_id=request_id,
            sampled_slot=sampled_slot,
            candidate_mapping=mapping,
            selected_service_node=selected_node,
            route_length_m=route_length,
        )
        events.append(
            Event(
                self._state.step,
                "dispatch",
                "dispatch_reserved",
                request_id,
                (
                    ("origin_current_node", self._state.vehicle.current_node),
                    ("origin_edge_progress_m", self._state.vehicle.edge_progress_m),
                    ("origin_target_node", self._state.vehicle.target_node),
                    ("request_id", request_id),
                    ("route_length_m", route_length),
                    ("sampled_slot", sampled_slot),
                    ("selected_service_node", selected_node),
                ),
            )
        )
        return dispatch

    def _controller_decision(self, *, active: _Dispatch | None = None) -> ControllerDecision:
        candidates, mapping = self._candidate_requests()
        request_rows = []
        for request in candidates:
            uav = next(item for item in self._state.uavs if item.uav_id == request.uav_id)
            slot = mapping.index(request.request_id)
            request_rows.append(ObservableRequest(
                request.request_id, request.uav_id, slot, request.created_step,
                request.requested_l, uav.pesticide_l, self.config.usable_capacity_l,
                float(max(0, self.max_steps - self._state.step)), self._primary_nodes_within_radius(uav),
            ))
        observation = DispatchObservation(
            step=self._state.step, graph=self.graph, vehicle=self._state.vehicle,
            requests=tuple(request_rows), candidate_mapping=tuple(mapping),
            service_cap_l=self.config.service_cap_l, tolerance=self.config.tolerance,
            active_request_id=active.request_id if active else None,
            active_sampled_slot=active.sampled_slot if active else None,
            selected_service_node=active.selected_service_node if active else None,
            vehicle_speed_mps=self.config.vehicle_speed_mps,
        )
        decision = self.vehicle_controller.decide(observation)
        if not isinstance(decision, ControllerDecision):
            raise TypeError("vehicle_controller.decide must return ControllerDecision")
        return decision

    def _physical_vehicle_action(self, dispatch: _Dispatch) -> Action:
        vehicle = self._state.vehicle
        if vehicle.mode is VehicleMode.SERVING:
            return Action.STAY
        if vehicle.mode is VehicleMode.TRANSIT:
            if vehicle.direction is None:
                raise ValueError("transit vehicle has no physical direction")
            return vehicle.direction
        if vehicle.current_node == dispatch.selected_service_node:
            return Action.STAY
        path, _ = astar_path_and_distance(
            self.graph, vehicle.current_node, dispatch.selected_service_node
        )
        next_node = path[1]
        return next(
            action
            for neighbor, action, _ in self.graph.neighbors(vehicle.current_node)
            if neighbor == next_node
        )

    def step(
        self,
        action_result: ActionResult,
        *,
        returning_uav_ids: Iterable[str] = (),
        decision_runtime_s: float = 0.0,
    ) -> dict[str, Any]:
        if self._state.terminated:
            raise RuntimeError("episode is already terminated")
        self._validate_action_result(action_result)
        before = self._state
        step = before.step
        events: list[Event] = []
        requests = list(before.requests)
        dispatch = self._dispatch
        mapping = tuple(self._current_view["candidate_mapping"]["vehicle"])
        sampled_slot = int(action_result.actions["vehicle"][0])
        uavs = {uav.uav_id: uav for uav in before.uavs}
        uav_actions: dict[str, Action] = {}

        for uav, sampled in zip(sorted(before.uavs, key=lambda item: item.uav_id), action_result.actions["uav"]):
            physical = G3_TO_G2_UAV_ACTION[int(sampled)]
            uav_actions[uav.uav_id] = physical
            moved, motion_event = move_uav(
                uav, physical, self.config, self.graph.aoi_bounds_m, step=step
            )
            events.append(motion_event)
            if physical is Action.SPRAY:
                moved, ledger, spray_event = apply_spray(
                    moved, before.ledger, self.config.spray_per_step_l, step=step
                )
                before = replace(before, ledger=ledger)
                events.append(spray_event)
            uavs[uav.uav_id] = moved

        if dispatch is None and self.vehicle_controller is not None:
            decision = self._controller_decision()
            sampled_slot = decision.sampled_slot
            if sampled_slot > 0:
                request_id = decision.request_id
                if request_id is None or sampled_slot > len(mapping) or mapping[sampled_slot - 1] != request_id:
                    raise ValueError("controller decision request does not match candidate mapping")
                self._candidate_nodes[request_id] = (int(decision.selected_service_node), float(decision.route_length_m))
                dispatch = self._commit_dispatch(requests, sampled_slot, mapping, events)
        elif dispatch is None and sampled_slot > 0:
            dispatch = self._commit_dispatch(requests, sampled_slot, mapping, events)
        elif dispatch is not None:
            if self.vehicle_controller is not None:
                decision = self._controller_decision(active=dispatch)
                if decision.sampled_slot != dispatch.sampled_slot or decision.request_id != dispatch.request_id:
                    raise ValueError("controller changed an active dispatch identity")
                dispatch = replace(
                    dispatch,
                    selected_service_node=int(decision.selected_service_node),
                    route_length_m=float(decision.route_length_m),
                )
            if sampled_slot != dispatch.sampled_slot or mapping != dispatch.candidate_mapping:
                if self.vehicle_controller is None:
                    raise ValueError("active dispatch must preserve its original sampled slot and mapping")

        vehicle = before.vehicle
        if dispatch is None:
            vehicle, vehicle_event = move_vehicle(
                vehicle,
                Action.STAY,
                self.graph,
                self.config.vehicle_speed_mps * self.config.dt_s,
                step=step,
            )
            events.append(vehicle_event)
        else:
            physical = self._physical_vehicle_action(dispatch)
            vehicle, vehicle_event = move_vehicle(
                vehicle,
                physical,
                self.graph,
                self.config.vehicle_speed_mps * self.config.dt_s,
                step=step,
            )
            events.append(vehicle_event)
            motion = dict(vehicle_event.payload)
            events.append(
                Event(
                    step,
                    "dispatch",
                    "vehicle_slot_executed",
                    vehicle.vehicle_id,
                    (
                        ("physical_direction", physical.name),
                        ("request_id", dispatch.request_id),
                        ("sampled_slot", dispatch.sampled_slot),
                    ),
                )
            )
            events.append(
                Event(
                    step,
                    "dispatch",
                    "vehicle_service_motion",
                    dispatch.request_id,
                    (("actual_distance_m", motion["actual_distance_m"]),),
                )
            )

        provisional = EpisodeState(
            step,
            tuple(uavs[key] for key in sorted(uavs)),
            vehicle,
            tuple(requests),
            before.ledger,
        )
        for uav_id in sorted(uavs):
            uav = uavs[uav_id]
            if uav.active_request_id is not None:
                continue
            delay = estimate_service_delay_s(uav, provisional, self.graph, self.config)
            has_positive_pesticide_gap = (
                self.config.usable_capacity_l - uav.pesticide_l
                > self.config.tolerance
            )
            if has_positive_pesticide_gap and should_request(
                uav.pesticide_l,
                self.config.spray_flow_lpm / 60.0,
                delay,
                self.config.request_margin_s,
            ):
                uav, request, request_event = create_request(
                    uav, step, delay, self.config
                )
                uavs[uav_id] = uav
                requests.append(request)
                events.append(request_event)

        ledger = before.ledger
        rendezvous_ready = False
        if vehicle.mode is VehicleMode.SERVING:
            active = next(item for item in requests if item.request_id == vehicle.active_request_id)
            active_uav = uavs[active.uav_id]
            active, vehicle, active_uav, ledger, service_events = advance_service(
                active, vehicle, active_uav, ledger, self.config, step
            )
            _replace_request(requests, active)
            uavs[active.uav_id] = active_uav
            events.extend(service_events)
            if active.status is RequestStatus.COMPLETED:
                transferred = next(
                    float(dict(event.payload)["transferred_l"])
                    for event in service_events
                    if event.kind == "service_completed"
                )
                events.append(
                    Event(
                        step,
                        "service",
                        "service_outcome",
                        active.request_id,
                        (
                            ("requested_l", active.requested_l),
                            ("transferred_l", transferred),
                        ),
                    )
                )
                dispatch = None
        elif (
            dispatch is not None
            and vehicle.current_node == dispatch.selected_service_node
            and vehicle.target_node is None
        ):
            reserved = next(
                item for item in requests if item.request_id == dispatch.request_id
            )
            rendezvous_uav = uavs[reserved.uav_id]
            rendezvous_ready = (
                math.hypot(
                    rendezvous_uav.x_m - vehicle.x_m,
                    rendezvous_uav.y_m - vehicle.y_m,
                )
                <= self.config.rendezvous_radius_m + self.config.tolerance
            )
        if vehicle.mode is not VehicleMode.SERVING and dispatch is not None and rendezvous_ready:
            active = next(item for item in requests if item.request_id == dispatch.request_id)
            active_uav = uavs[active.uav_id]
            active, vehicle, active_uav, started_event = start_service(
                active, vehicle, active_uav, self.config, step, self.graph
            )
            _replace_request(requests, active)
            uavs[active.uav_id] = active_uav
            events.append(started_event)
            active, vehicle, active_uav, ledger, service_events = advance_service(
                active, vehicle, active_uav, ledger, self.config, step
            )
            _replace_request(requests, active)
            uavs[active.uav_id] = active_uav
            events.extend(service_events)
            if active.status is RequestStatus.COMPLETED:
                transferred = next(
                    float(dict(event.payload)["transferred_l"])
                    for event in service_events
                    if event.kind == "service_completed"
                )
                events.append(
                    Event(
                        step,
                        "service",
                        "service_outcome",
                        active.request_id,
                        (
                            ("requested_l", active.requested_l),
                            ("transferred_l", transferred),
                        ),
                    )
                )
                dispatch = None

        ordered_uavs = tuple(uavs[key] for key in sorted(uavs))
        assert_conserved(ordered_uavs, vehicle.inventory_l, ledger, self.config.tolerance)
        observed = math.fsum(uav.pesticide_l for uav in ordered_uavs) + vehicle.inventory_l
        expected = ledger.initial_total_l - ledger.cumulative_sprayed_l
        events.append(
            Event(
                step,
                "conservation",
                "conservation_checked",
                "pesticide",
                (("error_l", abs(observed - expected)),),
            )
        )
        next_step = step + 1
        terminated = next_step >= self.max_steps
        if terminated:
            requests_tuple, vehicle, uav_map, cancellation_events = cancel_terminal_requests(
                requests, vehicle, {uav.uav_id: uav for uav in ordered_uavs}, step
            )
            requests = list(requests_tuple)
            ordered_uavs = tuple(uav_map[key] for key in sorted(uav_map))
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
            dispatch = None
        after = EpisodeState(
            next_step,
            ordered_uavs,
            vehicle,
            tuple(requests),
            ledger,
            tuple(events),
            terminated,
        )
        self._metrics.record_step(
            self._state,
            after,
            events=events,
            uav_actions=uav_actions,
            returning_uav_ids=returning_uav_ids,
            decision_runtime_s=decision_runtime_s,
        )
        self._state = after
        self._dispatch = dispatch
        view = self._make_view(events=tuple(events))
        view["sampled_actions"] = {
            role: values.copy() for role, values in action_result.actions.items()
        }
        return view

    def episode_record(self) -> EpisodeRecord:
        return self._metrics.finalize(
            self._state,
            terminal_boundary_step=self._state.step,
            initial_total_pest=self.initial_total_pest,
            final_total_pest=self.final_total_pest,
            scenario_id=self.scenario_id,
        )


__all__ = ["Problem2CooperativeEnv"]
