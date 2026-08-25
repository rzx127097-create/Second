from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest

from problem2.statistics.convergence import summarize_convergence
from problem2.statistics.diagnosis import diagnose_result_bundle
from problem2.statistics.equivalence import classify_equivalence
from problem2.statistics.mechanism import summarize_mechanism
from problem2.statistics.multiplicity import holm_adjust
from problem2.statistics.paired import hierarchical_paired_bootstrap


def test_convergence_uses_grid_auc_censoring_window_and_diagnostics() -> None:
    rows = [
        {"training_seed": 1, "scale": "g20", "interaction_count": 0, "reduction_rate": 0.0},
        {"training_seed": 1, "scale": "g20", "interaction_count": 50, "reduction_rate": 0.5, "clipped": True},
        {"training_seed": 1, "scale": "g20", "interaction_count": 100, "reduction_rate": 0.9, "regression": True},
        {"training_seed": 2, "scale": "g20", "interaction_count": 0, "reduction_rate": 0.0},
        {"training_seed": 2, "scale": "g20", "interaction_count": 50, "reduction_rate": 0.4, "valid_update": False},
        {"training_seed": 2, "scale": "g20", "interaction_count": 100, "reduction_rate": 0.6},
    ]
    out = summarize_convergence(rows, budget=100)
    assert out.normalized_auc == pytest.approx(0.4125)
    assert out.threshold_interactions == 100
    assert out.threshold_observed is False
    assert out.restricted_mean_time_to_threshold == 100
    assert out.final_window_sd == pytest.approx(0.15)
    assert out.across_seed_checkpoint_dispersion[50] == pytest.approx(0.05)
    assert out.invalid_update_count == 1
    assert out.clipped_count == 1
    assert out.regression_count == 1


def test_convergence_right_censors_and_rejects_duplicate_cells() -> None:
    rows = [{"training_seed": 1, "scale": "s", "interaction_count": 0, "reduction_rate": 0.1}]
    out = summarize_convergence(rows, 10)
    assert out.threshold_interactions == 10
    assert out.threshold_observed is False
    assert out.restricted_mean_time_to_threshold == 10
    with pytest.raises(ValueError, match="duplicate"):
        summarize_convergence(rows + [dict(rows[0])], 10)


def test_hierarchical_bootstrap_pairs_scenarios_and_seeds() -> None:
    rows = []
    for seed, offset in [(1, 0.0), (2, 1.0)]:
        for scenario, a, b in [(10, 2.0, 1.0), (11, 4.0, 2.0)]:
            rows.append({"training_seed": seed, "scenario_id": scenario, "method": "A", "method_order": ["A", "B"], "reduction_rate": a + offset})
            rows.append({"training_seed": seed, "scenario_id": scenario, "method": "B", "method_order": ["A", "B"], "reduction_rate": b})
    out = hierarchical_paired_bootstrap(rows, "reduction_rate", B=100, seed=4)
    assert out.observed_difference == pytest.approx(2.0)
    assert out.per_seed_summary == {1: 1.5, 2: 2.5}
    assert 0 <= out.p_value <= 1
    assert out.interval[0] <= out.observed_difference <= out.interval[1]
    assert json.dumps(out.to_dict(), sort_keys=True).encode() == json.dumps(out.to_dict(), sort_keys=True).encode()
    with pytest.raises(ValueError, match="unsupported"):
        hierarchical_paired_bootstrap(rows, "unknown", B=10)
    with pytest.raises(ValueError, match="pair"):
        hierarchical_paired_bootstrap(rows[:-1], "reduction_rate", B=10)


def test_holm_family_local_and_equivalence_boundaries() -> None:
    adjusted = holm_adjust([
        {"family": "primary", "hypothesis_id": "b", "p_value": 0.04},
        {"family": "primary", "hypothesis_id": "a", "p_value": 0.01},
        {"family": "other", "hypothesis_id": "c", "p_value": 0.03},
    ])
    assert [r.hypothesis_id for r in adjusted] == ["a", "b", "c"]
    assert [r.adjusted_p_value for r in adjusted] == pytest.approx([0.02, 0.04, 0.03])
    assert classify_equivalence((-0.02, 0.02), 0.02) == "equivalent"
    assert classify_equivalence((0.03, 0.05), 0.02) == "directional_positive"
    assert classify_equivalence((-0.05, -0.03), 0.02) == "directional_negative"
    assert classify_equivalence((0.0, 0.03), 0.02) == "inconclusive"


def test_mechanism_sign_coherence_and_ordered_diagnosis() -> None:
    rows = []
    for seed in [1, 2]:
        for scenario in [10, 11]:
            rows.extend([
                {"training_seed": seed, "scenario_id": scenario, "method": "mobile", "rendezvous_distance_m": 5, "vehicle_service_travel_m": 6, "waiting_steps": 2, "pesticide_disabled_steps": 1, "effective_spray_steps": 8, "reduction_rate": 0.9, "success_at_0_85": True},
                {"training_seed": seed, "scenario_id": scenario, "method": "fixed", "rendezvous_distance_m": 10, "vehicle_service_travel_m": 12, "waiting_steps": 4, "pesticide_disabled_steps": 2, "effective_spray_steps": 6, "reduction_rate": 0.8, "success_at_0_85": False},
            ])
    summary = summarize_mechanism(rows)
    assert summary.sign_coherence["scenario"] is True
    assert summary.interpretation == "mechanism_supported_in_tested_simulation_regime"
    report = diagnose_result_bundle(rows, [{"stage": "data_state_correctness", "status": "pass"}])
    assert report.stages[0].name == "data_state_correctness"
    assert report.stages[-1].name == "genuine_boundary_or_absence"
    assert report.complete is False


