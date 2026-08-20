from __future__ import annotations

import inspect

import numpy as np
import pytest

from problem2.algorithms.sr_mappo.actors import RoleActor
from problem2.algorithms.sr_mappo.critic import CentralCritic
from problem2.algorithms.sr_mappo.losses import entropy_bonus, ppo_policy_loss, value_loss
from problem2.environment.action_masks import (
    convert_g2_masks_to_roles,
)
from problem2.environment.observations import (
    build_role_observations,
    build_structured_critic_state,
)


def _snapshot() -> dict:
    return {
        "step": 3,
        "max_steps": 32,
        "field_summary": [0.2, 0.4, 0.1, 0.3, 0.05, 0.6, 0.1, 0.2],
        "uavs": [
            {
                "id": "uav-0",
                "x": 2.0,
                "y": 3.0,
                "pesticide_l": 0.8,
                "capacity_l": 1.0,
                "service_locked": False,
                "active_request_id": None,
                "request_remaining_l": 0.0,
            },
            {
                "id": "uav-1",
                "x": 7.0,
                "y": 5.0,
                "pesticide_l": 0.3,
                "capacity_l": 1.0,
                "service_locked": True,
                "active_request_id": "req-1",
                "request_remaining_l": 0.7,
            },
        ],
        "vehicle": {
            "id": "vehicle-0",
            "x": 4.0,
            "y": 4.0,
            "inventory_l": 2.0,
            "capacity_l": 4.0,
            "mode": "idle",
            "active_request_id": None,
        },
        "requests": [
            {
                "id": "req-1",
                "uav_id": "uav-1",
                "remaining_l": 0.7,
                "urgency": 0.9,
                "road_distance_m": 3.0,
                "valid": True,
            }
        ],
        "candidate_slots": [
            {
                "slot": 0,
                "request_id": "req-1",
                "uav_id": "uav-1",
                "remaining_l": 0.7,
                "urgency": 0.9,
                "road_distance_m": 3.0,
                "valid": True,
            }
        ],
        "critic_only": [99.0, 88.0, 77.0],
    }


def test_role_observation_and_critic_dimensions_are_frozen() -> None:
    snapshot = _snapshot()

    observations = build_role_observations(
        snapshot,
        uav_count=2,
        max_candidate_slots=4,
    )
    critic_state = build_structured_critic_state(
        snapshot,
        uav_count=2,
        max_candidate_slots=4,
    )

    assert observations["uav"].shape == (2, 179)
    assert observations["vehicle"].shape == (1, 28)
    assert critic_state.shape == (185,)
    assert np.isfinite(observations["uav"]).all()
    assert np.isfinite(observations["vehicle"]).all()
    assert np.isfinite(critic_state).all()


def test_role_observations_exclude_critic_only_fields() -> None:
    first = _snapshot()
    second = _snapshot()
    second["critic_only"] = [100000.0, -100000.0, 3.0]

    first_observations = build_role_observations(first, 2, 4)
    second_observations = build_role_observations(second, 2, 4)
    first_critic = build_structured_critic_state(first, 2, 4)
    second_critic = build_structured_critic_state(second, 2, 4)

    np.testing.assert_array_equal(
        first_observations["uav"], second_observations["uav"]
    )
    np.testing.assert_array_equal(
        first_observations["vehicle"], second_observations["vehicle"]
    )
    assert not np.array_equal(first_critic, second_critic)


def test_actor_interfaces_accept_only_role_observation() -> None:
    actor_parameters = list(inspect.signature(RoleActor.forward).parameters)
    critic_parameters = list(inspect.signature(CentralCritic.forward).parameters)
    assert actor_parameters == ["self", "observation"]
    assert critic_parameters == ["self", "state"]

    torch = pytest.importorskip("torch")
    actor = RoleActor(179, 6, hidden_dim=16)
    observation = torch.zeros(2, 179)
    assert actor(observation).shape == (2, 6)
    with pytest.raises(TypeError):
        actor(observation, critic_only=torch.zeros(2, 3))


def test_role_actors_have_disjoint_parameters_and_critic_is_scalar() -> None:
    torch = pytest.importorskip("torch")
    uav_actor = RoleActor(179, 6, hidden_dim=16)
    vehicle_actor = RoleActor(28, 5, hidden_dim=16)
    critic = CentralCritic(185, hidden_dim=16)

    assert set(map(id, uav_actor.parameters())).isdisjoint(
        set(map(id, vehicle_actor.parameters()))
    )
    assert critic(torch.zeros(4, 185)).shape == (4,)


def test_g2_masks_convert_to_role_masks_without_action_replacement() -> None:
    uav_mask, vehicle_mask = convert_g2_masks_to_roles(
        uav_mask=[True, True, False, True, False, True],
        vehicle_mask=[True, False, True, False, True],
        candidate_slot_mask=[True, False, True, False],
    )

    assert uav_mask.tolist() == [True, False, True, False, True, True]
    assert vehicle_mask.tolist() == [True, True, False, True, False]


def test_g2_vehicle_mask_allows_hold_only_without_candidate_slots() -> None:
    _, vehicle_mask = convert_g2_masks_to_roles(
        uav_mask=[True, True, True, True, True, True],
        vehicle_mask=[True, False, False, False, False],
        candidate_slot_mask=[False, False, False, False],
    )

    assert vehicle_mask.tolist() == [True, False, False, False, False]


def test_g2_vehicle_mask_validates_candidate_slot_identity() -> None:
    _, vehicle_mask = convert_g2_masks_to_roles(
        uav_mask=[True, True, True, True, True, True],
        vehicle_mask=[True, False, False, False, False],
        candidate_slot_mask=[True, False, False, False],
        candidate_mapping=["req-1", None, None, None],
    )
    assert vehicle_mask.tolist() == [True, True, False, False, False]

    with pytest.raises(ValueError, match="candidate slot"):
        convert_g2_masks_to_roles(
            uav_mask=[True, True, True, True, True, True],
            vehicle_mask=[True, False, False, False, False],
            candidate_slot_mask=[True, False, False, False],
            candidate_mapping=[None, None, None, None],
        )


def test_policy_value_and_entropy_losses_are_finite() -> None:
    torch = pytest.importorskip("torch")
    new_log_prob = torch.tensor([-0.2, -0.4])
    old_log_prob = torch.tensor([-0.3, -0.4])
    advantages = torch.tensor([1.0, -1.0])
    policy = ppo_policy_loss(new_log_prob, old_log_prob, advantages)
    value = value_loss(
        torch.tensor([1.2, 0.4]),
        torch.tensor([1.0, 0.5]),
        torch.tensor([1.0, 0.0]),
    )
    entropy = entropy_bonus(torch.tensor([0.2, 0.4]))

    assert torch.isfinite(policy)
    assert torch.isfinite(value)
    assert torch.isfinite(entropy)
