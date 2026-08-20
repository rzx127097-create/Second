from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Iterable

from problem2.domain import Event, UavState


class ResourceInvariantError(ValueError):
    """Raised before publishing a non-finite or non-conserved transaction."""


@dataclass(frozen=True)
class ResourceLedger:
    initial_total_l: float
    cumulative_sprayed_l: float = 0.0
    cumulative_transferred_l: float = 0.0
    events: tuple[Event, ...] = ()


def _finite_nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)) or value < 0.0:
        raise ResourceInvariantError(f"{name} must be finite and nonnegative")
    return float(value)


def new_ledger(
    uavs: Iterable[UavState], vehicle_inventory_l: float
) -> ResourceLedger:
    inventory = _finite_nonnegative(vehicle_inventory_l, "vehicle_inventory_l")
    initial_total = math.fsum(uav.pesticide_l for uav in uavs) + inventory
    return ResourceLedger(initial_total_l=initial_total)


def assert_conserved(
    uavs: Iterable[UavState],
    vehicle_inventory_l: float,
    ledger: ResourceLedger,
    tolerance: float,
) -> None:
    inventory = _finite_nonnegative(vehicle_inventory_l, "vehicle_inventory_l")
    allowed_error = _finite_nonnegative(tolerance, "tolerance")
    observed = math.fsum(uav.pesticide_l for uav in uavs) + inventory
    expected = ledger.initial_total_l - ledger.cumulative_sprayed_l
    error = abs(observed - expected)
    if error > allowed_error:
        raise ResourceInvariantError(
            "pesticide conservation failed: "
            f"expected {expected:.17g} L, observed {observed:.17g} L, "
            f"error {error:.17g} L"
        )


def apply_spray(
    uav: UavState,
    ledger: ResourceLedger,
    requested_l: float,
    *,
    step: int = 0,
) -> tuple[UavState, ResourceLedger, Event]:
    requested = _finite_nonnegative(requested_l, "requested_l")
    actual = min(uav.pesticide_l, requested)
    updated_uav = replace(uav, pesticide_l=uav.pesticide_l - actual)
    event = Event(
        step=step,
        phase="spray",
        kind="spray",
        entity_id=uav.uav_id,
        payload=(
            ("after_l", updated_uav.pesticide_l),
            ("before_l", uav.pesticide_l),
            ("delta_l", actual),
            ("requested_l", requested),
        ),
    )
    updated_ledger = replace(
        ledger,
        cumulative_sprayed_l=ledger.cumulative_sprayed_l + actual,
        events=ledger.events + (event,),
    )
    return updated_uav, updated_ledger, event


def apply_transfer(
    uav: UavState,
    vehicle_inventory_l: float,
    ledger: ResourceLedger,
    service_cap_l: float,
    usable_capacity_l: float,
    *,
    step: int = 0,
) -> tuple[UavState, float, ResourceLedger, Event]:
    inventory = _finite_nonnegative(vehicle_inventory_l, "vehicle_inventory_l")
    service_cap = _finite_nonnegative(service_cap_l, "service_cap_l")
    capacity = _finite_nonnegative(usable_capacity_l, "usable_capacity_l")
    if uav.pesticide_l > capacity:
        raise ResourceInvariantError(
            f"UAV pesticide {uav.pesticide_l} exceeds usable capacity {capacity}"
        )
    gap = capacity - uav.pesticide_l
    actual = min(gap, service_cap, inventory)
    updated_uav = replace(uav, pesticide_l=uav.pesticide_l + actual)
    updated_inventory = inventory - actual
    event = Event(
        step=step,
        phase="transfer",
        kind="transfer",
        entity_id=uav.uav_id,
        payload=(
            ("delta_l", actual),
            ("uav_after_l", updated_uav.pesticide_l),
            ("uav_before_l", uav.pesticide_l),
            ("vehicle_after_l", updated_inventory),
            ("vehicle_before_l", inventory),
        ),
    )
    updated_ledger = replace(
        ledger,
        cumulative_transferred_l=ledger.cumulative_transferred_l + actual,
        events=ledger.events + (event,),
    )
    return updated_uav, updated_inventory, updated_ledger, event
