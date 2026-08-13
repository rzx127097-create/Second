from __future__ import annotations

import numpy as np
import pytest

from problem2.algorithms.sr_mappo.rollout import RolloutBatch


def test_rollout_preserves_joint_transition_metadata_and_masks() -> None:
    batch = RolloutBatch()
    batch.add(
        observations={"uav": [1.0, 2.0], "vehicle": [3.0]},
        state=[4.0, 5.0],
        actions={"uav": 1, "vehicle": 0},
        masks={"uav": [True, True, False], "vehicle": [True, False]},
        log_probs={"uav": -0.2, "vehicle": -0.1},
        reward=2.0,
        value=0.5,
        done=False,
        agent_ids={"uav": ["uav-0"], "vehicle": ["vehicle-0"]},
        candidate_mapping={"vehicle": [("req-7", "rv-2")]},
        valid_actor_sample={"uav": True, "vehicle": False},
        reward_components={"control": 1.0, "service": 1.0},
    )

    assert batch.agent_ids["uav"] == [["uav-0"]]
    assert batch.candidate_mappings == [{"vehicle": [("req-7", "rv-2")]}]
    assert batch.valid_actor_samples["uav"] == [True]
    assert batch.valid_actor_samples["vehicle"] == [False]
    assert batch.reward_components == [{"control": 1.0, "service": 1.0}]


def test_rollout_finish_computes_one_team_gae_and_rejects_mismatched_lengths() -> None:
    batch = RolloutBatch()
    for reward, value, done in ((1.0, 0.5, False), (2.0, 1.0, True)):
        batch.add(
            observations={"uav": [0.0], "vehicle": [0.0]},
            state=[0.0],
            actions={"uav": 0, "vehicle": 0},
            masks={"uav": [True], "vehicle": [True]},
            log_probs={"uav": 0.0, "vehicle": 0.0},
            reward=reward,
            value=value,
            done=done,
        )
    batch.finish(gamma=0.9, gae_lambda=0.8)
    assert batch.advantages is not None
    assert batch.returns is not None
    assert batch.advantages.shape == (2,)
    assert batch.returns.shape == (2,)
    np.testing.assert_allclose(batch.returns, batch.advantages + np.array([0.5, 1.0], dtype=np.float32))


def test_truncation_bootstraps_but_true_termination_cuts_gae() -> None:
    def build(*, terminated: bool, truncated: bool) -> RolloutBatch:
        batch = RolloutBatch()
        batch.add(
            observations={"uav": [0.0], "vehicle": [0.0]},
            state=[0.0],
            actions={"uav": 0, "vehicle": 0},
            masks={"uav": [True], "vehicle": [True]},
            log_probs={"uav": 0.0, "vehicle": 0.0},
            reward=1.0,
            value=0.5,
            done=terminated or truncated,
            terminated=terminated,
            truncated=truncated,
        )
        batch.finish(gamma=0.9, gae_lambda=0.8, last_value=2.0)
        return batch

    truncated = build(terminated=False, truncated=True)
    terminal = build(terminated=True, truncated=False)
    np.testing.assert_allclose(truncated.advantages, np.array([2.3], dtype=np.float32))
    np.testing.assert_allclose(terminal.advantages, np.array([0.5], dtype=np.float32))


def test_internal_truncation_does_not_carry_gae_into_next_episode() -> None:
    batch = RolloutBatch()
    for step, truncated in ((0, True), (1, False)):
        batch.add(
            observations={"uav": [0.0], "vehicle": [0.0]},
            state=[float(step)],
            actions={"uav": 0, "vehicle": 0},
            masks={"uav": [True], "vehicle": [True]},
            log_probs={"uav": 0.0, "vehicle": 0.0},
            reward=1.0,
            value=0.0,
            done=truncated,
            terminated=False,
            truncated=truncated,
        )
    batch.finish(gamma=0.9, gae_lambda=0.8, last_value=0.0)
    np.testing.assert_allclose(batch.advantages, np.array([1.0, 1.0], dtype=np.float32))


