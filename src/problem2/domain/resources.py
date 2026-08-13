"""Pesticide accounting with explicit conservation and bounded transfers."""

from __future__ import annotations

from dataclasses import dataclass

from .state import UAVState, VehicleState
from .types import ResourceInvariantError, SprayResult, TransferResult
from .units import volume_from_rate


@dataclass
class PesticideResources:
    uavs: dict[str, UAVState]
    vehicles: dict[str, VehicleState]

    def __post_init__(self) -> None:
        self._initial_total_l = self.total_pesticide_l
        self._cumulative_sprayed_l = 0.0

    def uav(self, uav_id: str) -> UAVState:
        return self.uavs[uav_id]

    def vehicle(self, vehicle_id: str) -> VehicleState:
        return self.vehicles[vehicle_id]

    @property
    def total_pesticide_l(self) -> float:
        return sum(item.onboard_l for item in self.uavs.values()) + sum(
            item.inventory_l for item in self.vehicles.values()
        )

    def transfer(self, uav_id: str, vehicle_id: str, requested_l: float) -> TransferResult:
        if requested_l < 0:
            raise ResourceInvariantError("requested transfer must be non-negative")
        uav = self.uav(uav_id)
        vehicle = self.vehicle(vehicle_id)
        free_before = max(0.0, uav.capacity_l - uav.onboard_l)
        inventory_before = vehicle.inventory_l
        amount = min(requested_l, free_before, inventory_before, vehicle.service_cap_l)
        uav.onboard_l += amount
        vehicle.inventory_l -= amount
        self._clamp_state(uav, vehicle)
        return TransferResult(amount, free_before, inventory_before)

    def spray(self, uav_id: str, amount_l: float) -> SprayResult:
        if amount_l < 0:
            raise ResourceInvariantError("spray amount must be non-negative")
        uav = self.uav(uav_id)
        amount = min(amount_l, uav.onboard_l)
        limited = amount + 1e-12 < amount_l
        uav.onboard_l -= amount
        self._cumulative_sprayed_l += amount
        self._clamp_state(uav)
        return SprayResult(amount, limited)

    def spray_step(self, uav_id: str, dt_s: float) -> SprayResult:
        uav = self.uav(uav_id)
        return self.spray(uav_id, volume_from_rate(uav.spray_flow_l_s, dt_s))

    def assert_conservation(self, tolerance: float = 1e-9) -> None:
        current = self.total_pesticide_l
        sprayed = getattr(self, "_cumulative_sprayed_l", 0.0)
        if abs(current + sprayed - self._initial_total_l) > tolerance:
            raise AssertionError(
                "pesticide conservation violated: "
                f"initial={self._initial_total_l}, current={current}, sprayed={sprayed}"
            )

    def _clamp_state(self, *states: UAVState | VehicleState) -> None:
        for state in states:
            if isinstance(state, UAVState):
                if state.onboard_l < -1e-10 or state.onboard_l > state.capacity_l + 1e-10:
                    raise ResourceInvariantError("UAV pesticide bound violated")
                state.onboard_l = max(0.0, min(state.capacity_l, state.onboard_l))
            else:
                if state.inventory_l < -1e-10 or state.inventory_l > state.capacity_l + 1e-10:
                    raise ResourceInvariantError("vehicle inventory bound violated")
                state.inventory_l = max(0.0, min(state.capacity_l, state.inventory_l))
