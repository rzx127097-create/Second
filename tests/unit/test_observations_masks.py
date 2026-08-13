from __future__ import annotations

import numpy as np

from problem2.domain.resources import PesticideResources
from problem2.domain.state import UAVState, VehicleState
from problem2.environment.action_masks import (
    UAV_ACTIONS,
    VEHICLE_ACTIONS,
    uav_action_mask,
    vehicle_action_mask,
)
from problem2.environment.observations import (
    build_structured_critic_state,
    build_uav_observation,
    build_vehicle_observation,
    stable_slot_mapping,
)


def _resources() -> PesticideResources:
    return PesticideResources(
        uavs={
            "uav-2": UAVState("uav-2", 0.2, 1.0, 0.1),
            "uav-1": UAVState("uav-1", 0.5, 1.0, 0.1),
        },
        vehicles={
            "vehicle-2": VehicleState("vehicle-2", 2.0, 3.0, 0.2, 1.0),
            "vehicle-1": VehicleState("vehicle-1", 1.0, 3.0, 0.2, 1.0),
        },
    )


def test_slot_mapping_is_sorted_and_observation_shape_is_invariant() -> None:
    resources = _resources()
    mapping = stable_slot_mapping(resources.uavs, resources.vehicles)
    assert mapping.uav_ids == ("uav-1", "uav-2")
    assert mapping.vehicle_ids == ("vehicle-1", "vehicle-2")
    observation = build_uav_observation(
        "uav-1",
        resources,
        positions={"uav-1": (0, 0), "uav-2": (0, 1)},
        vehicle_positions={"vehicle-1": (1, 0), "vehicle-2": (1, 1)},
        pest_density=np.ones((2, 2)),
        mapping=mapping,
    )
    assert observation["role"] == "uav"
    assert observation["vector"].shape == observation["vector"].shape
    assert "critic_state" not in observation
    assert "global_pest_density" not in observation


def test_vehicle_observation_uses_fixed_vehicle_and_request_slots() -> None:
    resources = _resources()
    mapping = stable_slot_mapping(resources.uavs, resources.vehicles, max_request_slots=2)
    observation = build_vehicle_observation(
        "vehicle-1",
        resources,
        positions={"uav-1": (0, 0), "uav-2": (0, 1)},
        vehicle_positions={"vehicle-1": (1, 0), "vehicle-2": (1, 1)},
        requests=[
            {"request_id": "req-2", "uav_id": "uav-2", "remaining_l": 0.4, "urgency": 2.0},
            {"request_id": "req-1", "uav_id": "uav-1", "remaining_l": 0.7, "urgency": 1.0},
        ],
        mapping=mapping,
    )
    assert observation["role"] == "vehicle"
    assert observation["request_slots"].shape == (2,)
    assert observation["request_slot_mask"].tolist() == [1, 1]
    assert observation["slot_mapping"] == ("req-1", "req-2")


def test_critic_state_is_structured_and_flattening_is_stable() -> None:
    resources = _resources()
    mapping = stable_slot_mapping(resources.uavs, resources.vehicles, max_request_slots=2)
    state = build_structured_critic_state(
        resources,
        positions={"uav-1": (0, 0), "uav-2": (0, 1)},
        vehicle_positions={"vehicle-1": (1, 0), "vehicle-2": (1, 1)},
        pest_density=np.ones((2, 2)),
        mapping=mapping,
        requests=[],
        step=3,
        max_steps=10,
    )
    assert set(state) >= {"eco", "uavs", "vehicles", "requests", "service", "time", "vector"}
    assert state["vector"].ndim == 1
    assert state["vector"].size > 0


def test_locked_uav_mask_only_allows_hold() -> None:
    mask = uav_action_mask(
        (0, 0),
        shape=(2, 2),
        onboard_l=1.0,
        spray_flow_l_s=0.1,
        locked=True,
    )
    assert mask.actions == UAV_ACTIONS
    assert mask.tolist() == [0, 0, 0, 0, 1, 0]
    assert mask.fallback_hold is False


def test_uav_mask_records_fallback_hold_when_no_progress_move_exists() -> None:
    mask = uav_action_mask(
        (0, 0),
        shape=(1, 1),
        onboard_l=0.0,
        spray_flow_l_s=0.1,
        rendezvous_target=(0, 0),
        must_approach=True,
    )
    assert mask.tolist() == [0, 0, 0, 0, 1, 0]
    assert mask.fallback_hold is True
    assert "fallback_hold" in mask.events


def test_uav_must_approach_mask_disables_spray_until_rendezvous() -> None:
    mask = uav_action_mask(
        (0, 0),
        shape=(1, 3),
        onboard_l=1.0,
        spray_flow_l_s=0.1,
        rendezvous_target=(0, 2),
        must_approach=True,
    )
    assert mask.tolist() == [0, 0, 0, 1, 0, 0]


def test_vehicle_mask_keeps_hold_when_locked_and_has_fixed_slots() -> None:
    mask = vehicle_action_mask(locked=True, candidate_slots=[{"request_id": "req-1"}], max_slots=2)
    assert mask.actions == ("hold", "slot-0", "slot-1")
    assert mask.tolist() == [1, 0, 0]
    assert mask.fallback_hold is False


def test_vehicle_mask_accepts_generator_candidates_without_losing_slots() -> None:
    candidates = ({"request_id": f"req-{i}"} for i in range(2))
    mask = vehicle_action_mask(candidate_slots=candidates, max_slots=None)
    assert mask.actions == ("hold", "slot-0", "slot-1")
    assert mask.tolist() == [1, 1, 1]
