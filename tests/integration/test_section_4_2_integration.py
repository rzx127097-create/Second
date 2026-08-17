from __future__ import annotations

import numpy as np
import pytest

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.environment.action_masks import ActionMask
from problem2.environment.service_state_machine import ServicePhase
from problem2.road.graph import RoadGraph
from problem2.section4_2.road_executor import RoadVehicleExecutor
from problem2.section4_2.adapter import HeterogeneousDecisionAdapter
from problem2.section4_2.audit import ConsistencyAuditor


def graph() -> RoadGraph:
    return RoadGraph.from_edges(
        {"a": (0.0, 0.0), "b": (3.0, 0.0), "c": (6.0, 0.0)},
        [("a", "b", 3.0), ("b", "c", 3.0)],
    )


def resources() -> PesticideResources:
    return PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.2, 1.0, 0.01)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 0.5, 0.5, 0.02, 0.3)},
    )


def resources_with_unassigned_uav() -> PesticideResources:
    return PesticideResources(
        uavs={
            "uav-1": UAVState("uav-1", 0.2, 1.0, 0.01),
            "uav-2": UAVState("uav-2", 0.4, 1.0, 0.01),
        },
        vehicles={"vehicle-1": VehicleState("vehicle-1", 0.5, 0.5, 0.02, 0.3)},
    )


def rendezvous_adapter() -> HeterogeneousDecisionAdapter:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.8, 1.0, 0.01)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 0.5, 0.5, 1.0, 0.5)},
    )
    return HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=2.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        request_threshold_ratio=0.9,
        service_setup_s=1.0,
        rendezvous_radius_m=0.5,
        max_candidate_slots=3,
    )


def test_road_vehicle_executor_carries_residual_distance_and_stays_on_graph() -> None:
    executor = RoadVehicleExecutor(graph(), current_node="a", speed_mps=2.0)
    executor.set_route(["a", "b", "c"])

    first = executor.advance(dt_s=1.0)
    assert first.node == "a"
    assert first.residual_distance_m == pytest.approx(2.0)
    assert first.on_road is True

    second = executor.advance(dt_s=1.0)
    assert second.node == "b"
    assert second.residual_distance_m == pytest.approx(1.0)
    assert second.on_road is True

    third = executor.advance(dt_s=1.0)
    # The third one-second budget consumes the remaining 2 m of the b-c edge.
    # Residual distance is the distance already consumed on the current edge;
    # at a reached node it therefore resets to zero.
    assert third.node == "c"
    assert third.residual_distance_m == pytest.approx(0.0)
    assert third.route_complete is True


def test_road_vehicle_executor_rejects_route_outside_graph() -> None:
    executor = RoadVehicleExecutor(graph(), current_node="a", speed_mps=1.0)
    with pytest.raises(ValueError, match="road graph"):
        executor.set_route(["a", "missing"])


def test_heterogeneous_adapter_keeps_role_slots_and_event_order() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(), graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=2.0, decision_dt_s=1.0,
    )
    state = adapter.reset(seed=11)
    assert state.role_slots == {"uav": ("uav-1",), "vehicle": ("vehicle-1",)}
    assert state.action_masks["uav-1"].actions == ("up", "down", "left", "right", "hold", "spray")
    next_state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    assert [event["event_type"] for event in next_state.events] == ["actions_validated", "movement_applied", "field_updated"]


def test_adapter_maps_vehicle_slot_to_route_and_advances_on_road() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(), graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=2.0, decision_dt_s=1.0,
    )
    adapter.reset(seed=3)
    adapter.set_candidate_routes("vehicle-1", {"slot-0": ["a", "b", "c"]})

    state = adapter.step({"uav-1": "hold", "vehicle-1": "slot-0"})

    assert state.vehicle_nodes["vehicle-1"] == "a"
    movement = next(event for event in state.events if event["event_type"] == "movement_applied")
    assert movement["travelled_distance_m"] == pytest.approx(2.0)
    assert movement["route_complete"] is False
    assert state.action_masks["vehicle-1"].valid_actions == ("hold",)
    continued = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    assert continued.vehicle_nodes["vehicle-1"] == "b"
    movement = next(event for event in continued.events if event["event_type"] == "movement_applied")
    assert movement["travelled_distance_m"] == pytest.approx(2.0)

    completed = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    assert completed.vehicle_nodes["vehicle-1"] == "c"
    assert completed.action_masks["vehicle-1"].valid_actions == ("hold",)


