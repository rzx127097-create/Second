"""Immutable rendezvous-point records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RendezvousPoint:
    point_id: str
    road_node_id: str
    position: tuple[float, float]
    distance_m: float
    reachable: bool = True
    service_separation_m: float = 0.0

    def __post_init__(self) -> None:
        if not self.point_id or not self.road_node_id:
            raise ValueError("rendezvous point and road node identifiers are required")
        if self.distance_m < 0 or self.service_separation_m < 0:
            raise ValueError("rendezvous distances must be non-negative")
