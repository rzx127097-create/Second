"""ETA calculations in physical seconds."""

from __future__ import annotations

from math import ceil


def eta_seconds(distance_m: float, speed_mps: float) -> float:
    if distance_m < 0:
        raise ValueError("distance_m must be non-negative")
    if speed_mps <= 0:
        raise ValueError("speed_mps must be positive")
    return distance_m / speed_mps


def eta_steps(distance_m: float, speed_mps: float, dt_s: float) -> int:
    if dt_s <= 0:
        raise ValueError("dt_s must be positive")
    return int(ceil(eta_seconds(distance_m, speed_mps) / dt_s))


def eta(*args, **kwargs) -> float:
    return eta_seconds(*args, **kwargs)

