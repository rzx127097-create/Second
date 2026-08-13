"""Deterministic replenishment-demand urgency scoring."""

from __future__ import annotations

from math import inf


def urgency_score(
    remaining_l: float,
    available_s: float | None = None,
    eta_s: float = 0.0,
    *,
    epsilon: float = 1e-12,
) -> float:
    """Return a dimensionless urgency score; larger means more urgent.

    A request with no remaining spray endurance is maximally urgent.  For
    positive endurance, urgency increases with ETA and decreases with the
    available spraying time.  ``inf`` is returned for an already exhausted
    UAV, making ordering deterministic without silently hiding the failure.
    """

    if remaining_l < 0 or eta_s < 0 or (available_s is not None and available_s < 0):
        raise ValueError("urgency inputs must be non-negative")
    if remaining_l <= epsilon:
        return inf
    endurance = remaining_l if available_s is None else max(available_s, epsilon)
    return (eta_s + epsilon) / endurance


def compute_urgency(*args, **kwargs) -> float:
    return urgency_score(*args, **kwargs)

