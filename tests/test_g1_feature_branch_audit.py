from __future__ import annotations

import re
import subprocess

import pytest

from scripts.audit_g1_feature_branch import (
    ADMISSIBILITY_CLASSES,
    _git_grep,
    _markdown_report,
    _parse_changed_paths,
    audit_candidate_branch,
    classify_path,
)


BASE = "origin/main"
CANDIDATE = "origin/feature/problem2-code-framework"


def test_git_grep_rejects_execution_error_and_preserves_command_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_git(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            argv,
            2,
            stdout=b"",
            stderr=b"fatal: simulated grep failure",
        )

    monkeypatch.setattr(subprocess, "run", fail_git)
    commands: list[dict[str, object]] = []

    with pytest.raises(RuntimeError, match="git grep failed"):
        _git_grep("M2", CANDIDATE, commands)

    assert commands[-1]["returncode"] == 2
    assert commands[-1]["status"] == "error"
    assert commands[-1]["stderr"] == "fatal: simulated grep failure"


def test_candidate_path_classes_cover_all_asset_types() -> None:
    assert classify_path("src/problem2/environment/air_ground_env.py") == "source"
    assert classify_path("scripts/audit_parameters.py") == "source"
    assert classify_path("configs/formal_matrix.yaml") == "configuration"
    assert classify_path("tests/marl/test_masks_and_gae.py") == "test"
    assert classify_path("docs/verification/formal-readiness-final.json") == "report"
    assert classify_path("artifacts/figures/chapter4/figure.png") == "artifact"
    assert classify_path("outputs/problem2/results.json") == "output"
    assert classify_path("artifacts/documents/chapter4.docx") == "thesis/document"
    assert classify_path("README.md") == "documentation"


def test_changed_path_parser_preserves_nul_safe_rename_and_unicode_paths() -> None:
    output = "R100\0docs/旧 名称.md\0docs/新 名称.md\0A\0scripts/审计.py\0"
    assert _parse_changed_paths(output) == [
        {
            "status": "R100",
            "old_path": "docs/旧 名称.md",
            "path": "docs/新 名称.md",
            "class": "documentation",
            "admissibility": "admissible_design_input",
        },
        {
            "status": "A",
            "path": "scripts/审计.py",
            "class": "source",
            "admissibility": "requires_independent_reverification",
        },
    ]


def test_candidate_audit_is_complete_but_does_not_accept_maturity_claims() -> None:
    report = audit_candidate_branch(BASE, CANDIDATE)
    assert report["status"] == "pass"
    assert report["status_meaning"] == "audit_executed_successfully"
    assert report["current_branch_maturity"] == "M1"
    assert report["current_gate"] == "G1"
    assert report["read_only"] is True
    assert report["base_commit"] == "2643753855c385253951dfad2c225be0b09b7e00"
    assert report["candidate_commit"] == "52a92c00467fbc3fa6a81e0fcb43469b2f8d1940"

    assert report["changed_path_count"] == len(report["changed_paths"])
    assert report["changed_paths_rendered"] == report["changed_path_count"]
    assert report["changed_paths_omitted"] == 0
    assert all(
        item["admissibility"] in ADMISSIBILITY_CLASSES
        for item in report["changed_paths"]
    )

    assert report["commands"]
    assert all(
        isinstance(command["argv"], list)
        and command["argv"][0] == "git"
        and command["returncode"] in (0, 1)
        for command in report["commands"]
    )
    contracts = {item["kind"]: item for item in report["inspected_contracts"]}
    assert set(contracts) == {"parameter", "seed", "experiment", "artifact", "sealed"}
    assert all(re.fullmatch(r"[0-9a-f]{40,64}", item["blob_id"]) for item in contracts.values())
    assert all("missing_fields" in item and "conflicts" in item for item in contracts.values())

    seed_conflicts = [
        finding for finding in report["unresolved_findings"]
        if finding["code"] == "candidate_training_seed_conflict"
    ]
    assert seed_conflicts == [
        {
            "code": "candidate_training_seed_conflict",
            "path": "configs/experiments/formal_matrix.yaml",
            "candidate_value": [0, 1, 2, 3, 4],
            "g1_value": [42, 123, 2024, 3407, 7919],
            "resolution": "requires_independent_reverification",
        }
    ]

    assert report["forbidden_name_findings"]
    assert {
        finding["classification"] for finding in report["forbidden_name_findings"]
    } <= {"guardrail_mention", "substantive_reference"}
    assert any(
        finding["classification"] == "guardrail_mention"
        for finding in report["forbidden_name_findings"]
    )

    provenance = report["provenance"]
    assert provenance["auditor"]["version"]
    assert re.fullmatch(r"[0-9a-f]{64}", provenance["auditor"]["sha256"])
    assert provenance["generated_at_utc"].endswith("+00:00")
    assert re.fullmatch(r"[0-9a-f]{40,64}", provenance["repository_commit"])

    markdown = _markdown_report(report)
    for item in report["changed_paths"]:
        assert item["path"] in markdown
    assert "Candidate training seeds `[0, 1, 2, 3, 4]` conflict" in markdown
    assert "Omitted changed paths: `0`" in markdown
