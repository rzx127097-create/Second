from __future__ import annotations

import numpy as np
import pytest

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.environment.action_masks import ActionMask
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
