"""Role-slot adapter with road-constrained replenishment service events."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from math import hypot

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
        service_setup_s: float = 10.0,
        rendezvous_radius_m: float = 5.0,
        max_candidate_slots: int = 4,
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
        if service_setup_s < 0 or rendezvous_radius_m < 0 or max_candidate_slots < 1:
            raise ValueError("invalid service configuration")
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
        self.service_setup_s = float(service_setup_s)
        self.rendezvous_radius_m = float(rendezvous_radius_m)
        self.max_candidate_slots = int(max_candidate_slots)
        self.executors: dict[str, RoadVehicleExecutor] = {}
        self.uav_positions: dict[str, tuple[int, int]] = {}
        self._candidate_routes: dict[str, dict[str, tuple[str, ...]]] = {}
        self._candidate_request_ids: dict[str, dict[str, str]] = {}
        self._candidate_mapping_keys: dict[str, dict[str, str]] = {}
        self._candidate_records: dict[str, dict[str, RendezvousCandidate]] = {}
        self._candidate_target_cells: dict[str, dict[str, tuple[int, int]]] = {}
        self._locked_uav_id: str | None = None
        self._locked_vehicle_id: str | None = None
        self._service_target_node: str | None = None
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
        self._service_target_node = None
        start = sorted(self.road_graph.nodes)[0]
        self.executors = {
            vehicle_id: RoadVehicleExecutor(self.road_graph, current_node=start, speed_mps=self.vehicle_speed_mps)
            for vehicle_id in self.vehicle_slots
        }
        self.uav_positions = {uav_id: (0, 0) for uav_id in self.uav_slots}
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
            slot: self._road_node_to_uav_cell(route[-1]) for slot, route in routes.items()
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
            position = self.uav_positions[uav_id]
            if action in {"up", "down", "left", "right"}:
                self.uav_positions[uav_id] = legal_uav_position(position, action, self.uav_grid_shape, locked=uav_id == self._locked_uav_id)
            elif action == "spray" and uav_id != self._locked_uav_id:
                sprayed = self.resources.spray_step(uav_id, self.decision_dt_s)
                events.append({"event_type": "spray_applied", "uav_id": uav_id, "amount_l": sprayed.amount_l, "pesticide_limited": sprayed.pesticide_limited, "step": self._decision_step})

        for uav_id in self.uav_slots:
            state = self.resources.uav(uav_id)
            if self.request_threshold_ratio > 0 and state.onboard_l <= state.capacity_l * self.request_threshold_ratio + 1e-12:
                before = len(self.request_manager)
                request = self.request_manager.create_request(uav_id, state.capacity_l - state.onboard_l, self._decision_step)
                if len(self.request_manager) > before:
                    events.append({"event_type": "request_created", "request_id": request.request_id, "uav_id": uav_id, "amount_l": request.requested_l, "step": self._decision_step})
        for vehicle_id, executor in self.executors.items():
            action = actions[vehicle_id]
            if vehicle_id != self._locked_vehicle_id and action.startswith("slot-"):
                route = self._candidate_routes.get(vehicle_id, {}).get(action)
                request_id = self._candidate_request_ids.get(vehicle_id, {}).get(action)
                if route is not None:
                    executor.set_route(route)
                if request_id is not None and self.service.phase is ServicePhase.IDLE:
                    reserved = self.service.reserve_specific(self.request_manager, request_id, vehicle_id, self._decision_step, self.service_setup_s)
                    if reserved is not None and reserved.request_id == request_id:
                        self._service_target_node = route[-1] if route else None
                        self._locked_uav_id = reserved.uav_id
                        self._locked_vehicle_id = vehicle_id
                        events.append({"event_type": "request_reserved", "request_id": reserved.request_id, "uav_id": reserved.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
            advance = executor.advance(dt_s=self.decision_dt_s)
            events.append({"event_type": "movement_applied", "vehicle_id": vehicle_id, "travelled_distance_m": advance.travelled_distance_m, "remaining_edge_distance_m": advance.remaining_edge_distance_m, "route_complete": advance.route_complete, "step": self._decision_step})

        active_request_id = self.service.request_id
        if active_request_id is not None:
            request = self.request_manager.get(active_request_id)
            vehicle_id = self._locked_vehicle_id
            at_target = bool(vehicle_id and self._service_target_node and self.executors[vehicle_id].current_node == self._service_target_node)
            if not at_target:
                events.append({"event_type": "wait", "duration_s": self.decision_dt_s, "reason": "rendezvous_travel", "step": self._decision_step})
                events.append({"event_type": "pesticide_disabled", "duration_s": self.decision_dt_s, "uav_id": request.uav_id, "step": self._decision_step})
            else:
                previous_phase = self.service.phase
                transferred = self.service.tick(self.request_manager, self.resources, vehicle_id, self.decision_dt_s, self._decision_step)
                if previous_phase is ServicePhase.PREPARING:
                    events.append({"event_type": "wait", "duration_s": self.decision_dt_s, "reason": "service_setup", "step": self._decision_step})
                events.append({"event_type": "pesticide_disabled", "duration_s": self.decision_dt_s, "uav_id": request.uav_id, "step": self._decision_step})
                if transferred > 0:
                    events.append({"event_type": "pesticide_transfer", "amount_l": transferred, "request_id": request.request_id, "uav_id": request.uav_id, "vehicle_id": vehicle_id, "step": self._decision_step})
                if self.service.phase is ServicePhase.IDLE:
                    events.append({"event_type": "service_released", "request_id": request.request_id, "step": self._decision_step})
                    if request.status is RequestStatus.COMPLETED:
                        events.append({"event_type": "request_completed", "request_id": request.request_id, "step": self._decision_step})
                    self._locked_uav_id = None
                    self._locked_vehicle_id = None
                    self._service_target_node = None
        self._refresh_request_candidates()
        events.append({"event_type": "field_updated", "step": self._decision_step})
        self._refresh_state(events=events)
        return self.state

    def _masks(self) -> dict[str, ActionMask]:
        masks: dict[str, ActionMask] = {}
        for uav_id in self.uav_slots:
            state = self.resources.uav(uav_id)
            masks[uav_id] = uav_action_mask(self.uav_positions.get(uav_id, (0, 0)), self.uav_grid_shape, onboard_l=state.onboard_l, spray_flow_l_s=state.spray_flow_l_s, locked=uav_id == self._locked_uav_id)
        for vehicle_id in self.vehicle_slots:
            routes = self._candidate_routes.get(vehicle_id, {})
            current_node = self.executors[vehicle_id].current_node
            candidates = [
                self._candidate_records.get(vehicle_id, {}).get(f"slot-{index}")
                or (route if route is not None and route[0] == current_node else None)
                for index in range(self.max_candidate_slots)
                for route in (routes.get(f"slot-{index}"),)
            ]
            masks[vehicle_id] = vehicle_action_mask(locked=(vehicle_id == self._locked_vehicle_id or self.executors[vehicle_id].route_index < len(self.executors[vehicle_id].route) - 1), candidate_slots=candidates, max_slots=self.max_candidate_slots, inventory_l=self.resources.vehicle(vehicle_id).inventory_l, service_cap_l=self.resources.vehicle(vehicle_id).service_cap_l)
        return masks

    def _refresh_state(self, *, events: list[dict[str, object]]) -> None:
        self._state = DecisionState(role_slots={"uav": self.uav_slots, "vehicle": self.vehicle_slots}, action_masks=self._masks(), events=list(events), vehicle_nodes={key: executor.current_node for key, executor in self.executors.items()}, uav_positions=dict(self.uav_positions), candidate_mapping=self._candidate_mapping_snapshot())

    def _candidate_mapping_snapshot(self) -> dict[str, tuple[tuple[str, str], ...]]:
        return {
            vehicle_id: tuple(sorted(self._candidate_mapping_keys.get(vehicle_id, {}).items()))
            for vehicle_id in self.vehicle_slots
        }

    def _uav_metric_position(self, uav_id: str) -> tuple[float, float]:
        row, col = self.uav_positions[uav_id]
        row_size_m, col_size_m = self.uav_cell_size_m
        return float(col) * col_size_m, float(row) * row_size_m

    def _road_node_to_uav_cell(self, node_id: str) -> tuple[int, int]:
        x_m, y_m = self.road_graph.nodes[node_id]
        row_size_m, col_size_m = self.uav_cell_size_m
        row = min(max(int(round(y_m / row_size_m)), 0), self.uav_grid_shape[0] - 1)
        col = min(max(int(round(x_m / col_size_m)), 0), self.uav_grid_shape[1] - 1)
        return row, col

    def _rendezvous_points(self, uav_id: str) -> tuple[RendezvousPoint, ...]:
        uav_x, uav_y = self._uav_metric_position(uav_id)
        points = []
        for node_id, position in sorted(self.road_graph.nodes.items()):
            distance_m = hypot(position[0] - uav_x, position[1] - uav_y)
            if distance_m <= self.rendezvous_radius_m + 1e-12:
                points.append(
                    RendezvousPoint(
                        point_id=f"rv-{node_id}",
                        road_node_id=node_id,
                        position=position,
                        distance_m=distance_m,
                    )
                )
        return tuple(points)

    def _refresh_request_candidates(self) -> None:
        if not self.executors:
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
                candidates = generate_rendezvous_candidates(
                    points,
                    graph=self.road_graph,
                    vehicle_node=executor.current_node,
                    vehicle_speed_mps=self.vehicle_speed_mps,
                    uav_speed_mps=self.uav_speed_mps,
                    remaining_work_s=remaining_work_time_s(
                        onboard_l=uav.onboard_l,
                        spray_flow_l_s=uav.spray_flow_l_s,
                    ),
                    requested_l=request.remaining_l,
                    vehicle_inventory_l=vehicle.inventory_l,
                    service_cap_l=vehicle.service_cap_l,
                    service_setup_s=self.service_setup_s,
                    transfer_rate_l_s=vehicle.transfer_rate_l_s,
                    rendezvous_radius_m=self.rendezvous_radius_m,
                    request_id=request.request_id,
                    uav_id=request.uav_id,
                )
                feasible = [candidate for candidate in candidates if candidate.feasible]
                if not feasible:
                    continue
                best = min(
                    feasible,
                    key=lambda candidate: (
                        candidate.joint_arrival_eta_s,
                        candidate.road_distance_m,
                        candidate.point_id,
                        candidate.road_node_id,
                    ),
                )
                selected.append((best, request.created_step))
            selected.sort(
                key=lambda item: (
                    -item[0].urgency,
                    item[1],
                    item[0].joint_arrival_eta_s,
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
                self._candidate_target_cells[vehicle_id][slot] = self._road_node_to_uav_cell(
                    candidate.road_node_id
                )
            if not routes and not open_requests:
                for index, (node, _distance) in enumerate(self.road_graph.neighbors(executor.current_node)):
                    if index >= self.max_candidate_slots:
                        break
                    slot = f"slot-{index}"
                    routes[slot] = (executor.current_node, node)
                    self._candidate_mapping_keys[vehicle_id][slot] = f"reposition:{node}"
                    self._candidate_target_cells[vehicle_id][slot] = self._road_node_to_uav_cell(node)
            self._candidate_routes[vehicle_id] = routes


__all__ = ["DecisionState", "HeterogeneousDecisionAdapter"]
