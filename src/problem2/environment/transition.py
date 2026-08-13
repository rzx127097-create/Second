"""Pure-ish helpers for deterministic environment transition bookkeeping."""

from __future__ import annotations

from dataclasses import asdict

from problem2.domain.events import ResourceEvent


def event_dict(event: ResourceEvent) -> dict[str, object]:
    return asdict(event)


def reduction_rate(initial_density: float, density: float) -> float:
    if initial_density <= 0:
        return 0.0
    return max(0.0, 1.0 - density / initial_density)
