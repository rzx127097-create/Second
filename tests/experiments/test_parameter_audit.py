from __future__ import annotations

from pathlib import Path

import pytest

from problem2.experiments.readiness import audit_parameter_registry


ROOT = Path(__file__).resolve().parents[2]


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "symbol": "q",
        "meaning": "test parameter",
        "value": 1.0,
        "unit": "L",
        "min": 0.1,
        "max": 2.0,
        "source_type": "manual",
        "source_id": "manual:test-001",
        "source_value": 1.0,
        "source_unit": "L",
        "conversion": "value = source_value",
        "status": "verified",
        "scope": "main",
    }
    record.update(overrides)
    return record


def test_parameter_audit_requires_traceable_source_and_conversion() -> None:
    report = audit_parameter_registry(
        {
            "status": "verified",
            "parameters": {
                "uav_onboard_pesticide": _record(),
                "uav_usable_fraction": _record(
                    source_type="assumption",
                    source_id="pending-equipment-or-field-source",
                    source_value=None,
                    source_unit=None,
                    conversion=None,
                    status="verified",
                ),
            },
        }
    )

    assert report.ready is False
    assert any(issue.code == "unverified_source" for issue in report.issues)
    assert any(issue.code == "missing_parameter" for issue in report.issues)


def test_parameter_audit_rejects_out_of_range_and_inconsistent_units() -> None:
    record = _record(value=3.0, source_value=3.0, source_unit="m/s", unit="L")
    report = audit_parameter_registry(
        {
            "status": "verified",
            "parameters": {name: record for name in (
                "uav_onboard_pesticide", "uav_usable_fraction", "uav_spray_flow",
                "uav_speed", "vehicle_inventory", "vehicle_transfer_rate",
                "vehicle_service_capacity", "service_setup_time", "rendezvous_radius",
                "vehicle_speed", "decision_dt", "request_safety_margin",
            )},
        }
    )

    assert report.ready is False
    assert any(issue.code == "value_out_of_range" for issue in report.issues)
    assert any(issue.code == "unit_mismatch" for issue in report.issues)


def test_repository_registry_is_explicitly_provisional_until_sources_are_added() -> None:
    import yaml

    document = yaml.safe_load(
        (ROOT / "configs" / "parameter_registry.yaml").read_text(encoding="utf-8")
    )
    report = audit_parameter_registry(document)

    assert report.ready is False
    assert report.status == "provisional"
    assert report.missing_parameters == ()
    # Public product references now cover inventory, service capacity and
    # transfer-rate ranges; six project-specific values still need direct
    # equipment, field or numerical evidence.
    assert len([issue for issue in report.issues if issue.code == "unverified_source"]) == 6


def test_verified_parameter_fixture_has_no_blocking_issues() -> None:
    names = (
        "uav_onboard_pesticide", "uav_usable_fraction", "uav_spray_flow", "uav_speed",
        "vehicle_inventory", "vehicle_transfer_rate", "service_setup_time",
        "vehicle_service_capacity", "request_safety_margin", "rendezvous_radius",
        "vehicle_speed", "decision_dt",
    )
    registry = {"status": "verified", "parameters": {name: _record() for name in names}}
    registry["parameters"]["uav_usable_fraction"] = _record(
        value=0.8, unit="1", min=0.1, max=1.0, source_value=0.8, source_unit="1"
    )
    report = audit_parameter_registry(registry)

    assert report.ready is True
    assert report.issues == ()


def test_parameter_audit_cli_writes_report(tmp_path: Path) -> None:
    report_path = tmp_path / "parameter-audit.json"
    from scripts.audit_parameters import main

    assert main([
        str(ROOT / "configs" / "parameter_registry.yaml"),
        "--report",
        str(report_path),
    ]) == 0
    import json

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["name"] == "parameters"
    assert payload["ready"] is False
    assert payload["status"] == "provisional"
