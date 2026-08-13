"""Domain-level exceptions and immutable transfer records."""

from __future__ import annotations

from dataclasses import dataclass


class ResourceInvariantError(ValueError):
    """Raised when a resource state violates a physical bound."""


@dataclass(frozen=True)
class TransferResult:
    amount_l: float
    uav_free_capacity_before_l: float
    vehicle_inventory_before_l: float


@dataclass(frozen=True)
class SprayResult:
    amount_l: float
    pesticide_limited: bool
