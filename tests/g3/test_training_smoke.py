from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from problem2.config import load_g3_config
from problem2.training.development_env import DevelopmentCooperativeEnv
from problem2.training.train_g3_smoke import run_training_smoke


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "problem2" / "g3_heterogeneous_marl.yaml"


def test_development_environment_reset_is_seed_deterministic() -> None:
    config = load_g3_config(CONFIG_PATH)
    first = DevelopmentCooperativeEnv(seed=9001, config=config).reset()
    second = DevelopmentCooperativeEnv(seed=9001, config=config).reset()

    np.testing.assert_array_equal(first["observations"]["uav"], second["observations"]["uav"])
    np.testing.assert_array_equal(first["observations"]["vehicle"], second["observations"]["vehicle"])
    np.testing.assert_array_equal(first["critic_state"], second["critic_state"])
    np.testing.assert_array_equal(first["masks"]["uav"], second["masks"]["uav"])
    np.testing.assert_array_equal(first["masks"]["vehicle"], second["masks"]["vehicle"])
    assert first["candidate_mapping"] == second["candidate_mapping"]
    assert first["sealed_test_accessed"] is False


def test_development_environment_masks_are_legal_and_no_action_replacement_occurs() -> None:
    config = load_g3_config(CONFIG_PATH)
    env = DevelopmentCooperativeEnv(seed=9002, config=config)
    state = env.reset()

    assert state["observations"]["uav"].shape == (2, 179)
    assert state["observations"]["vehicle"].shape == (1, 28)
    assert state["masks"]["uav"].shape == (2, 6)
    assert state["masks"]["vehicle"].shape == (1, 5)
    assert state["masks"]["uav"].any(axis=1).all()
    assert state["masks"]["vehicle"].any(axis=1).all()

    illegal = {
        "uav": [int(np.flatnonzero(~state["masks"]["uav"][0])[0]), 0],
        "vehicle": [int(np.flatnonzero(~state["masks"]["vehicle"][0])[0])],
    }
    with pytest.raises(ValueError, match="illegal"):
        env.step(illegal)


@pytest.mark.parametrize("seed", [20000, 20049, 30000, 30099])
def test_development_environment_refuses_reserved_validation_and_sealed_seeds(seed: int) -> None:
    config = load_g3_config(CONFIG_PATH)

    with pytest.raises(ValueError, match="reserved"):
        DevelopmentCooperativeEnv(seed=seed, config=config)


def test_training_smoke_writes_finite_provenance_bound_artifacts(tmp_path: Path) -> None:
    result = run_training_smoke(
        CONFIG_PATH,
        tmp_path,
        seed=9010,
        updates=2,
        allow_noncanonical_output_root=True,
    )

    assert result["updates"] == 2
    assert result["sealed_test_accessed"] is False
    assert result["finite_loss_checks"] is True
    assert len(result["config_hash"]) == 64
    assert Path(result["checkpoint"]).exists()
    assert Path(result["raw_log"]).exists()
    assert Path(result["provenance"]).exists()

    lines = Path(result["raw_log"]).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert all(record["sealed_test_accessed"] is False for record in records)
    assert all(record["finite_losses"] is True for record in records)

    provenance = json.loads(Path(result["provenance"]).read_text(encoding="utf-8"))
    assert provenance["config_hash"] == result["config_hash"]
    assert provenance["sealed_test_accessed"] is False
    assert provenance["updates"] == 2
    assert len(provenance["scenario_seed_manifest_sha256"]) == 64
    assert provenance["scenario_seed_manifest_schema_version"] == "g1.v1"
    assert isinstance(provenance["source_tree_clean"], bool)
    assert len(provenance["source_tree_hash"]) == 64


def test_training_smoke_rejects_noncanonical_output_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="canonical G3 output root"):
        run_training_smoke(CONFIG_PATH, tmp_path, seed=9011, updates=1)
