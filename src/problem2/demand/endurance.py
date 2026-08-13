"""Physical estimates for the remaining UAV spraying endurance."""

from __future__ import annotations


def remaining_work_time_s(
    *, onboard_l: float, spray_flow_l_s: float, reserve_l: float = 0.0
) -> float:
    """Return usable spraying time in seconds after preserving ``reserve_l``."""

    if onboard_l < 0 or reserve_l < 0:
        raise ValueError("onboard_l and reserve_l must be non-negative")
    if spray_flow_l_s <= 0:
        raise ValueError("spray_flow_l_s must be positive")
    usable_l = max(0.0, float(onboard_l) - float(reserve_l))
    return usable_l / float(spray_flow_l_s)


__all__ = ["remaining_work_time_s"]
