from __future__ import annotations

import json
from pathlib import Path

import pytest

from problem2.experiments.job_identity import GitProvenance
from problem2.experiments.m3_pilot import (
    build_m3_manifest,
    load_m3_manifest,
    write_m3_manifest,
)
from problem2.experiments.orchestrator import Chapter45Orchestrator


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
