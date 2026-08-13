"""Small unit-conversion helpers used by the deterministic environment."""

from __future__ import annotations

import math


def volume_from_rate(rate_l_s: float, dt_s: float) -> float:
    if rate_l_s < 0 or dt_s < 0:
        raise ValueError("rates and durations must be non-negative")
    return rate_l_s * dt_s


def service_steps(setup_s: float, transfer_l: float, transfer_rate_l_s: float, dt_s: float) -> int:
    if min(setup_s, transfer_l, transfer_rate_l_s, dt_s) < 0:
        raise ValueError("service quantities must be non-negative")
    if dt_s == 0:
        raise ValueError("dt_s must be positive")
    transfer_time = 0.0 if transfer_l == 0 else transfer_l / transfer_rate_l_s
    return math.ceil((setup_s + transfer_time) / dt_s)
