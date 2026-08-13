"""Event records shared by the environment and evidence pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceEvent:
    event_type: str
    step: int
    uav_id: str | None = None
    vehicle_id: str | None = None
    amount_l: float = 0.0
    request_id: str | None = None
