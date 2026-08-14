from __future__ import annotations

from pathlib import Path

import pytest

from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.config import load_config_bundle
from problem2.experiments.methods import PRIMARY_METHODS, method_profile
from problem2.experiments.rollout_runner import train_policy
from problem2.scenarios.factory import build_synthetic_scenario


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("method", PRIMARY_METHODS)
def test_every_main_method_completes_a_real_training_update(method: str) -> None:
    """A registered main method without a real training path breaks the 4.5 matrix."""
    pytest.importorskip("torch")
    config = load_config_bundle(ROOT / "configs")
    profile = method_profile(method, config.algorithm)
    factory = lambda: build_synthetic_scenario("s1", 23, config_dir=ROOT / "configs")
    snapshot = factory().reset()
    algorithm = SRMAPPOAlgorithm(
        len(snapshot.role_observations["uav-1"]["vector"]),
        len(snapshot.role_observations["vehicle-1"]["vector"]),
        len(snapshot.critic_state["vector"]),
        len(snapshot.action_masks["uav-1"]),
        len(snapshot.action_masks["vehicle-1"]),
        hidden_dim=8,
        stability_components=profile.stability_components,
    )
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)

    records = train_policy(
        factory,
        algorithm,
        trainer,
        updates=1,
        rollout_horizon=2,
        checkpoint_path=None,
        total_updates=1,
        algorithm_config={**config.algorithm, "ppo_epochs": 1},
        method_profile=profile,
    )

    assert len(records) == 1
    assert records[0].policy_name == method
    assert records[0].training_phase
    assert records[0].losses["critic_loss"] >= 0.0
