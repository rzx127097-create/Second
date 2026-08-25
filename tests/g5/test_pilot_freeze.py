from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.experiments.g5_contract import BudgetDecision, load_g5_contract
from problem2.training.budget import aggregate_runtime, select_pilot_budget
from problem2.training.pilot import (
    PILOT_CONDITIONS,
    PILOT_METHODS,
    PILOT_SCALES,
    build_pilot_matrix,
    freeze_validation_candidates,
    run_pilot_matrix,
)


ROOT = Path(__file__).resolve().parents[2]


def test_pilot_matrix_covers_exact_development_panel_without_duplicates() -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)
    assert len(jobs) == 5 * 17 * 2 * 3 * 20
    assert {job.method for job in jobs} == set(PILOT_METHODS)
    assert {job.condition_id for job in jobs} == set(PILOT_CONDITIONS)
    assert {job.scale for job in jobs} == set(PILOT_SCALES)
    assert {job.training_seed for job in jobs} == {51001, 51002, 51003}
    assert {job.scenario_id for job in jobs} == set(range(10000, 10020))
    assert all(job.partition == "development" for job in jobs)
    identities = [job.identity for job in jobs]
    assert len(identities) == len(set(identities))


def test_runtime_aggregation_is_conservative_and_budget_selection_is_frozen() -> None:
    rows = [
        {"method_id": method, "scale_id": "g30x50_d4", "interactions": 100, "elapsed_seconds": seconds}
        for method, seconds in zip(
            ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"),
            (1.0, 1.2, 0.8, 1.5, 1.1),
        )
    ]
    aggregate = aggregate_runtime(rows)
    assert aggregate["g30x50_d4"]["maddpg_mobile"]["seconds_per_interaction"] == 0.015
    decision = select_pilot_budget(rows)
    assert isinstance(decision, BudgetDecision)
    assert decision.selected_budget == 200000
    assert decision.checkpoint_count == 20
    with pytest.raises(ValueError, match="frozen candidate"):
        select_pilot_budget(rows, candidate_budgets=(100, 200))


def test_candidate_freeze_has_four_hashed_candidates_and_rejects_validation_mutation(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    decision = BudgetDecision(selected_budget=50000, checkpoint_interval=2500, checkpoint_count=20, projected_slowest_hours=1.0)
    path = tmp_path / "validation-candidates.json"
    payload = freeze_validation_candidates(contract, decision, path)
    assert path.exists()
    assert payload["status"] == "frozen_before_validation"
    assert payload["validation_accessed"] is False
    assert payload["sealed_accessed"] is False
    assert payload["equal_environment_interactions"] == 50000
    assert payload["scenario_panel"]["count"] == 50
    assert all(len(candidates) == 4 for candidates in payload["candidates"].values())
    for candidates in payload["candidates"].values():
        assert all(len(item["config_hash"]) == 64 for item in candidates)
    frozen = json.loads(path.read_text(encoding="utf-8"))
    frozen["validation_accessed"] = True
    path.write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(ValueError, match="validation access"):
        freeze_validation_candidates(contract, decision, path)


def test_run_pilot_matrix_writes_descriptive_development_records_and_audit(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)[:1]

    def fake_runner(job, device, max_interactions, output_root):
        output = Path(output_root) / "fake"
        output.mkdir(parents=True, exist_ok=True)
        return {
            "method": job["method"],
            "algorithm_id": job["method"],
            "condition_id": job["condition_id"],
            "partition": "development",
            "scenario_id": job["scenario_id"],
            "training_seed": job["training_seed"],
            "interactions": max_interactions,
            "updates": 1,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    result = run_pilot_matrix(contract, tmp_path, jobs=jobs, interactions=2, runner=fake_runner)
    assert result["status"] == "pass"
    assert result["job_count"] == 1
    assert result["coverage"]["scales"] == ["g20x20_d2"]
    assert result["validation_accessed"] is False
    assert result["sealed_accessed"] is False
    records = Path(result["episodes_path"]).read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    assert json.loads(records[0])["data_status"] == "development_pilot_descriptive"


def test_runner_preserves_pilot_scale_and_scenario_identity_in_training_log(tmp_path: Path) -> None:
    from problem2.training.runner import run_training_job

    result = run_training_job(
        {
            "method": "iql_mobile",
            "condition_id": "sr_mappo_mobile",
            "training_seed": 51001,
            "scenario_id": 10007,
            "scale": "g30x50_d4",
            "partition": "development",
            "source_root": str(ROOT),
        },
        "cpu",
        1,
        tmp_path,
    )
    row = json.loads(Path(result["training_log"]).read_text(encoding="utf-8").splitlines()[0])
    assert row["scenario_id"] == 10007
    assert row["scale"] == "g30x50_d4"
