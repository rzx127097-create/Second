from __future__ import annotations

import random

import numpy as np
import pytest

from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
from problem2.algorithms.common.config_diff import configuration_diff
from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.algorithms.sr_mappo.rollout import RolloutBatch


def _algorithm(hidden_dim: int = 16) -> SRMAPPOAlgorithm:
    return SRMAPPOAlgorithm(
        uav_obs_dim=179,
        vehicle_obs_dim=28,
        state_dim=185,
        uav_action_dim=6,
        vehicle_action_dim=5,
        hidden_dim=hidden_dim,
    )


def _batch() -> RolloutBatch:
    batch = RolloutBatch()
    for step in range(3):
        batch.add(
            {
                "role": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "agent_id": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "raw_observation": {
                    "uav": np.full((2, 179), step + 1, dtype=np.float32),
                    "vehicle": np.full((1, 28), step + 2, dtype=np.float32),
                },
                "normalized_policy_observation": {
                    "uav": np.full((2, 179), step + 1, dtype=np.float32),
                    "vehicle": np.full((1, 28), step + 2, dtype=np.float32),
                },
                "critic_state": np.full(185, step + 0.5, dtype=np.float32),
                "action": {"uav": [0, 1], "vehicle": [0]},
                "action_mask": {
                    "uav": [[True, True, False, True, True, True], [True] * 6],
                    "vehicle": [[True, True, False, False, False]],
                },
                "old_log_prob": {"uav": [-1.0, -1.1], "vehicle": [-0.7]},
                "reward": 1.0,
                "value": 0.1 * step,
                "next_value": 0.1 * (step + 1),
                "terminated": step == 2,
                "truncated": False,
                "valid_actor_sample": {"uav": [True, step != 1], "vehicle": [True]},
                "candidate_mapping": {"vehicle": ["req-1", None, None, None]},
                "reward_components": {"team": 1.0},
                "normalization_versions": {"uav": step, "vehicle": step},
                "episode_id": "dev-episode",
                "config_id": "g3-test",
            }
        )
    batch.finish(gamma=0.99, gae_lambda=0.95)
    return batch


def test_actor_optimizer_parameter_sets_are_gradient_isolated() -> None:
    torch = pytest.importorskip("torch")
    algorithm = _algorithm()
    trainer = SRMAPPOTrainer(algorithm)

    loss = algorithm.uav_actor(torch.zeros(2, 179)).sum()
    loss.backward()

    assert any(parameter.grad is not None for parameter in algorithm.uav_actor.parameters())
    assert all(parameter.grad is None for parameter in algorithm.vehicle_actor.parameters())
    assert all(parameter.grad is None for parameter in algorithm.critic.parameters())
    assert set(
        parameter
        for group in trainer.optimizers["uav"].param_groups
        for parameter in group["params"]
    ).isdisjoint(
        set(
            parameter
            for group in trainer.optimizers["vehicle"].param_groups
            for parameter in group["params"]
        )
    )


def test_algorithm_act_replays_from_exact_masks_and_policy_inputs() -> None:
    torch = pytest.importorskip("torch")
    algorithm = _algorithm()
    observations = {
        "uav": np.zeros((2, 179), dtype=np.float32),
        "vehicle": np.zeros((1, 28), dtype=np.float32),
    }
    masks = {
        "uav": np.array([[True, False, True, False, False, False], [False, True, False, False, False, False]]),
        "vehicle": np.array([[True, False, True, False, False]]),
    }

    details = algorithm.act(observations, masks, deterministic=True, return_details=True)

    assert details["actions"]["uav"] == [0, 1]
    assert details["actions"]["vehicle"] == [0]
    replay_log_probs = algorithm.replay_log_probs(
        details["policy_observations"], masks, details["actions"]
    )
    np.testing.assert_allclose(replay_log_probs["uav"], details["log_probs"]["uav"], atol=1e-6)
    np.testing.assert_allclose(replay_log_probs["vehicle"], details["log_probs"]["vehicle"], atol=1e-6)
    assert torch.isfinite(torch.as_tensor(details["log_probs"]["uav"])).all()


