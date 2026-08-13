"""Mutable but validated resource state for UAVs and support vehicles."""

from __future__ import annotations

from dataclasses import dataclass

from .types import ResourceInvariantError


def _check_nonnegative(name: str, value: float) -> None:
    if value < -1e-12:
        raise ResourceInvariantError(f"{name} must be non-negative")


@dataclass
class UAVState:
    uav_id: str
    onboard_l: float
    capacity_l: float
    spray_flow_l_s: float

    def __post_init__(self) -> None:
        _check_nonnegative("onboard_l", self.onboard_l)
        _check_nonnegative("capacity_l", self.capacity_l)
        _check_nonnegative("spray_flow_l_s", self.spray_flow_l_s)
        if self.onboard_l > self.capacity_l + 1e-12:
            raise ResourceInvariantError("onboard_l cannot exceed capacity_l")


@dataclass
class VehicleState:
    vehicle_id: str
    inventory_l: float
    capacity_l: float
    transfer_rate_l_s: float
    service_cap_l: float

    def __post_init__(self) -> None:
        _check_nonnegative("inventory_l", self.inventory_l)
        _check_nonnegative("capacity_l", self.capacity_l)
        _check_nonnegative("transfer_rate_l_s", self.transfer_rate_l_s)
        _check_nonnegative("service_cap_l", self.service_cap_l)
        if self.inventory_l > self.capacity_l + 1e-12:
            raise ResourceInvariantError("inventory_l cannot exceed capacity_l")
