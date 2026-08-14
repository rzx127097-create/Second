from __future__ import annotations

import pytest

from problem2.demand.candidate_slots import build_candidate_action_slots
from problem2.demand.endurance import remaining_work_time_s
from problem2.demand.planning import (
    RendezvousCandidate,
    feasible_candidates,
    generate_rendezvous_candidates,
)
from problem2.demand.urgency import request_urgency
from problem2.road.graph import RoadGraph


def road_graph() -> RoadGraph:
    return RoadGraph.from_edges(
        {"a": (0.0, 0.0), "b": (2.0, 0.0), "c": (4.0, 0.0), "x": (0.0, 5.0)},
        [("a", "b", 2.0), ("b", "c", 2.0)],
    )


def test_remaining_work_time_uses_pesticide_and_flow_in_seconds() -> None:
    assert remaining_work_time_s(onboard_l=0.4, spray_flow_l_s=0.1) == pytest.approx(4.0)
    assert remaining_work_time_s(onboard_l=0.4, spray_flow_l_s=0.1, reserve_l=0.1) == pytest.approx(3.0)
    with pytest.raises(ValueError, match="spray_flow_l_s"):
        remaining_work_time_s(onboard_l=0.4, spray_flow_l_s=0.0)


def test_request_urgency_increases_with_response_time_and_exhaustion_is_explicit() -> None:
    assert request_urgency(remaining_work_s=10.0, response_time_s=5.0) == pytest.approx(0.5)
    assert request_urgency(remaining_work_s=10.0, response_time_s=8.0) > request_urgency(
        remaining_work_s=10.0, response_time_s=5.0
    )
    assert request_urgency(remaining_work_s=0.0, response_time_s=1.0) == float("inf")


def test_candidate_generation_uses_road_eta_and_rejects_unreachable_or_late_points() -> None:
    points = [
        {"point_id": "p-c", "road_node_id": "c", "position": (4.0, 0.0), "distance_m": 1.0},
        {"point_id": "p-b", "road_node_id": "b", "position": (2.0, 0.0), "distance_m": 1.0},
        {"point_id": "p-x", "road_node_id": "x", "position": (0.0, 5.0), "distance_m": 1.0},
    ]
    candidates = generate_rendezvous_candidates(
        points,
        graph=road_graph(),
        vehicle_node="a",
        vehicle_speed_mps=1.0,
        uav_speed_mps=1.0,
        remaining_work_s=10.0,
        requested_l=0.2,
        vehicle_inventory_l=1.0,
        service_cap_l=0.5,
        service_setup_s=1.0,
        transfer_rate_l_s=0.1,
        rendezvous_radius_m=2.0,
        request_id="req-1",
        uav_id="uav-1",
    )
    by_id = {candidate.point_id: candidate for candidate in candidates}
    assert set(by_id) == {"p-b", "p-c"}
    assert by_id["p-b"].road_distance_m == pytest.approx(2.0)
    assert by_id["p-b"].vehicle_ready_eta_s == pytest.approx(2.0)
    assert by_id["p-b"].joint_arrival_eta_s == pytest.approx(2.0)
    assert [candidate.point_id for candidate in candidates] == ["p-c", "p-b"]
    assert by_id["p-c"].urgency > by_id["p-b"].urgency

    late = generate_rendezvous_candidates(
        points[:1],
        graph=road_graph(),
        vehicle_node="a",
        vehicle_speed_mps=1.0,
        uav_speed_mps=1.0,
        remaining_work_s=2.0,
        requested_l=0.2,
        vehicle_inventory_l=1.0,
        service_cap_l=0.5,
        service_setup_s=1.0,
        transfer_rate_l_s=0.1,
        rendezvous_radius_m=2.0,
        request_id="req-1",
        uav_id="uav-1",
    )
    assert late[0].feasible is False
    assert late[0].reason == "late_service"
    assert feasible_candidates(late) == []

    deferred = generate_rendezvous_candidates(
        points[:1],
        graph=road_graph(),
        vehicle_node="a",
        vehicle_speed_mps=1.0,
        uav_speed_mps=1.0,
        remaining_work_s=2.0,
        requested_l=0.2,
        vehicle_inventory_l=1.0,
        service_cap_l=0.5,
        service_setup_s=1.0,
        transfer_rate_l_s=0.1,
        rendezvous_radius_m=2.0,
        request_id="req-1",
        uav_id="uav-1",
        allow_late_service=True,
    )
    assert deferred[0].feasible is True
    assert deferred[0].reason is None
    assert deferred[0].pesticide_disabled_expected is True


def test_candidate_action_slots_preserve_mapping_and_disable_padding() -> None:
    candidate = RendezvousCandidate(
        request_id="req-1",
        uav_id="uav-1",
        point_id="p-1",
        road_node_id="b",
        uav_distance_m=1.0,
        road_distance_m=2.0,
        uav_eta_s=1.0,
        vehicle_ready_eta_s=2.0,
        joint_arrival_eta_s=2.0,
        uav_wait_s=1.0,
        vehicle_wait_s=0.0,
        urgency=0.4,
        feasible=True,
        reason=None,
    )
    slots = build_candidate_action_slots([candidate], max_slots=3)
    assert slots.mapping == ("req-1:p-1", None, None)
    assert slots.mask.actions == ("hold", "slot-0", "slot-1", "slot-2")
    assert slots.mask.valid_actions == ("hold", "slot-0")


def test_candidate_generation_keeps_resource_failures_auditable() -> None:
    point = [{"point_id": "p-b", "road_node_id": "b", "position": (2.0, 0.0), "distance_m": 1.0}]
    empty_inventory = generate_rendezvous_candidates(
        point,
        graph=road_graph(), vehicle_node="a", vehicle_speed_mps=1.0, uav_speed_mps=1.0,
        remaining_work_s=10.0, requested_l=0.2, vehicle_inventory_l=0.0,
        service_cap_l=0.5, service_setup_s=1.0, transfer_rate_l_s=0.1,
        rendezvous_radius_m=2.0, request_id="req-1", uav_id="uav-1",
    )
    assert empty_inventory[0].feasible is False
    assert empty_inventory[0].reason == "vehicle_inventory_empty"

    empty_service = generate_rendezvous_candidates(
        point,
        graph=road_graph(), vehicle_node="a", vehicle_speed_mps=1.0, uav_speed_mps=1.0,
        remaining_work_s=10.0, requested_l=0.2, vehicle_inventory_l=1.0,
        service_cap_l=0.0, service_setup_s=1.0, transfer_rate_l_s=0.1,
        rendezvous_radius_m=2.0, request_id="req-1", uav_id="uav-1",
    )
    assert empty_service[0].feasible is False
    assert empty_service[0].reason == "service_capacity_empty"
