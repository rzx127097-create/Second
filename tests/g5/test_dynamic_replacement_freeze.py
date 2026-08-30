from __future__ import annotations

import json
from pathlib import Path
import sys

from scripts import _g5_cli, freeze_g5


ROOT = Path(__file__).resolve().parents[2]
DYNAMIC_ROOT = ROOT / "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5"


def test_dynamic_replacement_freeze_binds_complete_matrix_and_dynamic_inputs() -> None:
    payload = freeze_g5.freeze_dynamic_replacement(ROOT, write=False)

    assert payload["schema_version"] == "g5-dynamic-replacement-freeze-v1"
    assert payload["status"] == "pass"
    assert payload["ecology_id"] == "dynamic_pest_v1"
    assert payload["partition"] == "development"
    assert payload["replenished_resource"] == "pesticide"
    assert payload["matrix_complete"] is True
    assert payload["counts"]["jobs"] == 48
    assert payload["counts"]["episodes"] == 960
    assert payload["validation_accessed"] is False
    assert payload["sealed_accessed"] is False
    assert payload["battery_replenishment_enabled"] is False
    assert len(payload["expected_job_identities"]) == 48
    assert payload["expected_job_identities"] == payload["completed_job_identities"]
    assert payload["artifacts"]["pilot_audit"].endswith("audits/pilot-audit.json")
    assert payload["artifacts"]["pilot_artifact_manifest"].endswith("audits/pilot-artifact-manifest.json")


def test_dynamic_g6_jobs_bind_dynamic_candidate_and_budget_manifests() -> None:
    freeze = json.loads((DYNAMIC_ROOT / "freeze-manifest.json").read_text(encoding="utf-8"))
    training = json.loads(
        (DYNAMIC_ROOT / "manifests" / "g6-training-jobs.json").read_text(encoding="utf-8")
    )

    assert freeze["candidate_manifest_sha256"] != "67e6784b3d00d0385310d467c351f5b3374f02c7a7d7c22c571d4de29190419a"
    assert freeze["budget_manifest_sha256"] != "048138954f336c95e3d339aed594c71e23167ef30cc1f4a373d5c2b10bb049cb"
    assert all(
        job["dependency_graph"]["candidate_manifest_sha256"] == freeze["candidate_manifest_sha256"]
        and job["dependency_graph"]["budget_manifest_sha256"] == freeze["budget_manifest_sha256"]
        for job in training["jobs"]
    )


def test_dynamic_replacement_freeze_is_the_preflight_authority() -> None:
    report = _g5_cli.read_only_preflight(ROOT, gate="G6")

    assert report["checks"]["dynamic_g5_freeze"] is True
    assert report["checks"]["dynamic_replacement_matrix"] is True
    assert report["details"]["dynamic_g5_freeze"].endswith("freeze-manifest.json")


def test_dynamic_freeze_cli_mode_checks_the_dynamic_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["freeze_g5.py", "--dynamic-replacement", "--check-only", "--root", str(ROOT)],
    )
    assert freeze_g5.main() == 0
