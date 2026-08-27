from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_checkpoint
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.preflight import run_preflight
from problem2.training.runner import (
    ALL_CONDITION_TYPES,
    _state_digest as evaluation_state_digest,
    run_training_job,
)


ROOT = Path(__file__).resolve().parents[2]
METHODS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile")


@pytest.fixture(scope="module")
def contract():
    return load_g5_contract(ROOT)


def _job(method: str, condition: str | None = None) -> dict[str, object]:
    return {
        "method": method,
        "condition_id": condition or method,
        "training_seed": 51001,
        "scenario_id": 10000,
        "partition": "development",
        "source_root": str(ROOT),
    }


def test_cpu_preflight_is_development_only_and_records_determinism() -> None:
    report = run_preflight("cpu", ROOT)
    assert report["status"] == "pass"
    assert report["device"] == "cpu"
    assert report["validation_accessed"] is False
    assert report["sealed_accessed"] is False
    assert report["deterministic_algorithms"] is True
    assert report["battery_replenishment_enabled"] is False


@pytest.mark.parametrize("method", METHODS)
def test_runner_emits_finite_update_exact_roles_checkpoint_and_frozen_eval(tmp_path: Path, contract, method: str) -> None:
    result = run_training_job(_job(method), "cpu", 4, tmp_path)
    assert result["method"] == method
    assert result["updates"] >= 1
    assert result["interactions"] == 4
    assert result["finite_metrics"] is True
    assert result["validation_accessed"] is False
    assert result["sealed_accessed"] is False
    assert result["role_shapes"] == {"uav": [2, 179], "vehicle": [1, 28]}
    assert result["mask_shapes"] == {"uav": [2, 6], "vehicle": [1, 5]}
    assert result["evaluation_frozen"] is True
    assert Path(result["checkpoint"]).exists()
    assert Path(result["manifest"]).exists()
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["status"] == "pass"
    assert manifest["artifacts"]


def test_completed_smoke_checkpoint_contains_the_post_update_policy(tmp_path: Path, contract) -> None:
    result = run_training_job(_job("sr_mappo_mobile"), "cpu", 4, tmp_path)
    restored, _ = load_checkpoint(
        result["checkpoint"],
        lambda: build_algorithm("sr_mappo_mobile", contract, "cpu"),
        expected_provenance=result["provenance"],
    )

    assert evaluation_state_digest(restored) == result["algorithm_state_digest"]


def test_runner_supports_interruption_resume_equivalence(tmp_path: Path) -> None:
    full = run_training_job(_job("iql_mobile"), "cpu", 4, tmp_path / "full")
    first = run_training_job({**_job("iql_mobile"), "stop_after_interactions": 2}, "cpu", 4, tmp_path / "resume")
    resumed = run_training_job({**_job("iql_mobile"), "resume_from": first["checkpoint"], "resume_reference": full}, "cpu", 4, tmp_path / "resume")
    assert first["interrupted"] is True
    assert resumed["interactions"] == full["interactions"]
    assert resumed["resume_equivalent"] is True
    assert resumed["evaluation_actions"] == full["evaluation_actions"]
    assert resumed["resume_comparison"]["algorithm_state_equal"] is True
    assert resumed["resume_comparison"]["metrics_equal"] is True
    assert resumed["resume_comparison"]["diagnostics_equal"] is True


def test_resume_rejects_non_equivalent_reference(tmp_path: Path) -> None:
    full = run_training_job(_job("iql_mobile"), "cpu", 4, tmp_path / "full")
    first = run_training_job({**_job("iql_mobile"), "stop_after_interactions": 2}, "cpu", 4, tmp_path / "resume")
    with pytest.raises(ValueError, match="resume equivalence"):
        run_training_job({**_job("iql_mobile"), "resume_from": first["checkpoint"], "resume_reference": {**full, "algorithm_state_digest": "bad"}}, "cpu", 4, tmp_path / "resume")


@pytest.mark.parametrize("seed", (42, 51004, 20000, 30000))
def test_runner_rejects_non_development_training_seed(tmp_path: Path, seed: int) -> None:
    with pytest.raises(ValueError, match="development training seed"):
        run_training_job({**_job("iql_mobile"), "training_seed": seed}, "cpu", 1, tmp_path)


def test_runner_rejects_validation_and_sealed_partitions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="development"):
        run_training_job({**_job("sr_mappo_mobile"), "partition": "validation", "scenario_id": 20000}, "cpu", 1, tmp_path)


def test_condition_boundary_does_not_swap_learning_method(tmp_path: Path) -> None:
    result = run_training_job(_job("iql_mobile", "sr_mappo_astar"), "cpu", 1, tmp_path)
    assert result["method"] == "iql_mobile"
    assert result["algorithm_id"] == "iql_mobile"


def test_all_frozen_condition_types_are_registered() -> None:
    assert set(ALL_CONDITION_TYPES) >= {
        "sr_mappo_fixed", "sr_mappo_astar", "sr_mappo_nearest", "sr_mappo_urgency",
        "sr_mappo_two_stage", "no_observation_normalization", "learning_rate",
    }
