"""Deterministic request-to-rendezvous planning primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from problem2.road.graph import RoadGraph
from problem2.road.shortest_path import shortest_path

from .eta import eta_seconds
from .rendezvous import RendezvousPoint
from .urgency import request_urgency


@dataclass(frozen=True)
class RendezvousCandidate:
    request_id: str
    uav_id: str
    point_id: str
    road_node_id: str
    uav_distance_m: float
    road_distance_m: float
    uav_eta_s: float
    vehicle_ready_eta_s: float
    joint_arrival_eta_s: float
    uav_wait_s: float
    vehicle_wait_s: float
    urgency: float
    feasible: bool
    reason: str | None
    pesticide_disabled_expected: bool = False

    @property
    def mapping_key(self) -> str:
        return f"{self.request_id}:{self.point_id}"


def _point_values(point: RendezvousPoint | Mapping[str, Any]) -> tuple[str, str, tuple[float, float], float, bool]:
    if isinstance(point, RendezvousPoint):
        return point.point_id, point.road_node_id, point.position, point.distance_m, point.reachable
    try:
        return (
            str(point["point_id"]),
            str(point["road_node_id"]),
            (float(point["position"][0]), float(point["position"][1])),
            float(point["distance_m"]),
            bool(point.get("reachable", True)),
        )
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise ValueError("rendezvous point must provide identifiers, position and distance_m") from exc


def _service_duration_s(
    *, requested_l: float, vehicle_inventory_l: float, service_cap_l: float,
    service_setup_s: float, transfer_rate_l_s: float,
) -> float:
    if min(requested_l, vehicle_inventory_l, service_cap_l, service_setup_s) < 0:
        raise ValueError("service quantities and setup time must be non-negative")
    if transfer_rate_l_s <= 0:
        raise ValueError("transfer_rate_l_s must be positive")
    transfer_l = min(requested_l, vehicle_inventory_l, service_cap_l)
    return float(service_setup_s) + transfer_l / float(transfer_rate_l_s)


def generate_rendezvous_candidates(
    points: Iterable[RendezvousPoint | Mapping[str, Any]],
    *,
    graph: RoadGraph,
    vehicle_node: str,
    vehicle_speed_mps: float,
    uav_speed_mps: float,
    remaining_work_s: float,
    requested_l: float,
    vehicle_inventory_l: float,
    service_cap_l: float,
    service_setup_s: float,
    transfer_rate_l_s: float,
    rendezvous_radius_m: float,
    request_id: str,
    uav_id: str,
    vehicle_release_s: float = 0.0,
    allow_late_service: bool = False,
) -> list[RendezvousCandidate]:
    if remaining_work_s < 0 or rendezvous_radius_m < 0 or vehicle_release_s < 0:
        raise ValueError("time and rendezvous radius must be non-negative")
    if requested_l < 0 or vehicle_inventory_l < 0 or service_cap_l < 0:
        raise ValueError("pesticide quantities must be non-negative")
    if not graph.has_node(vehicle_node):
        raise ValueError("vehicle_node must belong to the road graph")
    if vehicle_speed_mps <= 0 or uav_speed_mps <= 0:
        raise ValueError("vehicle_speed_mps and uav_speed_mps must be positive")

    service_duration_s = _service_duration_s(
        requested_l=requested_l,
        vehicle_inventory_l=vehicle_inventory_l,
        service_cap_l=service_cap_l,
        service_setup_s=service_setup_s,
        transfer_rate_l_s=transfer_rate_l_s,
    )
    result: list[RendezvousCandidate] = []
    for point in points:
        point_id, road_node_id, _position, uav_distance_m, reachable = _point_values(point)
        if not reachable or not graph.has_node(road_node_id):
            continue
        try:
            _path, road_distance_m = shortest_path(graph, vehicle_node, road_node_id)
        except ValueError:
            continue
        if uav_distance_m < 0:
            raise ValueError("uav distance must be non-negative")
        uav_eta_s = eta_seconds(uav_distance_m, uav_speed_mps)
        vehicle_ready_eta_s = vehicle_release_s + eta_seconds(road_distance_m, vehicle_speed_mps)
        joint_arrival_eta_s = max(uav_eta_s, vehicle_ready_eta_s)
        uav_wait_s = max(0.0, vehicle_ready_eta_s - uav_eta_s)
        vehicle_wait_s = max(0.0, uav_eta_s - vehicle_ready_eta_s)
        candidate_urgency = request_urgency(
            remaining_work_s=remaining_work_s,
            response_time_s=joint_arrival_eta_s + service_duration_s,
        )
        reason: str | None = None
        if uav_distance_m > rendezvous_radius_m + 1e-12:
            reason = "outside_rendezvous_radius"
        elif vehicle_inventory_l <= 0:
            reason = "vehicle_inventory_empty"
        elif requested_l > 0 and service_cap_l <= 0:
            reason = "service_capacity_empty"
        pesticide_disabled_expected = joint_arrival_eta_s + service_duration_s > remaining_work_s + 1e-12
        if reason is None and pesticide_disabled_expected and not allow_late_service:
            reason = "late_service"
        result.append(RendezvousCandidate(
            request_id=request_id,
            uav_id=uav_id,
            point_id=point_id,
            road_node_id=road_node_id,
            uav_distance_m=float(uav_distance_m),
            road_distance_m=float(road_distance_m),
            uav_eta_s=float(uav_eta_s),
            vehicle_ready_eta_s=float(vehicle_ready_eta_s),
            joint_arrival_eta_s=float(joint_arrival_eta_s),
            uav_wait_s=float(uav_wait_s),
            vehicle_wait_s=float(vehicle_wait_s),
            urgency=float(candidate_urgency),
            feasible=reason is None,
            reason=reason,
            pesticide_disabled_expected=pesticide_disabled_expected,
        ))
    result.sort(key=lambda item: (-item.urgency, item.joint_arrival_eta_s, item.point_id, item.road_node_id))
    return result


def feasible_candidates(candidates: Iterable[RendezvousCandidate]) -> list[RendezvousCandidate]:
    return [candidate for candidate in candidates if candidate.feasible]


__all__ = ["RendezvousCandidate", "feasible_candidates", "generate_rendezvous_candidates"]
