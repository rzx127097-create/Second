from __future__ import annotations

import inspect

import pytest

from problem2.domain import VehicleState
from problem2.heuristics import DispatchObservation, ObservableRequest
from problem2.heuristics.astar import RollingAStarController, astar_path_and_distance
from problem2.heuristics.fixed import FixedSupportController
from problem2.heuristics.nearest import NearestRequestController
from problem2.heuristics.two_stage import TwoStageSchedule
from problem2.heuristics.urgency import UrgencyController
from problem2.road.search import dijkstra_distance
from tests.g2.helpers import make_raster_graph


def _graph():
    return make_raster_graph(
        [(0, 0), (0, 1), (1, 1), (1, 2), (0, 2), (3, 3)],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        shape=(4, 4),
        component_ids=[0, 0, 0, 0, 0, 1],
    )


def _vehicle(graph, *, inventory_l: float = 1.0) -> VehicleState:
    return VehicleState(
        "vehicle-0",
        current_node=0,
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        inventory_l=inventory_l,
    )


def _request(
    request_id: str,
    slot: int,
    service_node: int,
    *,
    created_step: int = 0,
    requested_l: float = 0.5,
    pesticide_l: float = 0.1,
    endurance_steps: float = 5.0,
) -> ObservableRequest:
    return ObservableRequest(
        request_id=request_id,
        uav_id=f"uav-{request_id}",
        slot=slot,
        created_step=created_step,
        requested_l=requested_l,
        pesticide_l=pesticide_l,
        usable_capacity_l=1.0,
        endurance_steps=endurance_steps,
        service_nodes=(service_node,),
    )


def _observation(graph, requests, *, step: int = 4, inventory_l: float = 1.0, **kwargs):
    mapping = [None, None, None, None]
    for request in requests:
        mapping[request.slot] = request.request_id
    return DispatchObservation(
        step=step,
        graph=graph,
        vehicle=_vehicle(graph, inventory_l=inventory_l),
        requests=tuple(requests),
        candidate_mapping=tuple(mapping),
        service_cap_l=0.6,
        tolerance=1e-9,
        **kwargs,
    )