def test_uav_grid_motion_uses_metric_speed_instead_of_one_cell_per_step() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(),
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        decision_dt_s=1.0,
        uav_grid_shape=(1, 2),
        uav_cell_size_m=(10.0, 10.0),
        uav_speed_mps=1.0,
    )
    adapter.reset(seed=4)

    started = adapter.step({"uav-1": "right", "vehicle-1": "hold"})

    assert adapter.uav_positions["uav-1"] == (0, 0)
    movement = next(
        event for event in started.events
        if event["event_type"] == "uav_movement_applied"
    )
    assert movement["distance_m"] == pytest.approx(1.0)
    assert movement["route_complete"] is False
    assert started.action_masks["uav-1"].valid_actions == ("hold",)

    travelled = movement["distance_m"]
    for _ in range(9):
        state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
        travelled += next(
            event["distance_m"] for event in state.events
            if event["event_type"] == "uav_movement_applied"
        )

    assert travelled == pytest.approx(10.0)
    assert adapter.uav_positions["uav-1"] == (0, 1)
    assert "left" in state.action_masks["uav-1"].valid_actions


def test_adapter_reset_restores_pesticide_state_deterministically() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(), graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
        uav_grid_shape=(1, 1),
    )
    adapter.reset(seed=1)
    adapter.step({"uav-1": "spray", "vehicle-1": "hold"})
    assert adapter.resources.uav("uav-1").onboard_l < 0.2
    adapter.reset(seed=1)
    assert adapter.resources.uav("uav-1").onboard_l == pytest.approx(0.2)
    assert adapter.resources.vehicle("vehicle-1").inventory_l == pytest.approx(0.5)
    adapter.resources.assert_conservation()


def test_adapter_reset_restores_resources_outside_active_role_slots() -> None:
    all_resources = resources_with_unassigned_uav()
    adapter = HeterogeneousDecisionAdapter(
        all_resources, graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
    )
    adapter.reset(seed=1)
    all_resources.spray("uav-2", 0.1)
    adapter.reset(seed=1)
    assert all_resources.uav("uav-2").onboard_l == pytest.approx(0.4)
    all_resources.assert_conservation()


def test_adapter_builds_vehicle_slots_from_section_4_3_rendezvous_candidates() -> None:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.8, 1.0, 0.01)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 0.5, 0.5, 1.0, 0.5)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=2.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        request_threshold_ratio=0.9,
        service_setup_s=0.0,
        rendezvous_radius_m=4.0,
        max_candidate_slots=3,
    )
    adapter.reset(seed=13)

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    request = adapter.request_manager.active_requests()[0]
    assert state.action_masks["vehicle-1"].valid_actions == ("hold", "slot-0")
    assert state.candidate_mapping["vehicle-1"] == (
        ("slot-0", f"{request.request_id}:rv-a"),
    )
    candidate = state.candidate_features["vehicle-1"][0]
    assert candidate["slot"] == "slot-0"
    assert candidate["mapping_key"] == f"{request.request_id}:rv-a"
    assert candidate["request_id"] == request.request_id
    assert candidate["road_distance_m"] == pytest.approx(0.0)
    assert candidate["joint_arrival_eta_s"] == pytest.approx(0.0)


def test_joint_rendezvous_can_select_a_future_uav_cell_outside_service_radius() -> None:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.1, 1.0, 0.1)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 1.0, 1.0, 1.0, 1.0)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=1.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        request_threshold_ratio=0.9,
        service_setup_s=0.0,
        rendezvous_radius_m=0.5,
        max_candidate_slots=3,
        initial_vehicle_nodes={"vehicle-1": "c"},
    )
    adapter.reset(seed=31)

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    request = adapter.request_manager.active_requests()[0]
    assert state.candidate_mapping["vehicle-1"] == (
        ("slot-0", f"{request.request_id}:rv-b"),
    )


def test_dynamic_request_uses_remaining_endurance_and_response_time() -> None:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.1, 1.0, 0.1)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 1.0, 1.0, 1.0, 1.0)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=1.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        request_threshold_ratio=0.0,
        dynamic_request_enabled=True,
        request_safety_margin_s=1.0,
        service_setup_s=1.0,
        rendezvous_radius_m=0.5,
        initial_vehicle_nodes={"vehicle-1": "c"},
    )
    adapter.reset(seed=32)

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    assert len(adapter.request_manager.active_requests()) == 1
    created = next(event for event in state.events if event["event_type"] == "request_created")
    assert created["trigger"] == "dynamic_endurance"
    assert created["remaining_work_s"] == pytest.approx(1.0)
    assert created["required_response_s"] > created["remaining_work_s"]
    assert created["amount_l"] >= 0.9