def test_cli_help_is_available() -> None:
    for script in ("scripts/analyze_g5_paired.py", "scripts/analyze_g7.py"):
        result = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()


def test_cli_requires_validated_provenance_and_rejects_sealed_locator(tmp_path) -> None:
    import json
    payload = {"rows": [], "metric": "reduction_rate"}
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/analyze_g5_paired.py", "--input", str(path)], capture_output=True, text=True)
    assert result.returncode != 0
    missing_partition = tmp_path / "missing.json"
    missing_partition.write_text(json.dumps({"validated": True, "provenance": {"status": "validated"}, "rows": []}), encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/analyze_g5_paired.py", "--input", str(missing_partition)], capture_output=True, text=True)
    assert result.returncode != 0
    sealed = tmp_path / "sealed" / "rows.json"
    sealed.parent.mkdir()
    sealed.write_text(json.dumps({"validated": True, "provenance": {"status": "validated", "partition": "sealed_test"}, "rows": []}), encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/analyze_g5_paired.py", "--input", str(sealed)], capture_output=True, text=True)
    assert result.returncode != 0
    alias = tmp_path / "sealed_alias.json"
    alias.write_text(sealed.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/analyze_g5_paired.py", "--input", str(alias)], capture_output=True, text=True)
    assert result.returncode != 0


def test_method_pair_requires_declared_order() -> None:
    rows = [
        {"training_seed": 1, "scenario_id": 1, "method": "mobile", "method_order": ["mobile", "fixed"], "reduction_rate": 10},
        {"training_seed": 1, "scenario_id": 1, "method": "fixed", "method_order": ["mobile", "fixed"], "reduction_rate": 1},
    ]
    assert hierarchical_paired_bootstrap(rows, "reduction_rate", B=20).observed_difference == pytest.approx(9)
    with pytest.raises(ValueError, match="order"):
        hierarchical_paired_bootstrap([rows[0], {**rows[1], "method_order": ["fixed", "mobile"]}], "reduction_rate", B=5)


def test_convergence_rejects_false_finite_and_reports_mixed_censoring() -> None:
    base = [
        {"training_seed": 1, "scale": "s", "interaction_count": 0, "reduction_rate": 0.0, "finite": True},
        {"training_seed": 1, "scale": "s", "interaction_count": 50, "reduction_rate": 0.9, "finite": True},
        {"training_seed": 2, "scale": "s", "interaction_count": 0, "reduction_rate": 0.0, "finite": True},
        {"training_seed": 2, "scale": "s", "interaction_count": 50, "reduction_rate": 0.2, "finite": True},
    ]
    assert summarize_convergence(base, 100).threshold_interactions == 100
    with pytest.raises(ValueError, match="finite"):
        summarize_convergence([{**base[0], "finite": False}], 100)


def test_mechanism_rejects_typed_metric_errors_and_reports_scale() -> None:
    row = {"training_seed": 1, "scenario_id": 1, "scale": "s", "method": "mobile", "rendezvous_distance_m": 1.0, "vehicle_service_travel_m": 1.0, "waiting_steps": 1, "pesticide_disabled_steps": 1, "effective_spray_steps": 2, "reduction_rate": .9, "success_at_0_85": True}
    fixed = {**row, "method": "fixed", "rendezvous_distance_m": 2.0, "vehicle_service_travel_m": 2.0, "waiting_steps": 2, "pesticide_disabled_steps": 2, "effective_spray_steps": 1, "reduction_rate": .8, "success_at_0_85": False}
    summary = summarize_mechanism([row, fixed])
    assert "scale" in summary.sign_coherence
    with pytest.raises(ValueError, match="integer"):
        summarize_mechanism([{**row, "waiting_steps": True}, fixed])
    with pytest.raises(ValueError, match="mobile.*fixed|method"):
        summarize_mechanism([{**row, "method": "x"}, {**fixed, "method": "y"}])


def test_diagnosis_requires_all_known_stages_and_pass_statuses() -> None:
    rows = [{"training_seed": 1, "scenario_id": 1}]
    report = diagnose_result_bundle(rows, [{"stage": "data_state_correctness", "status": "pass"}])
    assert report.complete is False
    with pytest.raises(ValueError, match="status"):
        diagnose_result_bundle(rows, [{"stage": "data_state_correctness", "status": "wat"}])
    with pytest.raises(ValueError, match="stage"):
        diagnose_result_bundle(rows, [{"stage": "unregistered_stage", "status": "pass"}])


def test_holm_and_equivalence_reject_bool_or_coerced_types() -> None:
    with pytest.raises(ValueError):
        holm_adjust([{"family": True, "hypothesis_id": "h", "p_value": 0.1}])
    with pytest.raises(ValueError):
        holm_adjust([{"family": "f", "hypothesis_id": "h", "p_value": True}])
    with pytest.raises(ValueError):
        holm_adjust([{"family": "f", "hypothesis_id": "h", "p_value": "0.1"}])
    with pytest.raises(ValueError):
        classify_equivalence((False, 0.1), 0.2)
    with pytest.raises(ValueError):
        classify_equivalence((0.0, 0.1), True)
    with pytest.raises(ValueError):
        classify_equivalence(("0.0", 0.1), 0.2)
