from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from problem2.evaluation.sealed_lock import SealedAccessError, assert_no_sealed_access, assert_partition_allowed


ROOT = Path(__file__).resolve().parents[2]
DYNAMIC_MANIFEST_ROOT = ROOT / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests"
DYNAMIC_OUTPUT_ROOT = "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6"


def _validation_rows(checkpoint_hash: str, *, reduction: float, success_count: int, interaction: int) -> list[dict[str, object]]:
    return [
        {
            "checkpoint_hash": checkpoint_hash,
            "scenario_id": scenario_id,
            "reduction_rate": reduction,
            "success_at_0_85": offset < success_count,
            "interaction_count": interaction,
        }
        for offset, scenario_id in enumerate(range(20000, 20050))
    ]


def test_validation_manifest_uses_only_the_frozen_validation_panel(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_validation"]
    assert payload["scenario_ids"] == list(range(20000, 20050))
    assert payload["scenario_content"] is None
    assert payload["sealed_accessed"] is False


def test_validation_manifest_requires_deterministic_policy(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_validation"]
    assert payload["deterministic_policy"] is True


def test_validation_manifest_is_confined_to_dynamic_ecology_output(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_validation"]
    assert payload["ecology_id"] == "dynamic_pest_v1"
    assert payload["output_root"] == DYNAMIC_OUTPUT_ROOT


def test_training_manifest_is_bound_to_dynamic_ecology(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_training"]
    assert payload["ecology_id"] == "dynamic_pest_v1"
    assert all(job["ecology_id"] == "dynamic_pest_v1" for job in payload["jobs"])


def test_training_manifest_is_confined_to_dynamic_output_root(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_training"]
    assert payload["output_root"] == DYNAMIC_OUTPUT_ROOT


def test_validation_manifest_binds_a_new_evaluator_hash(
    formal_freeze_payloads: dict[str, dict[str, object]],
) -> None:
    payload = formal_freeze_payloads["g6_validation"]
    blocking_stub_hash = hashlib.sha256((ROOT / "scripts/run_g6_jobs.py").read_bytes()).hexdigest()
    assert payload["evaluator_hash"] != blocking_stub_hash


def test_replacement_manifests_live_under_the_dynamic_g5_root() -> None:
    assert (DYNAMIC_MANIFEST_ROOT / "g6-training-jobs.json").is_file()
    assert (DYNAMIC_MANIFEST_ROOT / "g6-validation-evaluations.json").is_file()


def test_g6_rejects_sealed_scenario_identity_flag_and_locator() -> None:
    with pytest.raises(SealedAccessError):
        assert_partition_allowed(gate="G6", partition="sealed_test", scenario_id=30000)
    with pytest.raises(SealedAccessError):
        assert_no_sealed_access(gate="G6", sealed_accessed=True)
    with pytest.raises(SealedAccessError):
        assert_no_sealed_access(gate="G6", path=Path("outputs/sealed/episode.jsonl"))


def test_checkpoint_selection_uses_the_frozen_rule_and_keeps_all_candidate_rows() -> None:
    from problem2.evaluation.selection import select_frozen_checkpoint

    rows = [
        *_validation_rows("d" * 64, reduction=0.79, success_count=50, interaction=10000),
        *_validation_rows("c" * 64, reduction=0.80, success_count=35, interaction=10000),
        *_validation_rows("b" * 64, reduction=0.80, success_count=40, interaction=20000),
        *_validation_rows("a" * 64, reduction=0.80, success_count=40, interaction=10000),
    ]
    selected = select_frozen_checkpoint(rows, expected_scenarios=range(20000, 20050))
    assert selected["checkpoint_hash"] == "a" * 64
    assert selected["selection_order"] == [
        "mean_validation_reduction_rate",
        "higher_success_probability",
        "earlier_interaction_count",
        "lexicographically_smaller_checkpoint_hash",
    ]
    assert len(selected["candidate_rows"]) == len(rows)
    expected_rows = {
        (row["checkpoint_hash"], row["scenario_id"], row["interaction_count"])
        for row in rows
    }
    observed_rows = {
        (row["checkpoint_hash"], row["scenario_id"], row["interaction_count"])
        for row in selected["candidate_rows"]
    }
    assert observed_rows == expected_rows


def test_checkpoint_selection_rejects_incomplete_validation_row_coverage() -> None:
    from problem2.evaluation.selection import select_frozen_checkpoint

    rows = _validation_rows("a" * 64, reduction=0.80, success_count=40, interaction=10000)
    with pytest.raises(ValueError, match="coverage"):
        select_frozen_checkpoint(rows[:-1], expected_scenarios=range(20000, 20050))


@pytest.mark.parametrize("reduction_rate", (-0.25,))
def test_checkpoint_selection_accepts_finite_negative_reduction_rate(reduction_rate: float) -> None:
    from problem2.evaluation.selection import select_frozen_checkpoint

    rows = _validation_rows("a" * 64, reduction=reduction_rate, success_count=0, interaction=10000)
    selected = select_frozen_checkpoint(rows, expected_scenarios=range(20000, 20050))

    assert selected["mean_validation_reduction_rate"] == pytest.approx(reduction_rate)


@pytest.mark.parametrize("reduction_rate", (float("nan"), float("inf"), float("-inf")))
def test_checkpoint_selection_rejects_nonfinite_reduction_rate(reduction_rate: float) -> None:
    from problem2.evaluation.selection import select_frozen_checkpoint

    rows = _validation_rows("a" * 64, reduction=reduction_rate, success_count=0, interaction=10000)
    with pytest.raises(ValueError, match="finite"):
        select_frozen_checkpoint(rows, expected_scenarios=range(20000, 20050))
