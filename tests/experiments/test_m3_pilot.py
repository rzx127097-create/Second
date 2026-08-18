from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from problem2.experiments.job_identity import GitProvenance
from problem2.experiments.m3_audit import audit_m3_pilot
from problem2.experiments.m3_pilot import (
    build_m3_manifest,
    load_m3_manifest,
    write_m3_manifest,
)
from problem2.experiments.orchestrator import Chapter45Orchestrator
from tests.m3_fixtures import materialize_complete_m3_evidence


ROOT = Path(__file__).resolve().parents[2]


def _orchestrator(tmp_path: Path, *, dirty: bool = False) -> Chapter45Orchestrator:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path / "runs")
    orchestrator.git_provenance = GitProvenance(
        orchestrator.git_commit,
        "a" * 64,
        dirty,
    )
    return orchestrator


def _resource_report(
    orchestrator: Chapter45Orchestrator,
    path: Path,
    **overrides: object,
) -> Path:
    payload: dict[str, object] = {
        "activated": True,
        "diagnosis": "resource_service_chain_activated",
        "config_hash": orchestrator.config_hash,
        "git_commit": orchestrator.git_provenance.commit,
        "source_tree_hash": orchestrator.git_provenance.source_tree_hash,
        "simulation_profile_sha256": "b" * 64,
        "record_count": 45,
        "provisional": True,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_m3_manifest_has_fifty_jobs_and_one_hundred_evaluations(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    report = _resource_report(orchestrator, tmp_path / "resource.json")

    manifest = build_m3_manifest(
        orchestrator,
        resource_report_path=report,
        created_at="2026-08-18T00:00:00+00:00",
    )

    assert manifest["schema_version"] == 1
    assert manifest["profile"]["scales"] == ["s1", "s6"]
    assert manifest["profile"]["execution_profile"] == "simulation"
    assert len(manifest["jobs"]) == 50
    assert len(manifest["evaluations"]) == 100
    assert {row["scenario_id"] for row in manifest["evaluations"]} == {
        "val_001", "val_s1_002", "val_s6_001", "val_s6_002",
    }
    assert len({row["job_id"] for row in manifest["jobs"]}) == 50
    assert all(row["condition_id"] != "direct" for row in manifest["jobs"])
    assert all(row["split"] == "validation" for row in manifest["evaluations"])
    assert len(str(manifest["semantic_sha256"])) == 64


def test_m3_manifest_reuses_identical_semantics_without_rewriting(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    report = _resource_report(orchestrator, tmp_path / "resource.json")
    first = build_m3_manifest(
        orchestrator, resource_report_path=report,
        created_at="2026-08-18T00:00:00+00:00",
    )
    path = tmp_path / "m3.json"
    written, reused = write_m3_manifest(path, first)
    original_bytes = written.read_bytes()
    second = build_m3_manifest(
        orchestrator, resource_report_path=report,
        created_at="2026-08-19T00:00:00+00:00",
    )

    same_path, reused_again = write_m3_manifest(path, second)

    assert reused is False
    assert reused_again is True
    assert same_path == written
    assert same_path.read_bytes() == original_bytes
    assert load_m3_manifest(path)["created_at"] == "2026-08-18T00:00:00+00:00"


def test_m3_manifest_rejects_dirty_source(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, dirty=True)
    report = _resource_report(orchestrator, tmp_path / "resource.json")
    with pytest.raises(ValueError, match="clean Git worktree"):
        build_m3_manifest(orchestrator, resource_report_path=report)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"activated": False}, "activated"),
        ({"diagnosis": "resource_service_chain_not_activated"}, "diagnosis"),
        ({"config_hash": "c" * 64}, "config hash"),
        ({"git_commit": "d" * 40}, "Git commit"),
        ({"source_tree_hash": "e" * 64}, "source-tree hash"),
    ],
)
def test_m3_manifest_rejects_inactive_or_stale_resource_evidence(
    tmp_path: Path, overrides: dict[str, object], message: str,
) -> None:
    orchestrator = _orchestrator(tmp_path)
    report = _resource_report(
        orchestrator, tmp_path / "resource.json", **overrides,
    )
    with pytest.raises(ValueError, match=message):
        build_m3_manifest(orchestrator, resource_report_path=report)


