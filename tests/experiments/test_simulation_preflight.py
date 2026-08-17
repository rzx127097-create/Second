from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.simulation_preflight import audit_simulation_preflight
from problem2.experiments.simulation_preflight import load_simulation_profile
from problem2.experiments.job_identity import capture_git_provenance


ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"


def _config_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "configs"
    shutil.copytree(CONFIGS, destination)
    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "docs" / "verification").mkdir(parents=True)
    shutil.copy2(
        ROOT / "docs" / "verification" / "frozen-road-jodhpur.json",
        tmp_path / "docs" / "verification" / "frozen-road-jodhpur.json",
    )
    return destination


def test_assumption_sources_are_warnings_not_runtime_errors(tmp_path: Path) -> None:
    report = audit_simulation_preflight(_config_copy(tmp_path))

    assert report.ready is True
    assert report.errors == ()
    assert report.warnings
    assert all(issue.level == "warning" for issue in report.warnings)
    assert report.to_dict()["evidence_mode"] == "controlled_simulation"


def test_missing_assumption_rationale_is_a_technical_error(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    profile = config_dir / "simulation_profile.yaml"
    profile.write_text(
        profile.read_text(encoding="utf-8").replace(
            "assumption_rationale: Retained as an explicit controlled-simulation assumption.",
            "assumption_rationale: ''",
            1,
        ),
        encoding="utf-8",
    )

    report = audit_simulation_preflight(config_dir)

    assert report.ready is False
    assert any(issue.code == "missing_assumption_rationale" for issue in report.errors)


def test_profile_runtime_value_mismatch_is_an_error(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    registry = config_dir / "parameter_registry.yaml"
    registry.write_text(
        registry.read_text(encoding="utf-8").replace("value: 1.0\n    unit: L", "value: 1.25\n    unit: L", 1),
        encoding="utf-8",
    )

    report = audit_simulation_preflight(config_dir)

    assert report.ready is False
    assert any(issue.code == "profile_runtime_mismatch" for issue in report.errors)


def test_unstable_field_update_is_an_error(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    field = config_dir / "field_dynamics.yaml"
    field.write_text(
        field.read_text(encoding="utf-8").replace("value: 1.5\n    unit: m/s", "value: 100.0\n    unit: m/s", 1),
        encoding="utf-8",
    )

    report = audit_simulation_preflight(config_dir)

    assert report.ready is False
    assert any(issue.code == "wind_cfl_violation" for issue in report.errors)


def test_disabled_sr_mappo_stability_component_is_an_error(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    algorithm = config_dir / "algorithms" / "sr_mappo.yaml"
    algorithm.write_text(
        algorithm.read_text(encoding="utf-8").replace(
            "observation_normalization: true",
            "observation_normalization: false",
            1,
        ),
        encoding="utf-8",
    )

    report = audit_simulation_preflight(config_dir)

    assert report.ready is False
    assert any(issue.code == "disabled_sr_mappo_stability" for issue in report.errors)


def test_inactive_resource_pilot_is_warning_not_activation_evidence(tmp_path: Path) -> None:
    report_path = tmp_path / "resource.json"
    report_path.write_text(
        json.dumps({"activated": False, "record_count": 2}),
        encoding="utf-8",
    )

    report = audit_simulation_preflight(
        _config_copy(tmp_path), resource_report=report_path,
    )

    assert report.ready is True
    assert any(issue.code == "resource_mechanism_inactive" for issue in report.warnings)


def test_malformed_resource_pilot_is_an_error(tmp_path: Path) -> None:
    report_path = tmp_path / "resource.json"
    report_path.write_text(json.dumps({"activated": True}), encoding="utf-8")

    report = audit_simulation_preflight(
        _config_copy(tmp_path), resource_report=report_path,
    )

    assert report.ready is False
    assert any(issue.code == "invalid_resource_report" for issue in report.errors)


def _activated_resource_payload() -> dict[str, object]:
    metrics = {
        "request_count": 1.0,
        "requested_l": 0.8,
        "transferred_l": 0.8,
        "pesticide_disabled_s": 10.0,
    }
    return {
        "activated": True,
        "condition_means": {
            "finite_no_support": dict(metrics),
            "matched_fixed": dict(metrics),
            "sr_mappo_mobile": dict(metrics),
            "teleport_diagnostic": dict(metrics),
        },
    }


def test_activated_resource_report_without_identity_is_only_a_warning(tmp_path: Path) -> None:
    report_path = tmp_path / "resource.json"
    report_path.write_text(json.dumps(_activated_resource_payload()), encoding="utf-8")

    report = audit_simulation_preflight(
        _config_copy(tmp_path), resource_report=report_path,
    )

    assert report.ready is True
    assert report.errors == ()
    assert any(issue.code == "resource_report_identity_missing" for issue in report.warnings)


def test_resource_report_identity_mismatch_is_an_error(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    payload = _activated_resource_payload()
    payload.update({
        "config_hash": "0" * 64,
        "simulation_profile_sha256": load_simulation_profile(config_dir).sha256,
        "git_commit": capture_git_provenance(str(ROOT)).commit,
        "source_tree_hash": capture_git_provenance(str(ROOT)).source_tree_hash,
    })
    report_path = tmp_path / "resource.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    report = audit_simulation_preflight(
        config_dir, resource_report=report_path,
    )

    assert report.ready is False
    assert any(issue.code == "resource_report_identity_mismatch" for issue in report.errors)


def test_resource_report_with_current_identity_is_current_evidence(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    config = load_config_bundle(config_dir)
    provenance = capture_git_provenance(str(ROOT))
    payload = _activated_resource_payload()
    payload.update({
        "config_hash": config_identity(config),
        "simulation_profile_sha256": load_simulation_profile(config_dir).sha256,
        "git_commit": provenance.commit,
        "source_tree_hash": provenance.source_tree_hash,
    })
    report_path = tmp_path / "resource.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    report = audit_simulation_preflight(
        config_dir, resource_report=report_path,
    )

    assert report.ready is True
    assert report.errors == ()
    assert not any(issue.code == "resource_report_identity_missing" for issue in report.warnings)


def test_simulation_preflight_cli_is_deterministic_and_warning_tolerant(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.audit_simulation_preflight import main

    report_path = tmp_path / "preflight.json"
    arguments = ["--config-dir", str(CONFIGS), "--report", str(report_path)]
    assert main(arguments) == 0
    first = capsys.readouterr().out
    assert main(arguments) == 0
    second = capsys.readouterr().out

    assert json.loads(first) == json.loads(second)
    assert json.loads(first)["ready"] is True
    assert json.loads(first)["warnings"]


def test_simulation_preflight_cli_rejects_corrupted_road_hash(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_dir = _config_copy(tmp_path)
    environment = config_dir / "environment.yaml"
    environment.write_text(
        environment.read_text(encoding="utf-8").replace(
            "source_sha256: 62bfda5137bb5e29b46084fe00176313febc4c8d45fffca112c3c8ff3c2fab05",
            "source_sha256: " + "0" * 64,
            1,
        ),
        encoding="utf-8",
    )
    from scripts.audit_simulation_preflight import main

    assert main([
        "--config-dir", str(config_dir),
        "--report", str(tmp_path / "preflight.json"),
        "--strict",
    ]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is False
    assert any(issue["code"] == "road_hash_mismatch" for issue in payload["errors"])
