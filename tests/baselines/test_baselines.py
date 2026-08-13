from __future__ import annotations

import pytest

from problem2.baselines.fixed_support import FixedSupportBaseline
from problem2.baselines.priority_dispatch import PriorityDispatchPolicy
from problem2.baselines.rolling_astar import RollingAStarPolicy
from problem2.baselines.teleport_service import TeleportServiceBaseline
from problem2.baselines.unlimited_supply import UnlimitedSupplyBaseline
from problem2.road.graph import RoadGraph


def test_unlimited_and_teleport_are_diagnostic_policies_without_mutating_resource_state() -> None:
    observation = {
        "uav-1": {"role": "uav", "onboard_l": 0.0},
        "vehicle-1": {"role": "vehicle", "inventory_l": 0.0},
    }
    unlimited = UnlimitedSupplyBaseline()
    teleport = TeleportServiceBaseline()

    assert unlimited.act(observation)["uav-1"] == "spray"
    assert teleport.act(observation)["vehicle-1"] == "teleport_service"
    assert observation["vehicle-1"]["inventory_l"] == 0.0


def test_fixed_support_keeps_vehicle_at_fixed_node_and_dispatches_open_request() -> None:
    policy = FixedSupportBaseline(support_node="depot")
    observation = {"vehicle-1": {"role": "vehicle", "position": "road-2"}}

    actions = policy.act(observation)

    assert actions["vehicle-1"] == "return_to_support"
    assert policy.support_node == "depot"


def test_priority_dispatch_prefers_urgent_feasible_request_with_deterministic_ties() -> None:
    requests = [
        {"request_id": "late", "uav_id": "uav-2", "urgency": 0.9, "requested_l": 2.0},
        {"request_id": "early", "uav_id": "uav-1", "urgency": 0.9, "requested_l": 2.0},
        {"request_id": "infeasible", "uav_id": "uav-3", "urgency": 1.0, "requested_l": 5.0},
    ]
    selected = PriorityDispatchPolicy().select(requests, vehicle_inventory_l=3.0, service_cap_l=3.0)

    assert selected["request_id"] == "early"


def test_rolling_astar_uses_road_shortest_path_and_rejects_unreachable_target() -> None:
    graph = RoadGraph.from_edges(
        {"a": (0, 0), "b": (1, 0), "c": (2, 0), "x": (0, 5)},
        [("a", "b", 1.0), ("b", "c", 1.0)],
    )
    policy = RollingAStarPolicy(graph)

    route = policy.plan("a", [{"request_id": "r1", "target_node": "c", "urgency": 1.0}])
    assert route.path == ["a", "b", "c"]
    assert route.distance_m == pytest.approx(2.0)
    assert policy.plan("a", [{"request_id": "r2", "target_node": "x", "urgency": 2.0}]) is None

