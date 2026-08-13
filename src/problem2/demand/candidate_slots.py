"""Stable filtering and ordering of rendezvous candidates."""

from __future__ import annotations

from collections.abc import Iterable
from math import hypot

from .rendezvous import RendezvousPoint


def candidate_slots(
    points: Iterable[RendezvousPoint],
    uav_position: tuple[float, float] | None = None,
    max_radius_m: float | None = None,
    *,
    reachable_node_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[RendezvousPoint]:
    """Filter candidates and sort by distance, then stable identifiers.

    ``RendezvousPoint.distance_m`` is authoritative when supplied by the road
    projection layer.  If a caller omits it in a future adapter, passing a UAV
    position still gives a useful Euclidean fallback.
    """

    if max_radius_m is not None and max_radius_m < 0:
        raise ValueError("max_radius_m must be non-negative")
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    selected: list[tuple[float, RendezvousPoint]] = []
    for point in points:
        if not point.reachable:
            continue
        if reachable_node_ids is not None and point.road_node_id not in reachable_node_ids:
            continue
        distance = point.distance_m
        if uav_position is not None and distance < 0:
            distance = hypot(point.position[0] - uav_position[0], point.position[1] - uav_position[1])
        if max_radius_m is not None and distance > max_radius_m + 1e-12:
            continue
        selected.append((distance, point))
    selected.sort(key=lambda item: (item[0], item[1].point_id, item[1].road_node_id))
    result = [point for _, point in selected]
    return result if limit is None else result[:limit]

