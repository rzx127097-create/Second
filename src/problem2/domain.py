from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
import math
from typing import Any


class Action(IntEnum):
    STAY = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
    SPRAY = 5


class RequestStatus(str, Enum):
    PENDING = "pending"
    RESERVED = "reserved"
    SERVING = "serving"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VehicleMode(str, Enum):
    IDLE = "idle"
    TRANSIT = "transit"
    SERVING = "serving"


def _finite_nonnegative(value: float, name: str) -> None:
    if isinstance(value, bool) or not math.isfinite(float(value)) or value < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")


def _finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class UavState:
    uav_id: str
    x_m: float
    y_m: float
    pesticide_l: float
    active_request_id: str | None = None
    service_locked: bool = False

    def __post_init__(self) -> None:
        if not self.uav_id:
            raise ValueError("uav_id must be non-empty")
        _finite(self.x_m, "x_m")
        _finite(self.y_m, "y_m")
        _finite_nonnegative(self.pesticide_l, "pesticide_l")


@dataclass(frozen=True)
class VehicleState:
    vehicle_id: str
    current_node: int
    x_m: float
    y_m: float
    inventory_l: float
    inventory_depleted: bool = False
    mode: VehicleMode = VehicleMode.IDLE
    target_node: int | None = None
    direction: Action | None = None
    edge_progress_m: float = 0.0
    route_distance_m: float = 0.0
    active_request_id: str | None = None
    service_steps_elapsed: int = 0
    service_steps_required: int = 0
    planned_transfer_l: float = 0.0

    def __post_init__(self) -> None:
        if not self.vehicle_id:
            raise ValueError("vehicle_id must be non-empty")
        if self.current_node < 0:
            raise ValueError("current_node must be nonnegative")
        _finite(self.x_m, "x_m")
        _finite(self.y_m, "y_m")
        _finite_nonnegative(self.inventory_l, "inventory_l")
        _finite_nonnegative(self.edge_progress_m, "edge_progress_m")
        _finite_nonnegative(self.route_distance_m, "route_distance_m")
        _finite_nonnegative(self.planned_transfer_l, "planned_transfer_l")
        if self.service_steps_elapsed < 0 or self.service_steps_required < 0:
            raise ValueError("service step counters must be nonnegative")


@dataclass(frozen=True)
class ServiceRequest:
    request_id: str
    uav_id: str
    created_step: int
    requested_l: float
    status: RequestStatus = RequestStatus.PENDING
    reserved_vehicle_id: str | None = None

    def __post_init__(self) -> None:
        if not self.request_id or not self.uav_id:
            raise ValueError("request and UAV IDs must be non-empty")
        if self.created_step < 0:
            raise ValueError("created_step must be nonnegative")
        _finite_nonnegative(self.requested_l, "requested_l")


@dataclass(frozen=True)
class Event:
    step: int
    phase: str
    kind: str
    entity_id: str
    payload: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class EpisodeState:
    step: int
    uavs: tuple[UavState, ...]
    vehicle: VehicleState
    requests: tuple[ServiceRequest, ...] = ()
    ledger: Any = None
    last_step_events: tuple[Event, ...] = ()
    terminated: bool = False

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("step must be nonnegative")
        ids = [uav.uav_id for uav in self.uavs]
        if len(ids) != len(set(ids)):
            raise ValueError("UAV IDs must be unique")
