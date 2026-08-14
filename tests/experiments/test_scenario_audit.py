from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
import pytest

from problem2.experiments.readiness import audit_scenario_registry


ROOT = Path(__file__).resolve().parents[2]


def _documents() -> tuple[dict, dict, dict]:
    scenarios = yaml.safe_load((ROOT / "configs/scenarios.yaml").read_text(encoding="utf-8"))
    scales = yaml.safe_load((ROOT / "configs/scales.yaml").read_text(encoding="utf-8"))
    matrix = yaml.safe_load((ROOT / "configs/experiments/formal_matrix.yaml").read_text(encoding="utf-8"))
    scenarios["status"] = "verified"
    scenarios["source_kind"] = "frozen_gis"
    scenarios["dynamics_kind"] = "calibrated_reaction_diffusion_advection"
    scenarios["source_metadata_hash"] = "a" * 64
    scales["status"] = "verified"
    matrix["status"] = "verified"
    return scenarios, scales, matrix


def test_scenario_audit_checks_disjoint_splits_and_physical_cell_sizes() -> None:
    scenarios, scales, matrix = _documents()
    report = audit_scenario_registry(scenarios, scales, matrix)

    assert report.ready is True
    assert report.issues == ()
    assert report.details["split_counts"] == {"train": 18, "validation": 12, "sealed_test": 18}
    assert report.details["cell_size_m"]["s1"] == pytest.approx([30.0, 25.0])
    assert report.details["cell_size_m"]["s6"] == pytest.approx([10.0, 10.0])


def test_scenario_audit_rejects_duplicate_seed_offsets_and_split_overlap() -> None:
    scenarios, scales, matrix = _documents()
    broken = deepcopy(scenarios)
    broken["scenarios"]["val_001"]["seed_offset"] = broken["scenarios"]["train_001"]["seed_offset"]
    duplicate = deepcopy(broken["scenarios"]["train_001"])
    duplicate["scenario_id"] = "train_001"
    broken["scenarios"]["train_001_copy"] = duplicate

    report = audit_scenario_registry(broken, scales, matrix)

    assert report.ready is False
    assert any(issue.code == "duplicate_seed_offset" for issue in report.issues)
    assert any(issue.code == "duplicate_scenario_id" for issue in report.issues)


def test_repository_scenario_registry_is_not_formal_ready() -> None:
    scenarios, scales, matrix = (
        yaml.safe_load((ROOT / "configs/scenarios.yaml").read_text(encoding="utf-8")),
        yaml.safe_load((ROOT / "configs/scales.yaml").read_text(encoding="utf-8")),
        yaml.safe_load((ROOT / "configs/experiments/formal_matrix.yaml").read_text(encoding="utf-8")),
    )
    report = audit_scenario_registry(scenarios, scales, matrix)

    assert report.ready is False
    assert any(issue.code == "registry_provisional" for issue in report.issues)
    assert any(issue.code == "missing_source_metadata" for issue in report.issues)


def test_scenario_audit_cli_writes_report(tmp_path: Path) -> None:
    report_path = tmp_path / "scenario-audit.json"
    from scripts.audit_scenarios import main

    assert main([
        "--scenarios", str(ROOT / "configs/scenarios.yaml"),
        "--scales", str(ROOT / "configs/scales.yaml"),
        "--matrix", str(ROOT / "configs/experiments/formal_matrix.yaml"),
        "--report", str(report_path),
    ]) == 0
    import json

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["name"] == "scenarios"
    assert payload["ready"] is False
    assert payload["details"]["split_counts"]["sealed_test"] == 18