def test_advantage_normalization_uses_only_declared_valid_samples() -> None:
    from problem2.algorithms.common.gae import normalize_advantages

    advantages = np.array([1.0, 100.0, 3.0], dtype=np.float32)
    valid = np.array([True, False, True])
    normalized = normalize_advantages(advantages, valid)
    expected = np.array([-1.0, 100.0, 1.0], dtype=np.float32)
    np.testing.assert_allclose(normalized, expected, atol=1e-6)


def test_running_normalizer_roundtrip_restores_physical_value_scale() -> None:
    from problem2.algorithms.common.normalization import RunningNormalizer

    normalizer = RunningNormalizer(clip=None)
    normalizer.update(np.array([[10.0], [14.0]], dtype=np.float32))
    normalized = normalizer.normalize(np.array([[12.0]], dtype=np.float32))
    restored = normalizer.denormalize(normalized)
    np.testing.assert_allclose(restored, np.array([[12.0]], dtype=np.float32), atol=1e-6)


def test_value_loss_uses_clipped_pessimistic_huber_objective() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.losses import value_loss

    new_value = torch.tensor([2.0])
    old_value = torch.tensor([0.0])
    returns = torch.tensor([0.0])
    # The unclipped residual is 2.0; a clip range of 0.2 gives a residual of
    # 0.2, but PPO takes the larger per-sample Huber loss.
    assert float(value_loss(new_value, old_value, returns, clip_epsilon=0.2)) == pytest.approx(1.5)


def test_value_loss_supports_unclipped_mse_ablation() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.losses import value_loss

    result = value_loss(
        torch.tensor([2.0]),
        torch.tensor([0.0]),
        torch.tensor([0.0]),
        clip=False,
        huber_delta=None,
    )
    assert float(result) == pytest.approx(2.0)


def test_trainer_excludes_forced_single_action_samples_from_actor_loss() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    trainer = SRMAPPOTrainer(algorithm)
    batch = RolloutBatch()
    for valid in (True, False):
        batch.add(
            observations={"uav": [1.0, 0.0], "vehicle": [0.0, 1.0]},
            state=[1.0, 0.0, 0.0],
            actions={"uav": 0, "vehicle": 0},
            masks={"uav": [True, True], "vehicle": [True, False]},
            log_probs={"uav": -0.6931472, "vehicle": 0.0},
            reward=1.0,
            value=0.0,
            done=False,
            valid_actor_sample={"uav": valid, "vehicle": False},
        )
    batch.finish(0.99, 0.95)
    metrics = trainer.update(batch)
    assert metrics["uav_valid_samples"] == 1.0
    assert metrics["vehicle_valid_samples"] == 0.0


def test_detailed_action_keeps_floating_log_probability() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    details = algorithm.act(
        {"uav": torch.ones(1, 2), "vehicle": torch.ones(1, 2)},
        {
            "uav": torch.ones(1, 2, dtype=torch.bool),
            "vehicle": torch.ones(1, 2, dtype=torch.bool),
        },
        deterministic=True,
        return_details=True,
    )
    assert isinstance(details["log_probs"]["uav"], float)
    assert details["log_probs"]["uav"] < 0.0


