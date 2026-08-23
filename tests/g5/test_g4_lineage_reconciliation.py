from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit_g4_lineage import G4LineageError, audit_g4_lineage


ROOT = Path(__file__).resolve().parents[2]
G4_ROOT = ROOT / "outputs/problem2_sr_mappo_v1/g4"


def test_lineage_audit_rejects_nonexistent_recorded_commit(tmp_path: Path) -> None:
    repo_copy = tmp_path / "repo"
    repo_copy.mkdir()
    (repo_copy / "HANDOFFG4.md").write_text(
        "generator commit: 4e8156712986\n", encoding="utf-8"
    )

    with pytest.raises(G4LineageError, match="not a Git object"):
        audit_g4_lineage(repo_copy, repo_copy / "outputs/problem2_sr_mappo_v1/g4")


def test_lineage_audit_requires_one_exact_generator_tuple() -> None:
    report = audit_g4_lineage(ROOT, G4_ROOT)

    assert report.status == "pass"
    assert len(report.generator_commits) == 1
    assert len(report.source_trees) == 1
