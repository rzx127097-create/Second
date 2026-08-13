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

    def __post_init__(self) -> None:
        if not self.point_id or not self.road_node_id:
            raise ValueError("rendezvous point and road node identifiers are required")
        if self.distance_m < 0:
            raise ValueError("distance_m must be non-negative")

