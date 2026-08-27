from __future__ import annotations

import json
from dataclasses import replace
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
    verify_pilot_artifacts,
)


ROOT = Path(__file__).resolve().parents[2]


def test_pilot_matrix_covers_exact_development_panel_without_duplicates() -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)
    assert len(jobs) == 5 * 17 * 2 * 3
    assert {job.method for job in jobs} == set(PILOT_METHODS)
    assert {job.condition_id for job in jobs} == set(PILOT_CONDITIONS)
    assert {job.scale for job in jobs} == set(PILOT_SCALES)
    assert {job.training_seed for job in jobs} == {51001, 51002, 51003}
    assert {job.scenario_id for job in jobs} == {10000}
    assert all(job.scenario_ids == tuple(range(10000, 10020)) for job in jobs)
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
    payload = freeze_validation_candidates(contract, decision, path, allow_noncanonical_output_root=True)
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
        freeze_validation_candidates(contract, decision, path, allow_noncanonical_output_root=True)
    with pytest.raises(ValueError, match="frozen budget"):
        freeze_validation_candidates(
            contract,
            BudgetDecision(selected_budget=123, checkpoint_interval=1, checkpoint_count=20, projected_slowest_hours=1.0),
            tmp_path / "invalid-budget.json",
            allow_noncanonical_output_root=True,
        )


