from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from problem2.algorithms.common.gae import compute_gae
from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.common.normalization import RunningNormalizer
from problem2.algorithms.sr_mappo.rollout import RolloutBatch


def test_masked_categorical_has_exact_zero_probability_for_invalid_actions() -> None:
    logits = torch.tensor([[1.0, 2.0, -1.0, 0.5]])
    mask = torch.tensor([[True, False, True, False]])

    distribution = masked_categorical(logits, mask)

    assert torch.equal(distribution.probs[~mask], torch.zeros(2))
    assert torch.isclose(distribution.probs[mask].sum(), torch.tensor(1.0))
    sampled_action = torch.tensor([2])
    replayed = masked_categorical(logits, mask).log_prob(sampled_action)
    assert torch.isfinite(replayed).all()


def test_masked_categorical_rejects_a_row_without_a_legal_action() -> None:
    logits = torch.zeros((2, 3))
    mask = torch.tensor([[True, False, False], [False, False, False]])

    with pytest.raises(ValueError, match="at least one valid action"):
        masked_categorical(logits, mask)


def test_compute_gae_bootstraps_truncation_but_cuts_termination_and_trace() -> None:
    rewards = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    values = np.array([0.5, 0.7, 1.1], dtype=np.float64)
    next_values = np.array([0.7, 9.0, 4.0], dtype=np.float64)
    terminated = np.array([False, True, False])
    truncated = np.array([False, False, True])
    gamma = 0.9
    gae_lambda = 0.95

    advantages, returns = compute_gae(
        rewards,
        values,
        terminated,
        truncated,
        last_value=4.0,
        next_values=next_values,
        gamma=gamma,
        gae_lambda=gae_lambda,
    )

    deltas = np.array(
        [
            1.0 + gamma * 0.7 - 0.5,
            2.0 - 0.7,
            3.0 + gamma * 4.0 - 1.1,
        ]
    )
    expected_advantages = np.array(
        [deltas[0] + gamma * gae_lambda * deltas[1], deltas[1], deltas[2]]
    )
    expected_returns = expected_advantages + values

    np.testing.assert_allclose(advantages, expected_advantages, rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(returns, expected_returns, rtol=1e-6, atol=1e-6)
    assert advantages.dtype == np.float32
    assert returns.dtype == np.float32


def test_running_normalizer_can_be_frozen_and_round_tripped() -> None:
    normalizer = RunningNormalizer(shape=(2,), role="uav")
    normalizer.update(np.array([[1.0, 3.0], [3.0, 7.0]], dtype=np.float64))
    saved = copy.deepcopy(normalizer.state_dict())

    normalized = normalizer.normalize(np.array([1.0, 5.0]), update=False)
    frozen_state = normalizer.state_dict()

    np.testing.assert_allclose(normalized, np.array([-1.0, 0.0]), atol=1e-6)
    assert frozen_state["role"] == saved["role"]
    assert frozen_state["count"] == saved["count"]
    assert frozen_state["version"] == saved["version"]
    np.testing.assert_array_equal(frozen_state["mean"], saved["mean"])
    np.testing.assert_array_equal(frozen_state["variance"], saved["variance"])

    restored = RunningNormalizer(shape=(2,), role="uav")
    restored.load_state_dict(saved)
    np.testing.assert_allclose(
        restored.normalize(np.array([1.0, 5.0]), update=False), normalized
    )
    restored_state = restored.state_dict()
    assert restored_state["role"] == saved["role"]
    assert restored_state["count"] == saved["count"]
    assert restored_state["version"] == saved["version"]
    np.testing.assert_array_equal(restored_state["mean"], saved["mean"])
    np.testing.assert_array_equal(restored_state["variance"], saved["variance"])


def test_running_normalizer_keeps_role_statistics_separate() -> None:
    uav = RunningNormalizer(shape=(1,), role="uav")
    vehicle = RunningNormalizer(shape=(1,), role="vehicle")
    uav.update(np.array([[1.0], [3.0]]))
    vehicle.update(np.array([[10.0], [14.0]]))

    assert uav.state_dict()["role"] == "uav"
    assert vehicle.state_dict()["role"] == "vehicle"
    assert not np.array_equal(uav.state_dict()["mean"], vehicle.state_dict()["mean"])
    np.testing.assert_allclose(uav.normalize(np.array([[2.0]])), np.array([[0.0]]))
    np.testing.assert_allclose(vehicle.normalize(np.array([[12.0]])), np.array([[0.0]]))


def _transition(
    *,
    step: int,
    reward: float,
    value: float,
    next_value: float,
    terminated: bool = False,
    truncated: bool = False,
    valid: bool = True,
    uav_valid: bool = True,
    vehicle_valid: bool = True,
) -> dict[str, object]:
    return {
        "role": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
        "agent_id": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
        "raw_observation": {
            "uav": np.array([step, step + 1], dtype=np.float32),
            "vehicle": np.array([step + 2], dtype=np.float32),
        },
        "normalized_policy_observation": {
            "uav": np.array([step / 10], dtype=np.float32),
            "vehicle": np.array([step / 20], dtype=np.float32),
        },
        "critic_state": np.array([step, value], dtype=np.float32),
        "action": {"uav": [0, 5], "vehicle": 1},
        "action_mask": {
            "uav": np.array([[True, False, True], [True, True, False]]),
            "vehicle": np.array([True, True, False]),
        },
        "old_log_prob": {"uav": [-0.2, -0.4], "vehicle": -0.6},
        "value": value,
        "next_value": next_value,
        "reward": reward,
        "reward_components": {"coverage": reward},
        "terminated": terminated,
        "truncated": truncated,
        "valid": valid,
        "valid_actor_sample": {"uav": uav_valid, "vehicle": vehicle_valid},
        "candidate_mapping": {"vehicle": {1: "uav-0"}},
        "normalization_versions": {"uav": 3, "vehicle": 7, "return": 2},
        "episode_id": "dev-episode-001",
        "config_hash": "config-sha-001",
    }


def test_rollout_batch_preserves_replay_metadata_and_computes_team_gae() -> None:
    batch = RolloutBatch()
    first = _transition(step=0, reward=1.0, value=0.5, next_value=0.7)
    second = _transition(
        step=1,
        reward=2.0,
        value=0.7,
        next_value=4.0,
        truncated=True,
        vehicle_valid=False,
    )
    original_mask = copy.deepcopy(first["action_mask"])

    batch.add(first)
    batch.add(second)
    first["action_mask"]["uav"][0, 0] = False

    advantages, returns = batch.finish(gamma=0.9, gae_lambda=0.95)

    assert len(batch) == 2
    assert batch.transitions[0]["config_hash"] == "config-sha-001"
    assert batch.transitions[0]["episode_id"] == "dev-episode-001"
    assert batch.transitions[0]["normalized_policy_observation"] is not first[
        "normalized_policy_observation"
    ]
    np.testing.assert_array_equal(
        batch.transitions[0]["action_mask"]["uav"], original_mask["uav"]
    )
    assert batch.transitions[1]["terminated"] is False
    assert batch.transitions[1]["truncated"] is True
    np.testing.assert_allclose(advantages, batch.advantages)
    np.testing.assert_allclose(returns, batch.returns)
    assert batch.advantages.dtype == np.float32
    assert batch.returns.dtype == np.float32


def test_rollout_advantage_normalization_uses_only_valid_team_samples() -> None:
    batch = RolloutBatch()
    batch.add(_transition(step=0, reward=0.0, value=0.0, next_value=1.0, valid=True))
    batch.add(_transition(step=1, reward=0.0, value=0.0, next_value=100.0, valid=False))
    batch.finish(gamma=0.9, gae_lambda=0.95)

    normalized = batch.normalize_advantages()

    assert normalized[0] == pytest.approx(0.0)
    assert normalized[1] != 0.0
    assert batch.normalized_advantages is normalized


def test_rollout_role_valid_mask_excludes_padding_but_keeps_role_specific_forcing() -> None:
    batch = RolloutBatch()
    batch.add(_transition(step=0, reward=0.0, value=0.0, next_value=0.0))
    batch.add(
        _transition(
            step=1,
            reward=0.0,
            value=0.0,
            next_value=0.0,
            valid=True,
            vehicle_valid=False,
        )
    )
    batch.add(
        _transition(
            step=2,
            reward=0.0,
            value=0.0,
            next_value=0.0,
            valid=False,
        )
    )

    np.testing.assert_array_equal(batch.role_valid_mask("uav"), [True, True, False])
    np.testing.assert_array_equal(
        batch.role_valid_mask("vehicle"), [True, False, False]
    )
