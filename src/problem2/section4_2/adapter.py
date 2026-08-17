"""Role-slot adapter with road-constrained replenishment service events."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from math import hypot, isfinite

from problem2.demand.candidate_slots import build_candidate_action_slots
from problem2.demand.endurance import remaining_work_time_s
from problem2.demand.planning import RendezvousCandidate, generate_rendezvous_candidates
from problem2.demand.rendezvous import RendezvousPoint
from problem2.domain.requests import RequestManager, RequestStatus
from problem2.domain.resources import PesticideResources
from problem2.environment.action_masks import ActionMask, uav_action_mask, vehicle_action_mask
from problem2.environment.movement import legal_uav_position
from problem2.environment.service_state_machine import ServicePhase, ServiceStateMachine
from problem2.road.graph import RoadGraph
from problem2.road.shortest_path import shortest_path

from .road_executor import RoadVehicleExecutor


@dataclass(frozen=True)
class DecisionState:
    role_slots: dict[str, tuple[str, ...]]
    action_masks: dict[str, ActionMask]
    events: list[dict[str, object]]
    vehicle_nodes: dict[str, str]
    uav_positions: dict[str, tuple[int, int]]
    candidate_mapping: dict[str, tuple[tuple[str, str], ...]]
    candidate_features: dict[str, tuple[dict[str, object], ...]]


class HeterogeneousDecisionAdapter:
    """Single physical transition authority for UAVs, road vehicles and service."""

    def __init__(
        self,
        resources: PesticideResources,
        road_graph: RoadGraph,
        *,
        uav_slots: tuple[str, ...],
        vehicle_slots: tuple[str, ...],
        vehicle_speed_mps: float = 1.0,
        decision_dt_s: float = 1.0,
        uav_grid_shape: tuple[int, int] = (1, 1),
        uav_cell_size_m: tuple[float, float] = (1.0, 1.0),
        uav_speed_mps: float = 1.0,
        request_threshold_ratio: float = 0.0,
        dynamic_request_enabled: bool = False,
        request_safety_margin_s: float = 0.0,
        service_setup_s: float = 10.0,
        rendezvous_radius_m: float = 5.0,
        max_candidate_slots: int = 4,
        support_mode: str = "mobile",
        initial_vehicle_nodes: Mapping[str, str] | None = None,
        request_release_steps: Mapping[str, int] | None = None,
        endurance_prediction_enabled: bool = True,
        joint_demand_rendezvous_enabled: bool = True,
    ) -> None:
        if not vehicle_slots:
            raise ValueError("at least one vehicle slot is required")
        if any(identifier not in resources.uavs for identifier in uav_slots):
            raise ValueError("unknown UAV slot")
        if any(identifier not in resources.vehicles for identifier in vehicle_slots):
            raise ValueError("unknown vehicle slot")
        if decision_dt_s <= 0 or vehicle_speed_mps <= 0 or uav_speed_mps <= 0:
            raise ValueError("decision and vehicle speeds must be positive")
        if len(uav_grid_shape) != 2 or any(int(size) <= 0 for size in uav_grid_shape):
            raise ValueError("uav_grid_shape must contain two positive dimensions")
        if len(uav_cell_size_m) != 2 or any(float(size) <= 0 for size in uav_cell_size_m):
            raise ValueError("uav_cell_size_m must contain two positive dimensions")
        if not 0.0 <= request_threshold_ratio <= 1.0:
            raise ValueError("request_threshold_ratio must lie in [0, 1]")
        if (
            service_setup_s < 0
            or request_safety_margin_s < 0
            or rendezvous_radius_m < 0
            or max_candidate_slots < 1
        ):
            raise ValueError("invalid service configuration")
        if support_mode not in {"mobile", "fixed", "disabled", "teleport"}:
            raise ValueError("unsupported support_mode")
        self.resources = resources
        self._initial_uav_onboard = {key: float(value.onboard_l) for key, value in resources.uavs.items()}
        self._initial_vehicle_inventory = {key: float(value.inventory_l) for key, value in resources.vehicles.items()}
        self.road_graph = road_graph
        self.uav_slots = tuple(uav_slots)
        self.vehicle_slots = tuple(vehicle_slots)
        self.vehicle_speed_mps = float(vehicle_speed_mps)
        self.decision_dt_s = float(decision_dt_s)
        self.uav_grid_shape = (int(uav_grid_shape[0]), int(uav_grid_shape[1]))
        self.uav_cell_size_m = (float(uav_cell_size_m[0]), float(uav_cell_size_m[1]))
        self.uav_speed_mps = float(uav_speed_mps)
        self.request_threshold_ratio = float(request_threshold_ratio)
        self.dynamic_request_enabled = bool(dynamic_request_enabled)
        self.request_safety_margin_s = float(request_safety_margin_s)
        self.service_setup_s = float(service_setup_s)
        self.rendezvous_radius_m = float(rendezvous_radius_m)
        self.max_candidate_slots = int(max_candidate_slots)
        self.support_mode = str(support_mode)
        supplied_release_steps = dict(request_release_steps or {})
        if any(identifier not in self.uav_slots for identifier in supplied_release_steps):
            raise ValueError("request release schedule references an unknown UAV")
        if any(type(value) is not int or value < 1 for value in supplied_release_steps.values()):
            raise ValueError("request release steps must be positive integers")
        self.request_release_steps = {
            uav_id: int(supplied_release_steps.get(uav_id, 1)) for uav_id in self.uav_slots
        }
        self.endurance_prediction_enabled = bool(endurance_prediction_enabled)
        self.joint_demand_rendezvous_enabled = bool(joint_demand_rendezvous_enabled)
        default_start = sorted(self.road_graph.nodes)[0]
        supplied_starts = dict(initial_vehicle_nodes or {})
        if any(vehicle_id not in self.vehicle_slots for vehicle_id in supplied_starts):
            raise ValueError("initial vehicle node references an unknown vehicle")
        self.initial_vehicle_nodes = {
            vehicle_id: str(supplied_starts.get(vehicle_id, default_start))
            for vehicle_id in self.vehicle_slots
        }
        if any(not self.road_graph.has_node(node) for node in self.initial_vehicle_nodes.values()):
            raise ValueError("initial vehicle node must belong to the road graph")
        self.executors: dict[str, RoadVehicleExecutor] = {}
        self.uav_positions: dict[str, tuple[int, int]] = {}
        self._uav_metric_positions: dict[str, tuple[float, float]] = {}
        self._uav_transit: dict[str, dict[str, object]] = {}
        self._candidate_routes: dict[str, dict[str, tuple[str, ...]]] = {}
        self._candidate_request_ids: dict[str, dict[str, str]] = {}
        self._candidate_mapping_keys: dict[str, dict[str, str]] = {}
        self._candidate_records: dict[str, dict[str, RendezvousCandidate]] = {}
        self._candidate_target_cells: dict[str, dict[str, tuple[int, int]]] = {}
        self._locked_uav_id: str | None = None
        self._locked_vehicle_id: str | None = None
        self._committed_uav_id: str | None = None
        self._committed_vehicle_id: str | None = None
        self._service_target_node: str | None = None
        self._service_target_uav_cell: tuple[int, int] | None = None
        self._decision_step = 0
        self.request_manager = RequestManager()
        self.service = ServiceStateMachine()
        self._state: DecisionState | None = None

    @property
    def state(self) -> DecisionState:
        if self._state is None:
            raise RuntimeError("reset must be called before accessing state")
        return self._state

    def reset(self, *, seed: int | None = None) -> DecisionState:
        del seed
        for identifier, amount in self._initial_uav_onboard.items():
            self.resources.uav(identifier).onboard_l = amount
        for identifier, amount in self._initial_vehicle_inventory.items():
            self.resources.vehicle(identifier).inventory_l = amount
        self.resources._initial_total_l = self.resources.total_pesticide_l
        self.resources._cumulative_sprayed_l = 0.0
        self.request_manager = RequestManager()
        self.service = ServiceStateMachine()
        self._decision_step = 0
        self._locked_uav_id = None
        self._locked_vehicle_id = None
        self._committed_uav_id = None
        self._committed_vehicle_id = None
        self._service_target_node = None
        self._service_target_uav_cell = None
        self.executors = {
            vehicle_id: RoadVehicleExecutor(
                self.road_graph,
                current_node=self.initial_vehicle_nodes[vehicle_id],
                speed_mps=self.vehicle_speed_mps,
            )
            for vehicle_id in self.vehicle_slots
        }
        self.uav_positions = {uav_id: (0, 0) for uav_id in self.uav_slots}
        self._uav_metric_positions = {uav_id: (0.0, 0.0) for uav_id in self.uav_slots}
        self._uav_transit = {}
        self._candidate_routes = {}
        self._candidate_request_ids = {vehicle_id: {} for vehicle_id in self.vehicle_slots}
        self._candidate_mapping_keys = {vehicle_id: {} for vehicle_id in self.vehicle_slots}
        self._candidate_records = {vehicle_id: {} for vehicle_id in self.vehicle_slots}
        self._candidate_target_cells = {vehicle_id: {} for vehicle_id in self.vehicle_slots}
        self._refresh_request_candidates()
        self._refresh_state(events=[])
        return self.state

    def set_candidate_routes(self, vehicle_id: str, routes_by_slot: Mapping[str, Iterable[str]]) -> None:
        if vehicle_id not in self.executors:
            raise KeyError(vehicle_id)
        routes: dict[str, tuple[str, ...]] = {}
        for slot, route in routes_by_slot.items():
            slot_name = str(slot)
            if not slot_name.startswith("slot-"):
                raise ValueError("candidate route keys must use slot-* names")
            values = tuple(str(node) for node in route)
            if not values:
                raise ValueError("candidate route cannot be empty")
            probe = RoadVehicleExecutor(self.road_graph, current_node=self.executors[vehicle_id].current_node, speed_mps=self.vehicle_speed_mps)
            probe.set_route(values)
            routes[slot_name] = values
        self._candidate_routes[vehicle_id] = routes
        self._candidate_mapping_keys[vehicle_id] = {
            slot: f"manual:{slot}:{route[-1]}" for slot, route in routes.items()
        }
        self._candidate_target_cells[vehicle_id] = {
            slot: self.road_node_to_uav_cell(route[-1]) for slot, route in routes.items()
        }
        self._candidate_records[vehicle_id] = {}
        self._refresh_state(events=self.state.events if self._state is not None else [])

    def set_service_lock(self, uav_id: str, vehicle_id: str) -> None:
        if uav_id not in self.uav_slots or vehicle_id not in self.vehicle_slots:
            raise KeyError("service lock references an unknown role slot")
        self._locked_uav_id = uav_id
        self._locked_vehicle_id = vehicle_id
        if self._state is not None:
            self._refresh_state(events=self._state.events)

    def clear_service_lock(self) -> None:
        self._locked_uav_id = None
        self._locked_vehicle_id = None
        if self._state is not None:
            self._refresh_state(events=self._state.events)

    def step(self, actions: Mapping[str, str]) -> DecisionState:
        if self._state is None:
            raise RuntimeError("reset must be called before step")
        self._decision_step += 1
        events: list[dict[str, object]] = []
        masks = self._state.action_masks
        expected = set(self.uav_slots) | set(self.vehicle_slots)
        if set(actions) != expected:
            raise ValueError("actions must contain exactly one action for every role slot")
        for agent_id, action in actions.items():
            mask = masks.get(agent_id)
            if mask is None or action not in mask.actions or not mask.mask[mask.actions.index(action)]:
                raise ValueError(f"action is not legal for {agent_id}: {action}")
        events.append({"event_type": "actions_validated", "step": self._decision_step})

        for uav_id in self.uav_slots:
            action = actions[uav_id]
            if uav_id in self._uav_transit:
                self._advance_uav_transit(uav_id, events)
                continue
            position = self.uav_positions[uav_id]
            if action in {"up", "down", "left", "right"}:
                new_position = legal_uav_position(
                    position, action, self.uav_grid_shape, locked=uav_id == self._locked_uav_id,
                )
                if new_position != position:
                    self._start_uav_transit(uav_id, new_position, action)
                    self._advance_uav_transit(uav_id, events)
            elif action == "spray" and uav_id != self._locked_uav_id:
                sprayed = self.resources.spray_step(uav_id, self.decision_dt_s)
                events.append({"event_type": "spray_applied", "uav_id": uav_id, "amount_l": sprayed.amount_l, "duration_s": self.decision_dt_s, "pesticide_limited": sprayed.pesticide_limited, "step": self._decision_step})

        for uav_id in self.uav_slots:
            state = self.resources.uav(uav_id)
            dynamic_trigger = self._dynamic_request_trigger(uav_id)
            threshold_trigger = (
                not self.dynamic_request_enabled
                and self.request_threshold_ratio > 0
                and state.onboard_l <= state.capacity_l * self.request_threshold_ratio + 1e-12
            )
            if (
                self._decision_step >= self.request_release_steps[uav_id]
                and (dynamic_trigger is not None or threshold_trigger)
            ):
                before = len(self.request_manager)
                requested_l = (
                    float(dynamic_trigger["target_l"])
                    if dynamic_trigger is not None
                    else state.capacity_l - state.onboard_l
                )
                request = self.request_manager.create_request(
                    uav_id, requested_l, self._decision_step,
                )
                if len(self.request_manager) > before:
                    event: dict[str, object] = {
                        "event_type": "request_created",
                        "request_id": request.request_id,
                        "uav_id": uav_id,
                        "amount_l": request.requested_l,
                        "trigger": "dynamic_endurance" if dynamic_trigger is not None else "fixed_threshold",
                        "step": self._decision_step,
                    }
                    if dynamic_trigger is not None:
                        event.update(dynamic_trigger)
                    events.append(event)

        if self.support_mode == "teleport":
            self._apply_teleport_service(events)
        for vehicle_id, executor in self.executors.items():
            action = actions[vehicle_id]
            if vehicle_id != self._locked_vehicle_id and action.startswith("slot-"):
                route = self._candidate_routes.get(vehicle_id, {}).get(action)
                request_id = self._candidate_request_ids.get(vehicle_id, {}).get(action)
                if route is not None:
                    executor.set_route(route)
                if request_id is not None and self.service.phase is ServicePhase.IDLE:
                    reserved = self.service.reserve_specific(
                        self.request_manager,
                        request_id,
                        vehicle_id,
                        self._decision_step,
                        self.service_setup_s,
                        defer_preparation=True,
                    )
                    if reserved is not None and reserved.request_id == request_id:
                        self._service_target_node = route[-1] if route else None
                        self._service_target_uav_cell = self._candidate_target_cells.get(vehicle_id, {}).get(action)
                        self._committed_uav_id = reserved.uav_id
                        self._committed_vehicle_id = vehicle_id
                        candidate = self._candidate_records.get(vehicle_id, {}).get(action)
                        road_distance_m = (
                            float(candidate.road_distance_m)
                            if candidate is not None
                            else sum(self.road_graph.edge_weight(left, right) for left, right in zip(route or (), (route or ())[1:]))
                        )
                        events.append({"event_type": "request_reserved", "request_id": reserved.request_id, "uav_id": reserved.uav_id, "vehicle_id": vehicle_id, "rendezvous_road_distance_m": road_distance_m, "step": self._decision_step})
            advance = executor.advance(dt_s=self.decision_dt_s)
            events.append({"event_type": "movement_applied", "vehicle_id": vehicle_id, "travelled_distance_m": advance.travelled_distance_m, "remaining_edge_distance_m": advance.remaining_edge_distance_m, "route_complete": advance.route_complete, "step": self._decision_step})

        active_request_id = self.service.request_id
        if active_request_id is not None:
            request = self.request_manager.get(active_request_id)
            vehicle_id = self._committed_vehicle_id or self._locked_vehicle_id
            vehicle_arrived = bool(
                vehicle_id
                and self._service_target_node
                and self.executors[vehicle_id].current_node == self._service_target_node
                and self.executors[vehicle_id].route_index >= len(self.executors[vehicle_id].route) - 1
            )
            uav_arrived = self._uav_has_arrived(request.uav_id)
            if self.service.phase is ServicePhase.RESERVED:
                if vehicle_arrived and uav_arrived:
                    self.service.begin_preparation(self.request_manager, self._decision_step)
                    self._locked_uav_id = request.uav_id
                    self._locked_vehicle_id = vehicle_id
                    events.append({"event_type": "joint_arrival", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                    events.append({"event_type": "service_started", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                else:
                    if vehicle_arrived and not uav_arrived:
                        events.append({"event_type": "wait", "duration_s": self.decision_dt_s, "reason": "vehicle_waiting_for_uav", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                    elif uav_arrived and not vehicle_arrived:
                        events.append({"event_type": "wait", "duration_s": self.decision_dt_s, "reason": "uav_waiting_for_vehicle", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                    if self.resources.uav(request.uav_id).onboard_l <= 1e-12:
                        events.append({"event_type": "pesticide_disabled", "duration_s": self.decision_dt_s, "uav_id": request.uav_id, "step": self._decision_step})
            elif self.service.phase in {ServicePhase.PREPARING, ServicePhase.TRANSFERRING}:
                previous_phase = self.service.phase
                events.append({"event_type": "service_active", "duration_s": self.decision_dt_s, "phase": previous_phase.value, "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                transferred = self.service.tick(self.request_manager, self.resources, vehicle_id, self.decision_dt_s, self._decision_step)
                if previous_phase is ServicePhase.PREPARING:
                    events.append({"event_type": "wait", "duration_s": self.decision_dt_s, "reason": "service_setup", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                if self.resources.uav(request.uav_id).onboard_l <= 1e-12:
                    events.append({"event_type": "pesticide_disabled", "duration_s": self.decision_dt_s, "uav_id": request.uav_id, "step": self._decision_step})
                if transferred > 0:
                    events.append({"event_type": "pesticide_transfer", "amount_l": transferred, "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                if self.service.phase is ServicePhase.IDLE:
                    events.append({"event_type": "service_released", "request_id": request.request_id, "step": self._decision_step})
                    if request.status is RequestStatus.COMPLETED:
                        events.append({"event_type": "request_completed", "request_id": request.request_id, "step": self._decision_step})
                    self._locked_uav_id = None
                    self._locked_vehicle_id = None
                    self._committed_uav_id = None
                    self._committed_vehicle_id = None
                    self._service_target_node = None
                    self._service_target_uav_cell = None
        productive_uavs = {
            str(event.get("uav_id")) for event in events
            if event.get("event_type") == "spray_applied" and float(event.get("amount_l", 0.0)) > 0.0
        }
        disabled_uavs = {
            str(event.get("uav_id")) for event in events
            if event.get("event_type") == "pesticide_disabled"
        }
        for uav_id in self.uav_slots:
            if (
                self.resources.uav(uav_id).onboard_l <= 1e-12
                and uav_id not in productive_uavs
                and uav_id not in disabled_uavs
            ):
                events.append({"event_type": "pesticide_disabled", "duration_s": self.decision_dt_s, "uav_id": uav_id, "step": self._decision_step})
        self._refresh_request_candidates()
        events.append({"event_type": "field_updated", "step": self._decision_step})
        self._refresh_state(events=events)
        return self.state

    def _masks(self) -> dict[str, ActionMask]:
        masks: dict[str, ActionMask] = {}
        for uav_id in self.uav_slots:
            state = self.resources.uav(uav_id)
            committed = uav_id == self._committed_uav_id
            masks[uav_id] = uav_action_mask(
                self.uav_positions.get(uav_id, (0, 0)),
                self.uav_grid_shape,
                onboard_l=state.onboard_l,
                spray_flow_l_s=state.spray_flow_l_s,
                locked=(uav_id == self._locked_uav_id or uav_id in self._uav_transit),
                rendezvous_target=self._service_target_uav_cell if committed else None,
                must_approach=committed and self._must_approach_rendezvous(uav_id),
            )
        for vehicle_id in self.vehicle_slots:
            routes = self._candidate_routes.get(vehicle_id, {})
            current_node = self.executors[vehicle_id].current_node
            candidates = [
                self._candidate_records.get(vehicle_id, {}).get(f"slot-{index}")
                or (route if route is not None and route[0] == current_node else None)
                for index in range(self.max_candidate_slots)
                for route in (routes.get(f"slot-{index}"),)
            ]
            masks[vehicle_id] = vehicle_action_mask(locked=(vehicle_id in {self._locked_vehicle_id, self._committed_vehicle_id} or self.executors[vehicle_id].route_index < len(self.executors[vehicle_id].route) - 1), candidate_slots=candidates, max_slots=self.max_candidate_slots, inventory_l=self.resources.vehicle(vehicle_id).inventory_l, service_cap_l=self.resources.vehicle(vehicle_id).service_cap_l)
        return masks

    def _refresh_state(self, *, events: list[dict[str, object]]) -> None:
        self._state = DecisionState(
            role_slots={"uav": self.uav_slots, "vehicle": self.vehicle_slots},
            action_masks=self._masks(),
            events=list(events),
            vehicle_nodes={key: executor.current_node for key, executor in self.executors.items()},
            uav_positions=dict(self.uav_positions),
            candidate_mapping=self._candidate_mapping_snapshot(),
            candidate_features=self._candidate_features_snapshot(),
        )

    def _candidate_mapping_snapshot(self) -> dict[str, tuple[tuple[str, str], ...]]:
        return {
            vehicle_id: tuple(sorted(self._candidate_mapping_keys.get(vehicle_id, {}).items()))
            for vehicle_id in self.vehicle_slots
        }

    def _candidate_features_snapshot(self) -> dict[str, tuple[dict[str, object], ...]]:
        result: dict[str, tuple[dict[str, object], ...]] = {}
        for vehicle_id in self.vehicle_slots:
            rows = []
            for slot, candidate in sorted(self._candidate_records.get(vehicle_id, {}).items()):
                request = self.request_manager.get(candidate.request_id)
                urgency = float(candidate.urgency)
                if not isfinite(urgency):
                    urgency = 1_000_000.0
                rows.append(
                    {
                        "slot": slot,
                        "mapping_key": candidate.mapping_key,
                        "request_id": candidate.request_id,
                        "uav_id": candidate.uav_id,
                        "road_node_id": candidate.road_node_id,
                        "remaining_l": float(request.remaining_l),
                        "urgency": min(max(urgency, 0.0), 1_000_000.0),
                        "road_distance_m": float(candidate.road_distance_m),
                        "uav_distance_m": float(candidate.uav_distance_m),
                        "uav_eta_s": float(candidate.uav_eta_s),
                        "vehicle_ready_eta_s": float(candidate.vehicle_ready_eta_s),
                        "joint_arrival_eta_s": float(candidate.joint_arrival_eta_s),
                        "uav_wait_s": float(candidate.uav_wait_s),
                        "vehicle_wait_s": float(candidate.vehicle_wait_s),
                        "pesticide_disabled_expected": bool(candidate.pesticide_disabled_expected),
                    }
                )
            result[vehicle_id] = tuple(rows)
        return result

    def _uav_metric_position(self, uav_id: str) -> tuple[float, float]:
        return self._uav_metric_positions[uav_id]

    def _uav_route_distance_m(
        self,
        uav_id: str,
        target_metric: tuple[float, float],
    ) -> float:
        """Return executable four-connected distance, including in-edge travel."""

        transit = self._uav_transit.get(uav_id)
        if transit is None:
            origin_x, origin_y = self._uav_metric_positions[uav_id]
            committed_distance_m = 0.0
        else:
            origin_x, origin_y = transit["target_metric"]
            committed_distance_m = float(transit["remaining_m"])
        return committed_distance_m + abs(float(target_metric[0]) - float(origin_x)) + abs(
            float(target_metric[1]) - float(origin_y)
        )

    def _start_uav_transit(
        self,
        uav_id: str,
        target_cell: tuple[int, int],
        action: str,
    ) -> None:
        row_size_m, col_size_m = self.uav_cell_size_m
        target_metric = (
            float(target_cell[1]) * col_size_m,
            float(target_cell[0]) * row_size_m,
        )
        current_metric = self._uav_metric_positions[uav_id]
        remaining_m = hypot(
            target_metric[0] - current_metric[0],
            target_metric[1] - current_metric[1],
        )
        self._uav_transit[uav_id] = {
            "action": action,
            "target_cell": target_cell,
            "target_metric": target_metric,
            "remaining_m": remaining_m,
            "rendezvous_committed": uav_id == self._committed_uav_id,
        }

    def _advance_uav_transit(
        self,
        uav_id: str,
        events: list[dict[str, object]],
    ) -> None:
        transit = self._uav_transit[uav_id]
        current_x, current_y = self._uav_metric_positions[uav_id]
        target_x, target_y = transit["target_metric"]
        remaining_m = float(transit["remaining_m"])
        travelled_m = min(remaining_m, self.uav_speed_mps * self.decision_dt_s)
        route_complete = travelled_m + 1e-12 >= remaining_m
        if route_complete:
            self._uav_metric_positions[uav_id] = (float(target_x), float(target_y))
            self.uav_positions[uav_id] = tuple(transit["target_cell"])
            del self._uav_transit[uav_id]
            remaining_after_m = 0.0
        else:
            fraction = travelled_m / remaining_m
            self._uav_metric_positions[uav_id] = (
                current_x + (float(target_x) - current_x) * fraction,
                current_y + (float(target_y) - current_y) * fraction,
            )
            remaining_after_m = remaining_m - travelled_m
            transit["remaining_m"] = remaining_after_m
        events.append({
            "event_type": "uav_movement_applied",
            "uav_id": uav_id,
            "distance_m": travelled_m,
            "remaining_edge_distance_m": remaining_after_m,
            "route_complete": route_complete,
            "rendezvous_committed": bool(transit["rendezvous_committed"]),
            "step": self._decision_step,
        })

    def _dynamic_request_trigger(self, uav_id: str) -> dict[str, float] | None:
        if not self.dynamic_request_enabled:
            return None
        uav = self.resources.uav(uav_id)
        gap_l = max(0.0, uav.capacity_l - uav.onboard_l)
        if gap_l <= 1e-12:
            return None
        # The trigger forecasts when service is needed, while the request
        # volume remains the auditable free tank capacity at creation time.
        # Forecasting extra consumption here can leave a request open after
        # the UAV has already been filled to capacity.
        requested_l = gap_l
        remaining_work_s = remaining_work_time_s(
            onboard_l=uav.onboard_l,
            spray_flow_l_s=uav.spray_flow_l_s,
        )
        if self.support_mode == "teleport":
            # Teleport is a diagnostic upper bound for spatial-temporal
            # mismatch. It removes road travel and service setup delay while
            # retaining one decision interval and the declared safety margin.
            required_response_s = self.decision_dt_s + self.request_safety_margin_s
            if remaining_work_s > required_response_s + 1e-12:
                return None
            return {
                "remaining_work_s": remaining_work_s,
                "required_response_s": required_response_s,
                "safety_margin_s": self.request_safety_margin_s,
                "target_l": requested_l,
            }
        points = self._rendezvous_points(
            uav_id,
            include_all_nodes=self.support_mode != "fixed",
        )
        required_response_s = float("inf")
        for vehicle_id, executor in self.executors.items():
            vehicle = self.resources.vehicle(vehicle_id)
            transfer_l = min(requested_l, vehicle.inventory_l, vehicle.service_cap_l)
            if transfer_l <= 1e-12 or not points:
                continue
            candidates = generate_rendezvous_candidates(
                points,
                graph=self.road_graph,
                vehicle_node=executor.current_node,
                vehicle_speed_mps=self.vehicle_speed_mps,
                uav_speed_mps=self.uav_speed_mps,
                remaining_work_s=remaining_work_s,
                requested_l=requested_l,
                vehicle_inventory_l=vehicle.inventory_l,
                service_cap_l=vehicle.service_cap_l,
                service_setup_s=self.service_setup_s,
                transfer_rate_l_s=vehicle.transfer_rate_l_s,
                rendezvous_radius_m=self.rendezvous_radius_m,
                request_id="request-probe",
                uav_id=uav_id,
                allow_late_service=True,
            )
            feasible = [candidate for candidate in candidates if candidate.feasible]
            if not feasible:
                continue
            arrival_s = min(candidate.joint_arrival_eta_s for candidate in feasible)
            service_s = self.service_setup_s + transfer_l / vehicle.transfer_rate_l_s
            required_response_s = min(
                required_response_s,
                arrival_s + service_s + self.request_safety_margin_s,
            )
        if required_response_s == float("inf"):
            return None
        if remaining_work_s > required_response_s + 1e-12:
            return None
        return {
            "remaining_work_s": remaining_work_s,
            "required_response_s": required_response_s,
            "safety_margin_s": self.request_safety_margin_s,
            "target_l": requested_l,
        }

    def road_node_to_uav_cell(self, node_id: str) -> tuple[int, int]:
        """Map one metric road node to the shared UAV grid coordinate frame."""
        x_m, y_m = self.road_graph.nodes[node_id]
        row_size_m, col_size_m = self.uav_cell_size_m
        row = min(max(int(round(y_m / row_size_m)), 0), self.uav_grid_shape[0] - 1)
        col = min(max(int(round(x_m / col_size_m)), 0), self.uav_grid_shape[1] - 1)
        return row, col

    def _uav_has_arrived(self, uav_id: str) -> bool:
        if self._service_target_node is None:
            return False
        uav_x, uav_y = self._uav_metric_position(uav_id)
        target_x, target_y = self.road_graph.nodes[self._service_target_node]
        return hypot(target_x - uav_x, target_y - uav_y) <= self.rendezvous_radius_m + 1e-12

    def _must_approach_rendezvous(self, uav_id: str) -> bool:
        if self._service_target_node is None or self._service_target_uav_cell is None:
            return False
        if not self.endurance_prediction_enabled:
            return False
        uav = self.resources.uav(uav_id)
        remaining_s = remaining_work_time_s(
            onboard_l=uav.onboard_l,
            spray_flow_l_s=uav.spray_flow_l_s,
        )
        row_size_m, col_size_m = self.uav_cell_size_m
        target_metric = (
            float(self._service_target_uav_cell[1]) * col_size_m,
            float(self._service_target_uav_cell[0]) * row_size_m,
        )
        travel_s = self._uav_route_distance_m(uav_id, target_metric) / self.uav_speed_mps
        return remaining_s <= travel_s + self.service_setup_s + self.decision_dt_s

    def _rendezvous_points(
        self,
        uav_id: str,
        *,
        include_all_nodes: bool = False,
    ) -> tuple[RendezvousPoint, ...]:
        points = []
        if self.support_mode == "fixed" and not include_all_nodes:
            fixed_nodes = {self.initial_vehicle_nodes[vehicle_id] for vehicle_id in self.vehicle_slots}
            node_items = sorted((node_id, self.road_graph.nodes[node_id]) for node_id in fixed_nodes)
        else:
            node_items = sorted(self.road_graph.nodes.items())
        for node_id, position in node_items:
            target_cell = self.road_node_to_uav_cell(node_id)
            row_size_m, col_size_m = self.uav_cell_size_m
            target_metric = (
                float(target_cell[1]) * col_size_m,
                float(target_cell[0]) * row_size_m,
            )
            service_separation_m = hypot(
                position[0] - target_metric[0],
                position[1] - target_metric[1],
            )
            if service_separation_m <= self.rendezvous_radius_m + 1e-12:
                distance_m = self._uav_route_distance_m(uav_id, target_metric)
                points.append(
                    RendezvousPoint(
                        point_id=f"rv-{node_id}",
                        road_node_id=node_id,
                        position=target_metric,
                        distance_m=distance_m,
                        service_separation_m=service_separation_m,
                    )
                )
        return tuple(points)

    def _refresh_request_candidates(self) -> None:
        if not self.executors:
            return
        if self.support_mode in {"disabled", "teleport"}:
            for vehicle_id in self.vehicle_slots:
                self._candidate_routes[vehicle_id] = {}
                self._candidate_request_ids[vehicle_id] = {}
                self._candidate_mapping_keys[vehicle_id] = {}
                self._candidate_records[vehicle_id] = {}
                self._candidate_target_cells[vehicle_id] = {}
            return
        open_requests = sorted(
            (request for request in self.request_manager.active_requests() if request.status is RequestStatus.OPEN),
            key=lambda item: (item.created_step, item.request_id),
        )
        for vehicle_id, executor in self.executors.items():
            if not open_requests and self._candidate_routes.get(vehicle_id):
                continue
            if executor.route_index < len(executor.route) - 1:
                # Never overwrite a route while the executor is carrying
                # residual edge distance; policies receive a locked mask.
                continue
            if self.service.phase is not ServicePhase.IDLE:
                continue
            self._candidate_request_ids[vehicle_id] = {}
            self._candidate_mapping_keys[vehicle_id] = {}
            self._candidate_records[vehicle_id] = {}
            self._candidate_target_cells[vehicle_id] = {}
            routes: dict[str, tuple[str, ...]] = {}
            selected: list[tuple[RendezvousCandidate, int]] = []
            vehicle = self.resources.vehicle(vehicle_id)
            for request in open_requests:
                points = self._rendezvous_points(request.uav_id)
                if not points:
                    continue
                uav = self.resources.uav(request.uav_id)
                remaining_work_s = (
                    remaining_work_time_s(
                        onboard_l=uav.onboard_l,
                        spray_flow_l_s=uav.spray_flow_l_s,
                    )
                    if self.endurance_prediction_enabled
                    else 1.0e12
                )
                candidates = generate_rendezvous_candidates(
                    points,
                    graph=self.road_graph,
                    vehicle_node=executor.current_node,
                    vehicle_speed_mps=self.vehicle_speed_mps,
                    uav_speed_mps=self.uav_speed_mps,
                    remaining_work_s=remaining_work_s,
                    requested_l=request.remaining_l,
                    vehicle_inventory_l=vehicle.inventory_l,
                    service_cap_l=vehicle.service_cap_l,
                    service_setup_s=self.service_setup_s,
                    transfer_rate_l_s=vehicle.transfer_rate_l_s,
                    rendezvous_radius_m=self.rendezvous_radius_m,
                    request_id=request.request_id,
                    uav_id=request.uav_id,
                    allow_late_service=True,
                )
                feasible = [candidate for candidate in candidates if candidate.feasible]
                if not feasible:
                    continue
                if self.joint_demand_rendezvous_enabled:
                    best = min(
                        feasible,
                        key=lambda candidate: (
                            candidate.joint_arrival_eta_s,
                            candidate.road_distance_m,
                            candidate.point_id,
                            candidate.road_node_id,
                        ),
                    )
                else:
                    best = min(
                        feasible,
                        key=lambda candidate: (
                            candidate.road_distance_m,
                            candidate.point_id,
                            candidate.road_node_id,
                        ),
                    )
                selected.append((best, request.created_step))
            if self.joint_demand_rendezvous_enabled:
                selected.sort(
                    key=lambda item: (
                        -item[0].urgency,
                        item[1],
                        item[0].joint_arrival_eta_s,
                        item[0].mapping_key,
                    )
                )
            else:
                selected.sort(
                    key=lambda item: (
                        item[1],
                        item[0].request_id,
                        item[0].road_distance_m,
                        item[0].mapping_key,
                    )
                )
            slots = build_candidate_action_slots(
                (candidate for candidate, _ in selected),
                max_slots=self.max_candidate_slots,
            )
            for slot_index, candidate in enumerate(slots.candidates):
                slot = f"slot-{slot_index}"
                path, _distance = shortest_path(
                    self.road_graph,
                    executor.current_node,
                    candidate.road_node_id,
                )
                routes[slot] = tuple(path)
                self._candidate_request_ids[vehicle_id][slot] = candidate.request_id
                self._candidate_mapping_keys[vehicle_id][slot] = candidate.mapping_key
                self._candidate_records[vehicle_id][slot] = candidate
                self._candidate_target_cells[vehicle_id][slot] = self.road_node_to_uav_cell(
                    candidate.road_node_id
                )
            self._candidate_routes[vehicle_id] = routes

    def _apply_teleport_service(self, events: list[dict[str, object]]) -> None:
        """Serve at most one FIFO request per step without travel or setup delay."""

        vehicle_id = self.vehicle_slots[0]
        vehicle = self.resources.vehicle(vehicle_id)
        if vehicle.inventory_l <= 0 or vehicle.service_cap_l <= 0:
            return
        open_requests = [
            request for request in self.request_manager.active_requests()
            if request.status is RequestStatus.OPEN
        ]
        if not open_requests:
            return
        request = min(open_requests, key=lambda item: (item.created_step, item.uav_id, item.request_id))
        reserved = self.request_manager.reserve_request(
            request.request_id, vehicle_id, self._decision_step,
        )
        if reserved is None:
            return
        self.request_manager.start_service(request.request_id, self._decision_step)
        transferred = self.resources.transfer(request.uav_id, vehicle_id, request.remaining_l)
        updated = self.request_manager.apply_transfer(
            request.request_id, transferred.amount_l, self._decision_step,
        )
        events.extend([
            {"event_type": "request_reserved", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "rendezvous_road_distance_m": 0.0, "mode": "teleport_diagnostic", "step": self._decision_step},
            {"event_type": "service_started", "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "mode": "teleport_diagnostic", "step": self._decision_step},
            {"event_type": "pesticide_transfer", "amount_l": transferred.amount_l, "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "mode": "teleport_diagnostic", "step": self._decision_step},
        ])
        if updated.status is RequestStatus.COMPLETED:
            events.append({"event_type": "request_completed", "request_id": request.request_id, "mode": "teleport_diagnostic", "step": self._decision_step})
        else:
            self.request_manager.reopen(request.request_id, self._decision_step)
            events.append({"event_type": "request_partially_satisfied", "request_id": request.request_id, "mode": "teleport_diagnostic", "step": self._decision_step})


__all__ = ["DecisionState", "HeterogeneousDecisionAdapter"]