def test_dynamic_request_volume_is_bounded_by_current_tank_gap() -> None:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.3, 1.0, 0.01)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 1.0, 1.0, 0.01, 0.8)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=1.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        dynamic_request_enabled=True,
        service_setup_s=0.0,
        rendezvous_radius_m=0.5,
        initial_vehicle_nodes={"vehicle-1": "a"},
    )
    adapter.reset(seed=33)

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    created = next(event for event in state.events if event["event_type"] == "request_created")
    request = adapter.request_manager.active_requests()[0]
    assert created["amount_l"] == pytest.approx(0.7)
    assert request.requested_l == pytest.approx(0.7)


def test_fixed_support_request_forecast_uses_the_stationary_service_node() -> None:
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.1, 1.0, 0.1)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 1.0, 1.0, 10.0, 1.0)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        graph(),
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=100.0,
        decision_dt_s=1.0,
        uav_grid_shape=(1, 7),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        dynamic_request_enabled=True,
        service_setup_s=0.0,
        rendezvous_radius_m=0.5,
        support_mode="fixed",
        initial_vehicle_nodes={"vehicle-1": "a"},
    )
    adapter.reset(seed=34)
    adapter.uav_positions["uav-1"] = (0, 6)
    adapter._uav_metric_positions["uav-1"] = (6.0, 0.0)
    adapter._refresh_state(events=[])

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    created = next(event for event in state.events if event["event_type"] == "request_created")
    assert created["required_response_s"] == pytest.approx(6.09)


def test_request_forecast_uses_four_connected_uav_travel_distance() -> None:
    diagonal_graph = RoadGraph.from_edges({"rv": (3.0, 4.0)}, [])
    candidate_resources = PesticideResources(
        uavs={"uav-1": UAVState("uav-1", 0.6, 1.0, 0.1)},
        vehicles={"vehicle-1": VehicleState("vehicle-1", 1.0, 1.0, 10.0, 1.0)},
    )
    adapter = HeterogeneousDecisionAdapter(
        candidate_resources,
        diagonal_graph,
        uav_slots=("uav-1",),
        vehicle_slots=("vehicle-1",),
        vehicle_speed_mps=1.0,
        decision_dt_s=1.0,
        uav_grid_shape=(5, 4),
        uav_cell_size_m=(1.0, 1.0),
        uav_speed_mps=1.0,
        dynamic_request_enabled=True,
        service_setup_s=0.0,
        rendezvous_radius_m=0.5,
        support_mode="fixed",
        initial_vehicle_nodes={"vehicle-1": "rv"},
    )
    adapter.reset(seed=35)

    state = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    created = next(event for event in state.events if event["event_type"] == "request_created")
    assert created["required_response_s"] == pytest.approx(7.04)


def test_reservation_does_not_hard_lock_uav_before_joint_arrival() -> None:
    adapter = rendezvous_adapter()
    adapter.reset(seed=21)
    requested = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    assert requested.candidate_mapping["vehicle-1"][0][1].endswith(":rv-a")

    reserved = adapter.step({"uav-1": "right", "vehicle-1": "slot-0"})

    assert adapter.service.phase is ServicePhase.RESERVED
    assert adapter.uav_positions["uav-1"] == (0, 1)
    assert "spray" in reserved.action_masks["uav-1"].valid_actions
    assert not any(event["event_type"] == "joint_arrival" for event in reserved.events)


def test_service_preparation_starts_only_after_both_roles_arrive() -> None:
    adapter = rendezvous_adapter()
    adapter.reset(seed=22)
    adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    adapter.step({"uav-1": "right", "vehicle-1": "slot-0"})

    arrived = adapter.step({"uav-1": "left", "vehicle-1": "hold"})

    assert adapter.uav_positions["uav-1"] == (0, 0)
    assert adapter.service.phase is ServicePhase.PREPARING
    assert arrived.action_masks["uav-1"].valid_actions == ("hold",)
    assert arrived.action_masks["vehicle-1"].valid_actions == ("hold",)
    assert any(event["event_type"] == "joint_arrival" for event in arrived.events)