def test_trainer_updates_roles_with_isolated_optimizers_and_counts() -> None:
    algorithm = _algorithm()
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    before_uav = [parameter.detach().clone() for parameter in algorithm.uav_actor.parameters()]
    before_vehicle = [parameter.detach().clone() for parameter in algorithm.vehicle_actor.parameters()]
    before_critic = [parameter.detach().clone() for parameter in algorithm.critic.parameters()]

    metrics = trainer.update(_batch(), epochs=2, progress=0.25)

    assert metrics["critic_updates"] == 2
    assert metrics["uav_actor_updates"] == 2
    assert metrics["vehicle_actor_updates"] == 2
    assert metrics["uav_valid_samples"] == 5
    assert metrics["vehicle_valid_samples"] == 3
    assert any(not np.array_equal(a.numpy(), b.detach().numpy()) for a, b in zip(before_uav, algorithm.uav_actor.parameters()))
    assert any(not np.array_equal(a.numpy(), b.detach().numpy()) for a, b in zip(before_vehicle, algorithm.vehicle_actor.parameters()))
    assert any(not np.array_equal(a.numpy(), b.detach().numpy()) for a, b in zip(before_critic, algorithm.critic.parameters()))
    assert trainer.learning_rates()["uav"] < 1e-3


def test_deterministic_evaluation_freezes_normalizers_byte_identically() -> None:
    algorithm = _algorithm()
    observations = {
        "uav": np.ones((2, 179), dtype=np.float32),
        "vehicle": np.ones((1, 28), dtype=np.float32),
    }
    masks = {"uav": np.ones((2, 6), dtype=bool), "vehicle": np.ones((1, 5), dtype=bool)}
    algorithm.act(observations, masks, deterministic=True, return_details=True)
    before = algorithm.normalizer_state_bytes()

    _ = algorithm.evaluate(observations, masks)

    assert algorithm.normalizer_state_bytes() == before


def test_checkpoint_roundtrip_restores_policy_trainer_normalizers_and_rng(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    random.seed(123)
    np.random.seed(123)
    torch.manual_seed(123)
    algorithm = _algorithm()
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    trainer.update(_batch(), epochs=1, progress=0.1)
    observations = {
        "uav": np.ones((2, 179), dtype=np.float32),
        "vehicle": np.ones((1, 28), dtype=np.float32),
    }
    masks = {"uav": np.ones((2, 6), dtype=bool), "vehicle": np.ones((1, 5), dtype=bool)}
    before = algorithm.act(observations, masks, deterministic=True, return_details=True)
    path = tmp_path / "g3.pt"
    save_checkpoint(path, algorithm, step=7, provenance={"config_hash": "a" * 64})
    expected_random = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = float(torch.rand(1).item())

    random.seed(999)
    np.random.seed(999)
    torch.manual_seed(999)

    def factory() -> SRMAPPOAlgorithm:
        restored = _algorithm()
        SRMAPPOTrainer(restored, learning_rate=1e-3)
        return restored

    restored, metadata = load_checkpoint(path, factory)
    after = restored.act(observations, masks, deterministic=True, return_details=True)

    assert metadata["step"] == 7
    assert metadata["provenance"]["config_hash"] == "a" * 64
    assert metadata["format_version"] == "g3-checkpoint-v1"
    assert after["actions"] == before["actions"]
    np.testing.assert_allclose(after["log_probs"]["uav"], before["log_probs"]["uav"], atol=1e-6)
    assert restored._trainer.learning_rates() == pytest.approx(trainer.learning_rates())
    assert random.random() == pytest.approx(expected_random)
    assert float(np.random.random()) == pytest.approx(expected_numpy)
    assert float(torch.rand(1).item()) == pytest.approx(expected_torch)


def test_configuration_diff_only_allows_declared_stability_flags() -> None:
    sr_config = {"algorithm_name": "SR-MAPPO", "gamma": 0.99, "stability_components": {"value_clipping": True, "layer_normalization": True}}
    mappo_config = {"algorithm_name": "SR-MAPPO", "gamma": 0.99, "stability_components": {"value_clipping": False, "layer_normalization": False}}

    diff = configuration_diff(sr_config, mappo_config)

    assert diff["changed_keys"] == ["stability_components.layer_normalization", "stability_components.value_clipping"]
    assert diff["only_declared_stability_flags_changed"] is True


def test_configuration_diff_rejects_non_stability_drift() -> None:
    sr_config = {"algorithm_name": "SR-MAPPO", "gamma": 0.99, "stability_components": {"value_clipping": True}}
    mappo_config = {"algorithm_name": "SR-MAPPO", "gamma": 0.98, "stability_components": {"value_clipping": False}}

    with pytest.raises(ValueError, match="non-stability"):
        configuration_diff(sr_config, mappo_config)
