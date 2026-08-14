from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.artifacts.statistics import hierarchical_paired_bootstrap, holm_adjust


def _row(method: str, seed: int, scenario: str, reduction: float, success: bool) -> dict[str, object]:
    return {
        "method": method,
        "scale": "s3",
        "training_seed": seed,
        "scenario_id": scenario,
        "reduction_rate": reduction,
        "success": success,
    }


def test_hierarchical_bootstrap_weights_training_seeds_before_scenarios() -> None:
    rows = []
    for index in range(100):
        rows.extend([
            _row("reference", 0, f"many-{index}", 0.0, False),
            _row("comparison", 0, f"many-{index}", 1.0, True),
        ])
    rows.extend([
        _row("reference", 1, "single", 1.0, True),
        _row("comparison", 1, "single", 0.0, False),
    ])

    estimate = hierarchical_paired_bootstrap(
        rows, reference="reference", metric="reduction_rate", draws=500, seed=7,
    )[0]

    assert estimate.observed_difference == pytest.approx(0.0)
    assert estimate.n_training_seeds == 2
    assert estimate.scenarios_per_seed == {0: 100, 1: 1}
    assert estimate.pairing_complete is True
    assert estimate.difference_direction == "comparison_minus_reference"


def test_confirmatory_bootstrap_rejects_any_missing_shared_pair() -> None:
    rows = [
        _row("reference", 0, "a", 0.8, True),
        _row("reference", 0, "b", 0.8, True),
        _row("comparison", 0, "a", 0.7, False),
    ]

    with pytest.raises(ValueError, match="incomplete confirmatory pairs"):
        hierarchical_paired_bootstrap(
            rows, reference="reference", metric="reduction_rate", draws=200, seed=3,
        )


def test_constant_paired_effect_has_deterministic_interval_and_success_risk_difference() -> None:
    rows = []
    for seed in (0, 1, 2):
        for scenario in ("a", "b"):
            rows.extend([
                _row("reference", seed, scenario, 0.8, True),
                _row("comparison", seed, scenario, 0.7, False),
            ])

    reduction = hierarchical_paired_bootstrap(
        rows, reference="reference", metric="reduction_rate", draws=500, seed=11,
        practical_equivalence_margin=0.02,
    )[0]
    success = hierarchical_paired_bootstrap(
        rows, reference="reference", metric="success", draws=500, seed=11,
    )[0]

    assert reduction.observed_difference == pytest.approx(-0.1)
    assert reduction.ci_low == pytest.approx(-0.1)
    assert reduction.ci_high == pytest.approx(-0.1)
    assert reduction.practical_interpretation == "reference_better"
    assert reduction.raw_p_value == pytest.approx(0.25)
    assert success.observed_difference == pytest.approx(-1.0)
    assert success.effect_measure == "paired_risk_difference"


def test_holm_adjust_preserves_input_order_and_rejects_invalid_probabilities() -> None:
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        holm_adjust([0.2, 1.1])


def test_condition_families_can_pair_multiple_interventions_of_one_method() -> None:
    rows = []
    for condition, reduction in (("mobile", 0.8), ("fixed", 0.6)):
        row = _row("sr_mappo_mobile", 0, "shared", reduction, False)
        row["condition_id"] = condition
        rows.append(row)

    estimate = hierarchical_paired_bootstrap(
        rows, reference="mobile", metric="reduction_rate", draws=100, seed=2,
        group_field="condition_id",
    )[0]

    assert estimate.method == "fixed"
    assert estimate.reference_method == "mobile"
    assert estimate.group_field == "condition_id"
    assert estimate.observed_difference == pytest.approx(-0.2)


def test_paired_analysis_cli_writes_traceable_json_report(tmp_path: Path) -> None:
    rows = []
    for seed in (0, 1):
        for method, reduction in (("reference", 0.8), ("comparison", 0.7)):
            row = _row(method, seed, "shared", reduction, reduction >= 0.8)
            row.update({
                "run_id": f"{method}-{seed}", "config_hash": "cfg", "git_commit": "git",
                "split": "validation", "transferred_l": 1.0, "provisional": True,
            })
            rows.append(row)
    source = tmp_path / "episodes.jsonl"
    report = tmp_path / "paired.json"
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
    )

    from scripts.analyze_paired_results import main

    assert main([
        str(source), "--method-a", "reference", "--method-b", "comparison",
        "--metric", "reduction_rate", "--draws", "200", "--report", str(report),
    ]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["difference_direction"] == "method_b_minus_method_a"
    assert payload["estimates"][0]["observed_difference"] == pytest.approx(-0.1)