def test_candidate_freeze_rejects_any_canonical_manifest_drift(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    decision = BudgetDecision(selected_budget=50000, checkpoint_interval=2500, checkpoint_count=20, projected_slowest_hours=1.0)
    path = tmp_path / "validation-candidates.json"
    freeze_validation_candidates(contract, decision, path, allow_noncanonical_output_root=True)
    frozen = json.loads(path.read_text(encoding="utf-8"))
    frozen["checkpoint_count"] = 21
    path.write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest drift"):
        freeze_validation_candidates(contract, decision, path, allow_noncanonical_output_root=True)


def test_run_pilot_matrix_writes_descriptive_development_records_and_audit(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)

    def fake_runner(job, device, max_interactions, output_root):
        output = Path(output_root) / "fake"
        output.mkdir(parents=True, exist_ok=True)
        return {
            "method": job["method"],
            "algorithm_id": job["method"],
            "condition_id": job["condition_id"],
            "partition": "development",
            "scale": job["scale"],
            "scenario_id": job["scenario_id"],
            "scenario_ids": list(job["scenario_ids"]),
            "training_seed": job["training_seed"],
            "interactions": max_interactions,
            "updates": 1,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    result = run_pilot_matrix(
        contract,
        tmp_path,
        jobs=jobs,
        interactions=2,
        runner=fake_runner,
        allow_noncanonical_output_root=True,
    )
    assert result["status"] == "pass"
    assert result["job_count"] == 510
    assert result["episode_count"] == 10200
    assert result["coverage"]["scales"] == ["g20x20_d2", "g30x50_d4"]
    assert result["validation_accessed"] is False
    assert result["sealed_accessed"] is False
    records = Path(result["episodes_path"]).read_text(encoding="utf-8").splitlines()
    assert len(records) == 10200
    assert {json.loads(row)["scenario_id"] for row in records} == set(range(10000, 10020))
    assert json.loads(records[0])["data_status"] == "development_pilot_descriptive"
    assert all(json.loads(row)["record_type"] == "scenario_reference" for row in records)
    assert all(json.loads(row)["scenario_execution"] is False for row in records)
    assert all(json.loads(row)["training_result"]["training_scenario_id"] == 10000 for row in records)
    assert Path(result["artifact_manifest_path"]).exists()
    verify_pilot_artifacts(
        contract,
        result["episodes_path"],
        result["audit_path"],
        result["artifact_manifest_path"],
        allow_noncanonical_output_root=True,
    )


def test_pilot_output_root_requires_explicit_test_override(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    with pytest.raises(ValueError, match="canonical G5 output root"):
        run_pilot_matrix(contract, tmp_path, jobs=build_pilot_matrix(contract), interactions=1, runner=lambda *_args: {})


def test_pilot_artifact_manifest_detects_consolidated_table_tampering(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)

    def fake_runner(job, device, max_interactions, output_root):
        return {
            "method": job["method"],
            "algorithm_id": job["method"],
            "condition_id": job["condition_id"],
            "partition": "development",
            "scale": job["scale"],
            "scenario_id": job["scenario_id"],
            "scenario_ids": list(job["scenario_ids"]),
            "training_seed": job["training_seed"],
            "interactions": max_interactions,
            "updates": 1,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    result = run_pilot_matrix(
        contract,
        tmp_path,
        jobs=jobs,
        interactions=1,
        runner=fake_runner,
        allow_noncanonical_output_root=True,
    )
    episodes = Path(result["episodes_path"])
    episodes.write_bytes(episodes.read_bytes() + b"tampered\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_pilot_artifacts(
            contract,
            result["episodes_path"],
            result["audit_path"],
            result["artifact_manifest_path"],
            allow_noncanonical_output_root=True,
        )


def test_run_pilot_matrix_rejects_incomplete_or_non_development_jobs(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    malformed = replace(build_pilot_matrix(contract)[0], scenario_ids=(10000, *range(20000, 20019)))
    with pytest.raises(ValueError, match="scenario"):
        run_pilot_matrix(contract, tmp_path, jobs=(malformed,), interactions=1, runner=lambda *_args: {})


def test_runner_rejects_forbidden_injected_preflight(tmp_path: Path) -> None:
    from problem2.training.runner import run_training_job

    with pytest.raises(RuntimeError, match="preflight"):
        run_training_job(
            {
                "method": "iql_mobile",
                "condition_id": "sr_mappo_mobile",
                "training_seed": 51001,
                "scenario_id": 10007,
                "scale": "g30x50_d4",
                "partition": "development",
                "source_root": str(ROOT),
                "_preflight": {
                    "status": "pass",
                    "validation_accessed": True,
                    "sealed_accessed": False,
                    "battery_replenishment_enabled": False,
                },
            },
            "cpu",
            1,
            tmp_path,
        )


def test_runner_rejects_injected_preflight_without_determinism_fields(tmp_path: Path) -> None:
    from problem2.training.runner import run_training_job

    with pytest.raises(RuntimeError, match="preflight"):
        run_training_job(
            {
                "method": "iql_mobile",
                "condition_id": "sr_mappo_mobile",
                "training_seed": 51001,
                "scenario_id": 10007,
                "scale": "g30x50_d4",
                "partition": "development",
                "source_root": str(ROOT),
                "_preflight": {
                    "schema_version": "g5-smoke-preflight-v1",
                    "status": "pass",
                    "device": "cpu",
                    "validation_accessed": False,
                    "sealed_accessed": False,
                    "battery_replenishment_enabled": False,
                },
            },
            "cpu",
            1,
            tmp_path,
        )


def test_runner_rejects_non_development_scenario_panel(tmp_path: Path) -> None:
    from problem2.training.runner import run_training_job

    with pytest.raises(ValueError, match="scenario IDs"):
        run_training_job(
            {
                "method": "iql_mobile",
                "condition_id": "sr_mappo_mobile",
                "training_seed": 51001,
                "scenario_id": 10007,
                "scenario_ids": [10000, 20000],
                "scale": "g30x50_d4",
                "partition": "development",
                "source_root": str(ROOT),
            },
            "cpu",
            1,
            tmp_path,
        )


def test_run_pilot_matrix_rejects_runner_identity_and_numeric_drift(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)

    def bad_runner(job_payload, device, max_interactions, output_root):
        return {
            "method": "wrong",
            "algorithm_id": "wrong",
            "condition_id": "wrong",
            "scale": "wrong",
            "scenario_id": 99999,
            "training_seed": 1,
            "partition": "development",
            "interactions": 0,
            "finite_metrics": False,
            "evaluation_frozen": False,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    result = run_pilot_matrix(
        contract,
        tmp_path,
        jobs=jobs,
        interactions=1,
        runner=bad_runner,
        allow_noncanonical_output_root=True,
    )
    assert result["status"] == "fail"
    assert "mismatched method" in result["failures"][0]["error"]


def test_run_pilot_matrix_rejects_runner_scenario_panel_drift(tmp_path: Path) -> None:
    contract = load_g5_contract(ROOT)
    jobs = build_pilot_matrix(contract)

    def forged_runner(job_payload, device, max_interactions, output_root):
        return {
            "method": job_payload["method"],
            "algorithm_id": job_payload["method"],
            "condition_id": job_payload["condition_id"],
            "scale": job_payload["scale"],
            "training_seed": job_payload["training_seed"],
            "scenario_id": job_payload["scenario_id"],
            "scenario_ids": [10000],
            "partition": "development",
            "interactions": max_interactions,
            "finite_metrics": True,
            "evaluation_frozen": True,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }

    result = run_pilot_matrix(
        contract,
        tmp_path,
        jobs=jobs,
        interactions=1,
        runner=forged_runner,
        allow_noncanonical_output_root=True,
    )
    assert result["status"] == "fail"
    assert "mismatched scenario_ids" in result["failures"][0]["error"]


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
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["scale"] == "g30x50_d4"
    assert manifest["partition"] == "development"
    assert manifest["scenario_id"] == 10007
    assert manifest["scenario_ids"] == list(range(10000, 10020))
    assert manifest["training_seed"] == 51001


@pytest.mark.parametrize("field", ("selected_budget", "checkpoint_interval", "checkpoint_count"))
def test_candidate_freeze_rejects_float_budget_fields(tmp_path: Path, field: str) -> None:
    contract = load_g5_contract(ROOT)
    values = {"selected_budget": 50000, "checkpoint_interval": 2500, "checkpoint_count": 20, "projected_slowest_hours": 1.0}
    values[field] = float(values[field])
    with pytest.raises(ValueError, match="frozen budget"):
        freeze_validation_candidates(contract, BudgetDecision(**values), tmp_path / "validation-candidates.json", allow_noncanonical_output_root=True)
