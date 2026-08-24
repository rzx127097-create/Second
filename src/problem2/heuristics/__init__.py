"""Observable-only vehicle dispatch controller interfaces for G5."""

from __future__ import annotations

from dataclasses import dataclass
import math

from problem2.domain import VehicleState
from problem2.road.models import RasterRoadGraph
from problem2.road.search import NoPathError


@dataclass(frozen=True)
class ObservableRequest:
    request_id: str
    uav_id: str
    slot: int
    created_step: int
    requested_l: float
    pesticide_l: float
    usable_capacity_l: float
    endurance_steps: float
    service_nodes: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.request_id or not self.uav_id:
            raise ValueError("observable request identities must be non-empty")
        if isinstance(self.slot, bool) or not isinstance(self.slot, int) or not 0 <= self.slot < 4:
            raise ValueError("observable request slot must be in [0, 3]")
        if isinstance(self.created_step, bool) or not isinstance(self.created_step, int) or self.created_step < 0:
            raise ValueError("observable request created_step must be nonnegative")
        for name in (
            "requested_l",
            "pesticide_l",
            "usable_capacity_l",
            "endurance_steps",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        nodes = tuple(self.service_nodes)
        if any(isinstance(node, bool) or not isinstance(node, int) or node < 0 for node in nodes):
            raise ValueError("service nodes must be nonnegative integers")
        object.__setattr__(self, "service_nodes", nodes)


@dataclass(frozen=True)
class DispatchObservation:
    step: int
    graph: RasterRoadGraph
    vehicle: VehicleState
    requests: tuple[ObservableRequest, ...]
    candidate_mapping: tuple[str | None, ...]
    service_cap_l: float
    tolerance: float
    active_request_id: str | None = None
    active_sampled_slot: int | None = None
    selected_service_node: int | None = None
    vehicle_speed_mps: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.step, bool) or not isinstance(self.step, int) or self.step < 0:
            raise ValueError("dispatch step must be a nonnegative integer")
        requests = tuple(self.requests)
        mapping = tuple(self.candidate_mapping)
        if len(mapping) != 4:
            raise ValueError("candidate mapping must contain exactly four slots")
        if len({item.request_id for item in requests}) != len(requests):
            raise ValueError("observable request identities must be unique")
        for request in requests:
            if mapping[request.slot] != request.request_id:
                raise ValueError("candidate mapping must preserve request slot identity")
        for name in ("service_cap_l", "tolerance", "vehicle_speed_mps"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.vehicle_speed_mps <= 0.0:
            raise ValueError("vehicle_speed_mps must be positive")
        active_values = (
            self.active_request_id,
            self.active_sampled_slot,
            self.selected_service_node,
        )
        if any(value is not None for value in active_values):
            if any(value is None for value in active_values):
                raise ValueError("active dispatch fields must be supplied together")
            if not 1 <= int(self.active_sampled_slot) <= 4:
                raise ValueError("active sampled slot must be in [1, 4]")
            if mapping[int(self.active_sampled_slot) - 1] != self.active_request_id:
                raise ValueError("active dispatch must preserve its original slot mapping")
        object.__setattr__(self, "requests", requests)
        object.__setattr__(self, "candidate_mapping", mapping)


@dataclass(frozen=True)
class ControllerDecision:
    sampled_slot: int
    request_id: str | None
    selected_service_node: int | None
    route_length_m: float
    decision_runtime_s: float
    replanned: bool = False
    plan_version: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.sampled_slot, bool) or not isinstance(self.sampled_slot, int) or not 0 <= self.sampled_slot <= 4:
            raise ValueError("sampled slot must be in [0, 4]")
        for name in ("route_length_m", "decision_runtime_s"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if type(self.replanned) is not bool:
            raise ValueError("replanned must be boolean")
        if (
            isinstance(self.plan_version, bool)
            or not isinstance(self.plan_version, int)
            or self.plan_version < 0
        ):
            raise ValueError("plan_version must be a nonnegative integer")
        if self.sampled_slot == 0:
            if self.request_id is not None or self.selected_service_node is not None:
                raise ValueError("hold decisions cannot identify a request or service node")
        elif self.request_id is None or self.selected_service_node is None:
            raise ValueError("dispatch decisions require a request and service node")


def hold_decision(runtime_s: float) -> ControllerDecision:
    return ControllerDecision(0, None, None, 0.0, runtime_s)


def feasible_request_options(
    observation: DispatchObservation,
    distance_function,
) -> list[tuple[ObservableRequest, int, float]]:
    if observation.vehicle.inventory_l <= observation.tolerance:
        return []
    options: list[tuple[ObservableRequest, int, float]] = []
    for request in observation.requests:
        transferable = min(
            request.requested_l,
            max(0.0, request.usable_capacity_l - request.pesticide_l),
            observation.service_cap_l,
            observation.vehicle.inventory_l,
        )
        if transferable <= observation.tolerance:
            continue
        candidates: list[tuple[float, int]] = []
        for node in request.service_nodes:
            try:
                distance = float(
                    distance_function(
                        observation.graph, observation.vehicle.current_node, node
                    )
                )
            except (NoPathError, IndexError, KeyError):
                continue
            candidates.append((distance, node))
        if candidates:
            distance, node = min(candidates, key=lambda item: (item[0], item[1]))
            options.append((request, node, distance))
    return options


from problem2.heuristics.astar import RollingAStarController  # noqa: E402
from problem2.heuristics.fixed import FixedSupportController  # noqa: E402
from problem2.heuristics.nearest import NearestRequestController  # noqa: E402
from problem2.heuristics.two_stage import TwoStageSchedule  # noqa: E402
from problem2.heuristics.urgency import UrgencyController  # noqa: E402


__all__ = [
    "ControllerDecision",
    "DispatchObservation",
    "FixedSupportController",
    "NearestRequestController",
    "ObservableRequest",
    "RollingAStarController",
    "TwoStageSchedule",
    "UrgencyController",
]
