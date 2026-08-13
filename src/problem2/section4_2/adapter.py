"""Role-slot and event-order adapter for the heterogeneous decision step."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping

import numpy as np

from problem2.domain.resources import PesticideResources
from problem2.environment.action_masks import ActionMask, uav_action_mask, vehicle_action_mask
from problem2.environment.movement import legal_uav_position
from problem2.road.graph import RoadGraph

from .road_executor import RoadVehicleExecutor


@dataclass(frozen=True)
class DecisionState:
    role_slots: dict[str, tuple[str, ...]]
    action_masks: dict[str, ActionMask]
    events: list[dict[str, object]]
    vehicle_nodes: dict[str, str]
    uav_positions: dict[str, tuple[int, int]]


class HeterogeneousDecisionAdapter:
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
    ) -> None:
        if not vehicle_slots:
            raise ValueError("at least one vehicle slot is required")
        if any(identifier not in resources.uavs for identifier in uav_slots):
            raise ValueError("unknown UAV slot")
        if any(identifier not in resources.vehicles for identifier in vehicle_slots):
            raise ValueError("unknown vehicle slot")
        if decision_dt_s <= 0:
            raise ValueError("decision_dt_s must be positive")
        if len(uav_grid_shape) != 2 or any(int(size) <= 0 for size in uav_grid_shape):
            raise ValueError("uav_grid_shape must contain two positive dimensions")
        self.resources = resources
        self._initial_uav_onboard = {
            identifier: float(resources.uav(identifier).onboard_l) for identifier in uav_slots
        }
        self._initial_vehicle_inventory = {
            identifier: float(resources.vehicle(identifier).inventory_l) for identifier in vehicle_slots
        }
        self.road_graph = road_graph
        self.uav_slots = tuple(uav_slots)
        self.vehicle_slots = tuple(vehicle_slots)
        self.vehicle_speed_mps = vehicle_speed_mps
        self.decision_dt_s = decision_dt_s
        self.uav_grid_shape = (int(uav_grid_shape[0]), int(uav_grid_shape[1]))
        self.executors: dict[str, RoadVehicleExecutor] = {}
        self.uav_positions: dict[str, tuple[int, int]] = {}
        self._candidate_routes: dict[str, dict[str, tuple[str, ...]]] = {}
        self._locked_uav_id: str | None = None
        self._locked_vehicle_id: str | None = None
        self._state: DecisionState | None = None

    @property
    def state(self) -> DecisionState:
        if self._state is None:
            raise RuntimeError("reset must be called before accessing state")
        return self._state

    def reset(self, *, seed: int | None = None) -> DecisionState:
        del seed  # adapter state is deterministic; scenario randomness belongs to the environment
        for identifier, amount in self._initial_uav_onboard.items():
            self.resources.uav(identifier).onboard_l = amount
        for identifier, amount in self._initial_vehicle_inventory.items():
            self.resources.vehicle(identifier).inventory_l = amount
        self.resources._initial_total_l = self.resources.total_pesticide_l
        self.resources._cumulative_sprayed_l = 0.0
        start = sorted(self.road_graph.nodes)[0]
        self.executors = {
            vehicle_id: RoadVehicleExecutor(self.road_graph, current_node=start, speed_mps=self.vehicle_speed_mps)
            for vehicle_id in self.vehicle_slots
        }
        self.uav_positions = {uav_id: (0, 0) for uav_id in self.uav_slots}
        self._locked_uav_id = None
        self._locked_vehicle_id = None
        masks = self._masks()
        self._state = DecisionState(
            role_slots={"uav": self.uav_slots, "vehicle": self.vehicle_slots},
            action_masks=masks,
            events=[],
            vehicle_nodes={vehicle_id: executor.current_node for vehicle_id, executor in self.executors.items()},
            uav_positions=dict(self.uav_positions),
        )
        return self._state

    def set_candidate_routes(
        self, vehicle_id: str, routes_by_slot: Mapping[str, Iterable[str]]
    ) -> None:
        """Register validated high-level slot-to-route mappings for one vehicle."""

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
            # Validate against the current node without mutating the active route.
            probe = RoadVehicleExecutor(
                self.road_graph,
                current_node=self.executors[vehicle_id].current_node,
                speed_mps=self.vehicle_speed_mps,
            )
            probe.set_route(values)
            routes[slot_name] = values
        self._candidate_routes[vehicle_id] = routes
        if self._state is not None:
            self._refresh_state(events=self._state.events)

    def set_service_lock(self, uav_id: str, vehicle_id: str) -> None:
        """Lock one UAV and vehicle to the current service relation."""

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
        events: list[dict[str, object]] = []
        masks = self._state.action_masks
        for agent_id, action in actions.items():
            mask = masks.get(agent_id)
            if mask is None or action not in mask.actions or not mask.mask[mask.actions.index(action)]:
                raise ValueError(f"action is not legal for {agent_id}: {action}")
        events.append({"event_type": "actions_validated"})
        for uav_id in self.uav_slots:
            action = actions.get(uav_id, "hold")
            position = self.uav_positions[uav_id]
            if action in {"up", "down", "left", "right"}:
                self.uav_positions[uav_id] = legal_uav_position(
                    position, action, self.uav_grid_shape,
                    locked=uav_id == self._locked_uav_id,
                )
            elif action == "spray" and uav_id != self._locked_uav_id:
                sprayed = self.resources.spray_step(uav_id, self.decision_dt_s)
                events.append({
                    "event_type": "spray_applied",
                    "uav_id": uav_id,
                    "amount_l": sprayed.amount_l,
                    "pesticide_limited": sprayed.pesticide_limited,
                })
        for vehicle_id, executor in self.executors.items():
            action = actions.get(vehicle_id, "hold")
            if vehicle_id != self._locked_vehicle_id and action.startswith("slot-"):
                route = self._candidate_routes.get(vehicle_id, {}).get(action)
                if route is not None:
                    executor.set_route(route)
            advance = executor.advance(dt_s=self.decision_dt_s)
            events.append({
                "event_type": "movement_applied",
                "vehicle_id": vehicle_id,
                "travelled_distance_m": advance.travelled_distance_m,
                "remaining_edge_distance_m": advance.remaining_edge_distance_m,
                "route_complete": advance.route_complete,
            })
        if not any(event["event_type"] == "movement_applied" for event in events):
            events.append({"event_type": "movement_applied"})
        events.append({"event_type": "field_updated"})
        self._refresh_state(events=events)
        return self._state

    def _masks(self) -> dict[str, ActionMask]:
        masks: dict[str, ActionMask] = {}
        for uav_id in self.uav_slots:
            state = self.resources.uav(uav_id)
            masks[uav_id] = uav_action_mask(
                self.uav_positions.get(uav_id, (0, 0)),
                self.uav_grid_shape,
                onboard_l=state.onboard_l,
                spray_flow_l_s=state.spray_flow_l_s,
                locked=uav_id == self._locked_uav_id,
            )
        for vehicle_id in self.vehicle_slots:
            routes = self._candidate_routes.get(vehicle_id)
            if routes:
                slot_count = max(int(slot.split("-", 1)[1]) for slot in routes) + 1
                candidates = [routes.get(f"slot-{index}") for index in range(slot_count)]
                masks[vehicle_id] = vehicle_action_mask(
                    locked=(
                        vehicle_id == self._locked_vehicle_id
                        or self.executors[vehicle_id].route_index < len(self.executors[vehicle_id].route) - 1
                    ),
                    candidate_slots=[{"valid": route is not None} for route in candidates],
                    max_slots=slot_count,
                    inventory_l=self.resources.vehicle(vehicle_id).inventory_l,
                    service_cap_l=self.resources.vehicle(vehicle_id).service_cap_l,
                )
            else:
                masks[vehicle_id] = vehicle_action_mask(
                    locked=(
                        vehicle_id == self._locked_vehicle_id
                        or self.executors[vehicle_id].route_index < len(self.executors[vehicle_id].route) - 1
                    )
                )
        return masks

    def _refresh_state(self, *, events: list[dict[str, object]]) -> None:
        self._state = DecisionState(
            role_slots={"uav": self.uav_slots, "vehicle": self.vehicle_slots},
            action_masks=self._masks(),
            events=events,
            vehicle_nodes={vehicle_id: executor.current_node for vehicle_id, executor in self.executors.items()},
            uav_positions=dict(self.uav_positions),
        )
