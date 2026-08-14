from __future__ import annotations

import numpy as np
import pytest


def test_checkpoint_roundtrip_preserves_policy_and_normalization(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    algorithm = SRMAPPOAlgorithm(uav_obs_dim=4, vehicle_obs_dim=5, state_dim=6, uav_action_dim=3, vehicle_action_dim=2)
    algorithm.obs_normalizer.update(np.ones((4, 4), dtype=np.float32))
    observation = {"uav": torch.ones(1, 4), "vehicle": torch.ones(1, 5)}
    masks = {"uav": torch.ones(1, 3, dtype=torch.bool), "vehicle": torch.ones(1, 2, dtype=torch.bool)}
    before = algorithm.act(observation, masks, deterministic=True)
    path = tmp_path / "sr_mappo.pt"
    provenance = {
        "job_id": "job-17",
        "config_hash": "a" * 64,
        "protocol_hash": "b" * 64,
        "source_tree_hash": "c" * 64,
    }
    save_checkpoint(path, algorithm, step=17, provenance=provenance)
    restored, metadata = load_checkpoint(path, algorithm_factory=lambda: SRMAPPOAlgorithm(uav_obs_dim=4, vehicle_obs_dim=5, state_dim=6, uav_action_dim=3, vehicle_action_dim=2))
    after = restored.act(observation, masks, deterministic=True)
    assert metadata["step"] == 17
    assert metadata["provenance"] == provenance
    assert before == after
    np.testing.assert_allclose(restored.obs_normalizer.mean, algorithm.obs_normalizer.mean)


def test_deterministic_evaluation_does_not_update_normalization() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm

    algorithm = SRMAPPOAlgorithm(uav_obs_dim=4, vehicle_obs_dim=5, state_dim=6, uav_action_dim=3, vehicle_action_dim=2)
    algorithm.obs_normalizer.update(np.zeros((3, 4), dtype=np.float32))
    mean_before = algorithm.obs_normalizer.mean.copy()
    count_before = algorithm.obs_normalizer.count
    algorithm.evaluate({"uav": torch.ones(1, 4), "vehicle": torch.ones(1, 5)}, {"uav": torch.ones(1, 3, dtype=torch.bool), "vehicle": torch.ones(1, 2, dtype=torch.bool)})
    np.testing.assert_array_equal(algorithm.obs_normalizer.mean, mean_before)
    assert algorithm.obs_normalizer.count == count_before