def test_service_lock_is_not_counted_as_empty_tank_disablement() -> None:
    adapter = rendezvous_adapter()
    adapter.reset(seed=23)
    adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    adapter.step({"uav-1": "right", "vehicle-1": "slot-0"})
    adapter.step({"uav-1": "left", "vehicle-1": "hold"})

    service_step = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})

    assert adapter.resources.uav("uav-1").onboard_l > 0.0
    assert any(event["event_type"] == "service_active" for event in service_step.events)
    assert not any(
        event["event_type"] == "pesticide_disabled" for event in service_step.events
    )


def test_adapter_records_actual_spray_and_lock_blocks_spray() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(), graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
        uav_grid_shape=(1, 1),
    )
    adapter.reset(seed=1)
    sprayed = adapter.step({"uav-1": "spray", "vehicle-1": "hold"})
    event = next(item for item in sprayed.events if item["event_type"] == "spray_applied")
    assert event["amount_l"] == pytest.approx(0.01)

    adapter.set_service_lock("uav-1", "vehicle-1")
    locked = adapter.step({"uav-1": "hold", "vehicle-1": "hold"})
    assert not any(item["event_type"] == "spray_applied" for item in locked.events)


def test_service_lock_updates_both_role_masks_and_rejects_non_hold_actions() -> None:
    adapter = HeterogeneousDecisionAdapter(
        resources(), graph(), uav_slots=("uav-1",), vehicle_slots=("vehicle-1",),
    )
    adapter.reset(seed=5)
    adapter.set_service_lock("uav-1", "vehicle-1")

    state = adapter.state
    assert state.action_masks["uav-1"].valid_actions == ("hold",)
    assert state.action_masks["vehicle-1"].valid_actions == ("hold",)
    with pytest.raises(ValueError, match="not legal"):
        adapter.step({"uav-1": "spray", "vehicle-1": "hold"})


def test_consistency_auditor_checks_mask_service_and_conservation() -> None:
    auditor = ConsistencyAuditor()
    mask = ActionMask(np.array([1, 0], dtype=np.int8), ("hold", "slot-0"))
    result = auditor.check(
        vehicle_positions={"vehicle-1": "a"},
        road_graph=graph(),
        service_assignments={"request-1": "uav-1"},
        vehicle_assignments={"vehicle-1": "request-1"},
        sampled_actions={"vehicle-1": "hold"},
        action_masks={"vehicle-1": mask},
        resources=resources(),
    )
    assert result.ok is True
    assert result.violations == ()


def test_consistency_auditor_rejects_one_vehicle_with_multiple_requests() -> None:
    auditor = ConsistencyAuditor()
    result = auditor.check(
        vehicle_positions={"vehicle-1": "a"},
        road_graph=graph(),
        service_assignments={"request-1": "uav-1"},
        vehicle_assignments={"vehicle-1": ("request-1", "request-2")},
        sampled_actions={"vehicle-1": "hold"},
        action_masks={"vehicle-1": ActionMask(np.array([1, 0], dtype=np.int8), ("hold", "slot-0"))},
        resources=resources(),
    )
    assert result.ok is False
    assert "vehicle_serves_multiple_requests" in result.violations


def test_consistency_auditor_rejects_request_mapping_disagreement() -> None:
    result = ConsistencyAuditor().check(
        vehicle_positions={"vehicle-1": "a"},
        road_graph=graph(),
        service_assignments={"request-1": "uav-1"},
        vehicle_assignments={"vehicle-1": "request-2"},
        sampled_actions={"vehicle-1": "hold"},
        action_masks={"vehicle-1": ActionMask(np.array([1], dtype=np.int8), ("hold",))},
        resources=resources(),
    )
    assert result.ok is False
    assert "service_assignment_mismatch:request-2" in result.violations


def test_consistency_auditor_rejects_service_request_without_vehicle() -> None:
    result = ConsistencyAuditor().check(
        vehicle_positions={"vehicle-1": "a"},
        road_graph=graph(),
        service_assignments={"request-1": "uav-1", "request-2": "uav-2"},
        vehicle_assignments={"vehicle-1": "request-1"},
        sampled_actions={"vehicle-1": "hold"},
        action_masks={"vehicle-1": ActionMask(np.array([1], dtype=np.int8), ("hold",))},
        resources=resources(),
    )
    assert result.ok is False
    assert "service_assignment_mismatch:request-2" in result.violations
