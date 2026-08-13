"""Hard service-feasibility predicates."""

from __future__ import annotations


def is_serviceable(
    distance_m: float,
    rendezvous_radius_m: float,
    vehicle_inventory_l: float,
    requested_l: float | None = None,
    service_cap_l: float | None = None,
) -> bool:
    """Whether a UAV can be served at a rendezvous point right now."""

    values = (distance_m, rendezvous_radius_m, vehicle_inventory_l)
    if any(value < 0 for value in values):
        raise ValueError("distance and service limits must be non-negative")
    if requested_l is not None and requested_l < 0:
        raise ValueError("requested_l must be non-negative")
    if service_cap_l is not None and service_cap_l < 0:
        raise ValueError("service_cap_l must be non-negative")
    if distance_m > rendezvous_radius_m + 1e-12 or vehicle_inventory_l <= 0:
        return False
    if requested_l is not None and requested_l > 0 and service_cap_l is not None:
        return service_cap_l > 0
    return True


def service_feasible(*args, **kwargs) -> bool:
    return is_serviceable(*args, **kwargs)

