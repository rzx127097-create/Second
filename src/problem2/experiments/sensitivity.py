from __future__ import annotations

from typing import Mapping


SENSITIVITY_AXES = {
    "learning_rate": (1e-4, 3e-4, 5e-4),
    "clip_range": (0.10, 0.20, 0.30),
    "entropy_coef": (0.005, 0.010, 0.020),
    "gamma": (0.95, 0.99, 0.995),
    "gae_lambda": (0.90, 0.95, 0.98),
}
MECHANISM_SENSITIVITY_AXES = {
    "initial_uav_pesticide_l": (0.05, 0.2875, 0.525),
    "vehicle_speed_m_s": (4, 8, 12),
    "transfer_rate_l_min": (2, 4, 8),
    "setup_time_s": (5, 10, 30),
    "rendezvous_radius_m": (5, 15, 30),
}


def validate_sensitivity_diff(center: Mapping[str, object], variant: Mapping[str, object]) -> tuple[str, object]:
    if set(center) != set(variant):
        raise ValueError("sensitivity configuration keys must match")
    changed = [key for key in center if center[key] != variant[key]]
    if len(changed) != 1:
        raise ValueError("sensitivity must change exactly one registered axis")
    axis = changed[0]
    levels = SENSITIVITY_AXES.get(axis) or MECHANISM_SENSITIVITY_AXES.get(axis)
    if levels is None or variant[axis] not in levels or variant[axis] == center[axis]:
        raise ValueError("sensitivity value is not a registered noncenter level")
    if center[axis] != levels[1]:
        raise ValueError("sensitivity center must equal the registered axis center")
    return axis, variant[axis]


__all__ = ["SENSITIVITY_AXES", "MECHANISM_SENSITIVITY_AXES", "validate_sensitivity_diff"]