def test_astar_path_lengths_match_dijkstra_on_hand_checked_graph_pairs() -> None:
    graph = _graph()
    expected = {(0, 0): 0.0, (0, 2): 20.0, (0, 4): 40.0, (1, 3): 20.0}

    for pair, literal_distance in expected.items():
        path, distance = astar_path_and_distance(graph, *pair)
        assert distance == pytest.approx(literal_distance)
        assert distance == pytest.approx(dijkstra_distance(graph, *pair))
        assert path[0] == pair[0]
        assert path[-1] == pair[1]

    second = make_raster_graph(
        [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        shape=(3, 3),
    )
    for start, goal, literal_distance in ((0, 3, 30.0), (1, 4, 30.0)):
        _, distance = astar_path_and_distance(second, start, goal)
        assert distance == pytest.approx(literal_distance)
        assert distance == pytest.approx(dijkstra_distance(second, start, goal))


def test_nearest_controller_uses_deterministic_request_identity_tie_break() -> None:
    graph = _graph()
    requests = (_request("b", 0, 2), _request("a", 1, 2))

    decision = NearestRequestController().decide(_observation(graph, requests))

    assert decision.sampled_slot == 2
    assert decision.request_id == "a"
    assert decision.selected_service_node == 2
    assert decision.route_length_m == pytest.approx(20.0)
    assert decision.decision_runtime_s >= 0.0


@pytest.mark.parametrize(
    "controller",
    [RollingAStarController(replan_interval_steps=2), NearestRequestController(), UrgencyController()],
)
def test_controllers_hold_when_requests_are_unreachable_or_service_infeasible(controller) -> None:
    graph = _graph()
    unreachable = _request("unreachable", 0, 5)
    zero_gap = _request("zero-gap", 1, 2, pesticide_l=1.0)
    zero_request = _request("zero-request", 2, 2, requested_l=0.0)

    decision = controller.decide(
        _observation(graph, (unreachable, zero_gap, zero_request))
    )
    no_inventory = controller.decide(
        _observation(graph, (_request("reachable", 0, 2),), inventory_l=0.0)
    )

    assert decision.sampled_slot == 0
    assert decision.request_id is None
    assert no_inventory.sampled_slot == 0
    assert no_inventory.request_id is None


def test_urgency_controller_uses_current_endurance_then_waiting_and_identity() -> None:
    graph = _graph()
    requests = (
        _request("far-urgent", 0, 4, endurance_steps=1.0, created_step=3),
        _request("near-safe", 1, 1, endurance_steps=4.0, created_step=0),
    )

    decision = UrgencyController().decide(_observation(graph, requests, step=5))

    assert decision.request_id == "far-urgent"
    assert decision.sampled_slot == 1
    assert decision.route_length_m == pytest.approx(40.0)


def test_active_dispatch_preserves_original_sampled_slot_and_mapping() -> None:
    graph = _graph()
    request = _request("active", 2, 4)
    observation = _observation(
        graph,
        (request,),
        active_request_id="active",
        active_sampled_slot=3,
        selected_service_node=4,
    )

    decision = RollingAStarController(replan_interval_steps=2).decide(observation)

    assert decision.sampled_slot == 3
    assert decision.request_id == "active"
    assert decision.selected_service_node == 4


def test_astar_controller_uses_request_identity_for_deterministic_ties() -> None:
    graph = _graph()
    requests = (_request("b", 0, 2), _request("a", 1, 2))

    decision = RollingAStarController(replan_interval_steps=2).decide(
        _observation(graph, requests)
    )

    assert decision.sampled_slot == 2
    assert decision.request_id == "a"
    assert decision.selected_service_node == 2


def test_astar_controller_executes_frozen_replan_cadence_without_slot_drift() -> None:
    graph = _graph()
    request = _request("active", 2, 4)
    controller = RollingAStarController(replan_interval_steps=2)

    step_4 = controller.decide(
        _observation(
            graph,
            (request,),
            step=4,
            active_request_id="active",
            active_sampled_slot=3,
            selected_service_node=4,
        )
    )
    step_5 = controller.decide(
        _observation(
            graph,
            (request,),
            step=5,
            active_request_id="active",
            active_sampled_slot=3,
            selected_service_node=4,
        )
    )
    step_6 = controller.decide(
        _observation(
            graph,
            (request,),
            step=6,
            active_request_id="active",
            active_sampled_slot=3,
            selected_service_node=4,
        )
    )

    assert [step_4.replanned, step_5.replanned, step_6.replanned] == [True, False, True]
    assert [step_4.plan_version, step_5.plan_version, step_6.plan_version] == [1, 1, 2]
    assert {step_4.sampled_slot, step_5.sampled_slot, step_6.sampled_slot} == {3}
    assert {step_4.selected_service_node, step_5.selected_service_node, step_6.selected_service_node} == {4}
    assert controller.state_dict() == {
        "active_request_id": "active",
        "active_sampled_slot": 3,
        "cached_route_length_m": 40.0,
        "last_replan_step": 6,
        "plan_version": 2,
        "replan_interval_steps": 2,
        "selected_service_node": 4,
    }


def test_controller_public_decisions_accept_observable_state_only() -> None:
    assert list(inspect.signature(RollingAStarController.decide).parameters) == [
        "self",
        "observation",
    ]
    assert list(inspect.signature(NearestRequestController.decide).parameters) == [
        "self",
        "observation",
    ]
    assert list(inspect.signature(UrgencyController.decide).parameters) == [
        "self",
        "observation",
    ]
    assert "future" not in DispatchObservation.__dataclass_fields__
    assert "pest" not in DispatchObservation.__dataclass_fields__


def test_fixed_support_requires_exact_resource_and_service_matching() -> None:
    controller = FixedSupportController(
        support_node=2,
        initial_inventory_l=20.0,
        service_cap_l=1.08,
        transfer_rate_lpm=4.0,
        setup_time_s=10.0,
        mobile_initial_inventory_l=20.0,
        mobile_service_cap_l=1.08,
        mobile_transfer_rate_lpm=4.0,
        mobile_setup_time_s=10.0,
    )

    assert controller.initial_inventory_l == 20.0


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("mobile_initial_inventory_l", 19.0),
        ("mobile_service_cap_l", 1.0),
        ("mobile_transfer_rate_lpm", 8.0),
        ("mobile_setup_time_s", 30.0),
    ],
)
def test_fixed_support_denies_unmatched_resources_at_construction(field, bad_value) -> None:
    values = {
        "mobile_initial_inventory_l": 20.0,
        "mobile_service_cap_l": 1.08,
        "mobile_transfer_rate_lpm": 4.0,
        "mobile_setup_time_s": 10.0,
    }
    values[field] = bad_value

    with pytest.raises(ValueError, match="resource-matched"):
        FixedSupportController(
            support_node=2,
            initial_inventory_l=20.0,
            service_cap_l=1.08,
            transfer_rate_lpm=4.0,
            setup_time_s=10.0,
            **values,
        )


def test_fixed_support_dispatches_only_requests_serviceable_at_its_frozen_node() -> None:
    graph = _graph()
    controller = FixedSupportController(
        support_node=2,
        initial_inventory_l=20.0,
        service_cap_l=1.08,
        transfer_rate_lpm=4.0,
        setup_time_s=10.0,
        mobile_initial_inventory_l=20.0,
        mobile_service_cap_l=1.08,
        mobile_transfer_rate_lpm=4.0,
        mobile_setup_time_s=10.0,
    )
    requests = (_request("not-here", 0, 4), _request("at-support", 1, 2))

    decision = controller.decide(_observation(graph, requests))

    assert decision.sampled_slot == 2
    assert decision.request_id == "at-support"
    assert decision.selected_service_node == 2
    assert decision.route_length_m == 0.0


def test_two_stage_budget_exactly_equals_joint_budget_and_is_checkpoint_ancestry() -> None:
    schedule = TwoStageSchedule(
        total_interaction_budget=200_000,
        uav_stage_budget=120_000,
        vehicle_stage_budget=80_000,
        schedule_version="g5-two-stage-v1",
    )

    ancestry = schedule.checkpoint_ancestry(
        parent_checkpoint_sha256="a" * 64,
        uav_stage_checkpoint_sha256="b" * 64,
    )

    assert ancestry == {
        "method_id": "sr_mappo_two_stage",
        "schedule_version": "g5-two-stage-v1",
        "total_interaction_budget": 200_000,
        "uav_stage_budget": 120_000,
        "vehicle_stage_budget": 80_000,
        "parent_checkpoint_sha256": "a" * 64,
        "uav_stage_checkpoint_sha256": "b" * 64,
    }
    with pytest.raises(ValueError, match="sum exactly"):
        TwoStageSchedule(
            total_interaction_budget=200_000,
            uav_stage_budget=120_000,
            vehicle_stage_budget=79_999,
            schedule_version="g5-two-stage-v1",
        )
