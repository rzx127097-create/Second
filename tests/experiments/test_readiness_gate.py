from __future__ import annotations

from pathlib import Path

from problem2.experiments.readiness import audit_repository_readiness


ROOT = Path(__file__).resolve().parents[2]


def test_repository_readiness_reports_blockers_instead_of_only_a_boolean() -> None:
    report = audit_repository_readiness(ROOT / "configs")

    assert report.formal_ready is False
    assert report.highest_gate == "M2"
    assert {gate["name"] for gate in report.gates} >= {
        "parameters", "scenarios", "road_source", "algorithm", "protocol",
    }
    assert any("parameter" in blocker.lower() for blocker in report.blockers)
    assert any("dynamics" in blocker.lower() or "road" in blocker.lower() for blocker in report.blockers)


def test_readiness_gate_accepts_only_explicitly_verified_component_reports() -> None:
    report = audit_repository_readiness(ROOT / "configs")

    assert report.formal_ready is False
    assert report.to_dict()["formal_ready"] is False
    assert all("provisional" not in str(gate) or gate["ready"] is False for gate in report.gates)


def test_readiness_cli_writes_machine_readable_gate_report(tmp_path: Path) -> None:
    from scripts.audit_readiness import main
    import json

    output = tmp_path / "readiness.json"
    assert main(["--config-dir", str(ROOT / "configs"), "--report", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["formal_ready"] is False
    assert payload["highest_gate"] == "M2"