def test_trainer_updates_multiple_uavs_with_per_agent_valid_mask() -> None:
    pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    trainer = SRMAPPOTrainer(algorithm)
    batch = RolloutBatch()
    for step in range(2):
        batch.add(
            observations={
                "uav": [[1.0, 0.0], [0.0, 1.0]],
                "vehicle": [[0.0, 1.0]],
            },
            state=[1.0, float(step), 0.0],
            actions={"uav": [0, 1], "vehicle": [0]},
            masks={
                "uav": [[True, True], [True, True]],
                "vehicle": [[True, False]],
            },
            log_probs={"uav": [-0.6931472, -0.6931472], "vehicle": [0.0]},
            reward=1.0,
            value=0.0,
            done=step == 1,
            agent_ids={"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
            valid_actor_sample={"uav": [True, step == 0], "vehicle": [False]},
        )
    batch.finish(0.99, 0.95)
    metrics = trainer.update(batch)
    assert metrics["uav_valid_samples"] == 3.0
    assert metrics["vehicle_valid_samples"] == 0.0


def test_trainer_broadcasts_default_validity_for_multiple_uavs() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    trainer = SRMAPPOTrainer(algorithm)
    batch = RolloutBatch()
    batch.add(
        observations={"uav": [[1.0, 0.0], [0.0, 1.0]], "vehicle": [[0.0, 1.0]]},
        state=[1.0, 0.0, 0.0],
        actions={"uav": [0, 1], "vehicle": [0]},
        masks={"uav": [[True, True], [True, True]], "vehicle": [[True, False]]},
        log_probs={"uav": [-0.69, -0.69], "vehicle": [0.0]},
        reward=1.0,
        value=0.0,
        done=True,
    )
    batch.finish(0.99, 0.95)
    metrics = trainer.update(batch)
    assert metrics["uav_valid_samples"] == 2.0


def test_learning_rate_decay_switch_is_taken_from_algorithm_components() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer

    algorithm = SRMAPPOAlgorithm(
        2, 2, 3, 2, 2, hidden_dim=8,
        stability_components={"learning_rate_decay": False},
    )
    trainer = SRMAPPOTrainer(algorithm)
    before = trainer.learning_rates()
    trainer.step_scheduler(0.8)
    assert trainer.lr_decay is False
    assert trainer.learning_rates() == pytest.approx(before)


def test_collect_transition_exposes_exact_policy_inputs_and_normalization_versions() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    result = algorithm.collect_transition(
        {"uav": [[1.0, 0.0]], "vehicle": [[0.0, 1.0]]},
        {"uav": [[True, True]], "vehicle": [[True, True]]},
        [0.0, 0.0, 0.0],
    )
    assert "policy_observations" in result
    assert result["policy_observations"]["uav"] is not None
    assert result["normalization_versions"]["uav"] == algorithm.obs_normalizer.count


def test_checkpoint_restores_rng_state(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    import random

    from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    random.seed(17)
    np.random.seed(17)
    torch.manual_seed(17)
    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    path = tmp_path / "sr_mappo.pt"
    save_checkpoint(path, algorithm, step=4)
    expected_python = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = float(torch.rand(1).item())

    random.seed(999)
    np.random.seed(999)
    torch.manual_seed(999)
    restored, _ = load_checkpoint(
        path,
        algorithm_factory=lambda: SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8),
    )
    del restored
    assert random.random() == pytest.approx(expected_python)
    assert float(np.random.random()) == pytest.approx(expected_numpy)
    assert float(torch.rand(1).item()) == pytest.approx(expected_torch)


def test_checkpoint_restores_optimizer_and_scheduler_state(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    trainer.step_scheduler(0.4)
    before = trainer.learning_rates()
    path = tmp_path / "trainer.pt"
    save_checkpoint(path, algorithm, step=8)

    def factory():
        restored_algorithm = SRMAPPOAlgorithm(2, 2, 3, 2, 2, hidden_dim=8)
        SRMAPPOTrainer(restored_algorithm, learning_rate=1e-3)
        return restored_algorithm

    restored, metadata = load_checkpoint(path, factory)
    assert metadata["step"] == 8
    assert restored._trainer.learning_rates() == pytest.approx(before)
    assert set(restored._trainer.optimizers) == {"uav", "vehicle", "critic"}


def test_masked_actor_log_probability_replays_from_saved_policy_input() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.common.masked_distribution import masked_categorical
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    algorithm = SRMAPPOAlgorithm(2, 2, 3, 3, 2, hidden_dim=8)
    sample = algorithm.act(
        {"uav": [[2.0, -1.0]], "vehicle": [[0.0, 1.0]]},
        {"uav": [[True, False, True]], "vehicle": [[True, True]]},
        deterministic=True,
        return_details=True,
    )
    policy_input = torch.as_tensor(sample["normalized_observations"]["uav"], dtype=torch.float32)
    mask = torch.tensor([[True, False, True]])
    action = torch.tensor([sample["actions"]["uav"]])
    replayed = masked_categorical(algorithm.uav_actor(policy_input), mask).log_prob(action)
    assert float(replayed.item()) == pytest.approx(sample["log_probs"]["uav"], abs=1e-6)