def test_m3_manifest_rejects_missing_s6_validation_scenario(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    orchestrator.config.experiments["validation_scenarios"] = [
        scenario_id
        for scenario_id in orchestrator.config.experiments["validation_scenarios"]
        if scenario_id != "val_s6_002"
    ]
    report = _resource_report(orchestrator, tmp_path / "resource.json")
    with pytest.raises(ValueError, match="exactly two validation scenarios.*s6"):
        build_m3_manifest(orchestrator, resource_report_path=report)


def test_m3_manifest_rejects_conflicting_existing_file(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path)
    report = _resource_report(orchestrator, tmp_path / "resource.json")
    path = tmp_path / "m3.json"
    write_m3_manifest(path, build_m3_manifest(orchestrator, resource_report_path=report))
    other_report = _resource_report(
        orchestrator, tmp_path / "other-resource.json", record_count=50,
    )
    conflicting = build_m3_manifest(orchestrator, resource_report_path=other_report)

    with pytest.raises(ValueError, match="conflicting M3 manifest"):
        write_m3_manifest(path, conflicting)


def _complete_audit_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object], list[Path]]:
    orchestrator = _orchestrator(tmp_path)
    resource = _resource_report(orchestrator, tmp_path / "resource.json")
    manifest = build_m3_manifest(
        orchestrator,
        resource_report_path=resource,
        created_at="2026-08-18T00:00:00+00:00",
    )
    manifest_path = tmp_path / "m3.json"
    write_m3_manifest(manifest_path, manifest)
    run_root = tmp_path / "runs"
    evaluations = materialize_complete_m3_evidence(manifest, run_root)
    return manifest_path, run_root, manifest, evaluations


def _read_object(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_object(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_m3_audit_accepts_complete_fifty_job_hundred_evaluation_evidence(
    tmp_path: Path,
) -> None:
    manifest_path, run_root, _, _ = _complete_audit_fixture(tmp_path)

    report = audit_m3_pilot(manifest_path, output_root=run_root)

    assert report["m3_ready"] is True
    assert report["highest_maturity"] == "M3"
    assert report["counts"] == {
        "expected_jobs": 50,
        "completed_jobs": 50,
        "expected_evaluations": 100,
        "valid_evaluations": 100,
    }
    assert all(check["passed"] for check in report["checks"])


@pytest.mark.parametrize(
    ("case", "failed_check"),
    [
        ("missing_job", "job_records"),
        ("failed_status", "job_records"),
        ("checkpoint_sha_mismatch", "checkpoint_integrity"),
        ("checkpoint_step", "checkpoint_integrity"),
        ("duplicate_run_id", "evaluation_identity"),
        ("nonfinite_metric", "metric_finiteness"),
        ("stale_resource_hash", "resource_activation"),
        ("identity_mismatch", "evaluation_identity"),
        ("sealed_test", "sealed_test_exclusion"),
    ],
)
def test_m3_audit_fails_closed_and_preserves_incomplete_evidence(
    tmp_path: Path,
    case: str,
    failed_check: str,
) -> None:
    manifest_path, run_root, manifest, evaluations = _complete_audit_fixture(tmp_path)
    first_job = run_root / str(manifest["jobs"][0]["job_record_path"])
    first_checkpoint = run_root / str(manifest["jobs"][0]["checkpoint_path"])
    if case == "missing_job":
        first_job.unlink()
    elif case == "failed_status":
        payload = _read_object(first_job)
        payload["status"] = "failed"
        _write_object(first_job, payload)
    elif case == "checkpoint_sha_mismatch":
        first_checkpoint.write_bytes(b"tampered")
    elif case == "checkpoint_step":
        payload = _read_object(first_job)
        payload["checkpoint_step"] = int(payload["target_updates"]) - 1
        _write_object(first_job, payload)
    elif case == "duplicate_run_id":
        first = _read_object(evaluations[0])
        second = _read_object(evaluations[1])
        second["run_id"] = first["run_id"]
        _write_object(evaluations[1], second)
    elif case == "nonfinite_metric":
        payload = _read_object(evaluations[0])
        payload["reduction_rate"] = math.nan
        _write_object(evaluations[0], payload)
    elif case == "stale_resource_hash":
        resource_path = Path(str(manifest["resource_activation"]["path"]))
        payload = _read_object(resource_path)
        payload["record_count"] = int(payload["record_count"]) + 1
        _write_object(resource_path, payload)
    elif case == "identity_mismatch":
        payload = _read_object(evaluations[0])
        payload["method"] = "mappo_mobile"
        _write_object(evaluations[0], payload)
    elif case == "sealed_test":
        payload = _read_object(evaluations[0])
        payload["split"] = "sealed_test"
        _write_object(evaluations[0], payload)

    source_snapshots = {
        path: path.read_bytes()
        for path in (manifest_path, *[value for value in evaluations if value.exists()])
    }
    report = audit_m3_pilot(manifest_path, output_root=run_root)

    assert report["m3_ready"] is False
    assert report["highest_maturity"] == "M2"
    checks = {check["name"]: check for check in report["checks"]}
    assert checks[failed_check]["passed"] is False
    assert all(path.read_bytes() == value for path, value in source_snapshots.items())
