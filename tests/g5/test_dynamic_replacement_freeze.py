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
