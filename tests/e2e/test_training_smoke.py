from __future__ import annotations

from math import isfinite

import pytest

from problem2.algorithms.common.checkpoint import load_checkpoint
from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.scenarios.factory import build_synthetic_scenario


CONFIG_DIR = "configs"


def _bundle():
    return build_synthetic_scenario("s1", seed=19, config_dir=CONFIG_DIR)


def _algorithm_factory() -> SRMAPPOAlgorithm:
    snapshot = _bundle().reset()
    return SRMAPPOAlgorithm(
        uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
        vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
        state_dim=len(snapshot.critic_state["vector"]),
        uav_action_dim=len(snapshot.action_masks["uav-1"]),
        vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
        hidden_dim=16,
        device="cpu",
    )


def _restored_algorithm() -> SRMAPPOAlgorithm:
    algorithm = _algorithm_factory()
    SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    return algorithm


def test_cpu_training_smoke_collects_real_episode_and_resumes_checkpoint(tmp_path) -> None:
    """A missing real runner, fake events, or lost optimizer state breaks this flow."""
    torch = pytest.importorskip("torch")
    from problem2.experiments.rollout_runner import train_policy

    algorithm = _algorithm_factory()
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    checkpoint = tmp_path / "smoke.pt"

    first_records = train_policy(
        _bundle,
        algorithm,
        trainer,
        updates=1,
        rollout_horizon=3,
        checkpoint_path=checkpoint,
    )

    assert len(first_records) == 1
    first = first_records[0]
    assert first.episode_id == "s1-seed-19"
    assert first.event_count > 0
    assert first.steps > 0
    assert first.agent_ids["uav"] == ["uav-1", "uav-2"]
    assert first.to_row()["uav_agent_ids"] == ["uav-1", "uav-2"]
    assert first.to_row()["parameter_status"] == "provisional"
    assert all(isfinite(value) for value in first.losses.values())
    assert all(rate > 0.0 for rate in trainer.learning_rates().values())
    restored, metadata = load_checkpoint(checkpoint, _restored_algorithm)
    assert metadata == {"step": 1, "format": 2}
    before_resume = [parameter.detach().clone() for parameter in restored.uav_actor.parameters()]

    resumed_records = train_policy(
        _bundle,
        restored,
        restored._trainer,
        updates=1,
        rollout_horizon=3,
        checkpoint_path=checkpoint,
        start_update=metadata["step"],
    )

    assert len(resumed_records) == 1
    assert resumed_records[0].event_count > 0
    assert all(isfinite(value) for value in resumed_records[0].losses.values())
    assert all(rate > 0.0 for rate in restored._trainer.learning_rates().values())
    assert any(
        not torch.equal(before, after.detach())
        for before, after in zip(before_resume, restored.uav_actor.parameters())
    )
    _, resumed_metadata = load_checkpoint(checkpoint, _restored_algorithm)
    assert resumed_metadata == {"step": 2, "format": 2}
