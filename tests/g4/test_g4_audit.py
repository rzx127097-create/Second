from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

import problem2.experiments.g4_audit as g4_audit
from problem2.experiments.g4_audit import audit_g4_mechanism, build_g4_artifact_manifest
from problem2.experiments.g4_counterfactual import run_counterfactual_probe

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/evidence/g4/g4_contract.yaml"


def _record(policy: str, *, fingerprint: str = "same-input", waiting: float = 10.0) -> dict:
    return {
        "support_policy": policy,
        "scale_id": "g20x20_d2",
        "seed": 42,
        "scarcity_level_l": 6.5,
        "input_fingerprint": fingerprint,
        "request_count": 2,
        "reservation_count": 2,
        "service_count": 2,
        "waiting_time_s": waiting,
        "rendezvous_distance_m": 5.0 if policy == "fixed" else 3.0,
        "pesticide_disabled_time_s": 4.0,
        "sprayed_volume_l": 1.0,
        "conservation_error_l": 1e-12,
        "scarcity_active": True,
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _audit_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    output_root = tmp_path / "g4"
    (output_root / "fixed").mkdir(parents=True)
    (output_root / "mobile").mkdir()
    fixed_row = _record("fixed")
    mobile_row = _record("mobile", waiting=5.0)
    summary = lambda row, policy: {
        "activation_window": [1.0, 12.0],
        "records": [row],
        "support_policy": policy,
        "lineage": {
            "validation_accessed": False,
            "sealed_test_accessed": False,
            "battery_replenishment_enabled": False,
        },
    }
    _write_json(output_root / "fixed" / "activation-summary.json", summary(fixed_row, "fixed"))
    _write_json(output_root / "mobile" / "activation-summary.json", summary(mobile_row, "mobile"))
    _write_json(output_root / "fixed" / "provenance.json", summary(fixed_row, "fixed")["lineage"])
    _write_json(output_root / "mobile" / "provenance.json", summary(mobile_row, "mobile")["lineage"])
    (output_root / "fixed" / "raw-probe.jsonl").write_text(json.dumps(fixed_row) + "\n", encoding="utf-8")
    (output_root / "mobile" / "raw-probe.jsonl").write_text(json.dumps(mobile_row) + "\n", encoding="utf-8")
    monkeypatch.setattr(g4_audit, "CANONICAL_G4_ROOT", output_root.resolve())
    run_counterfactual_probe(
        {"records": [fixed_row]},
        {"records": [mobile_row]},
        output_path=str(output_root / "counterfactual-summary.json"),
    )
    _write_json(output_root / "artifact-manifest.json", build_g4_artifact_manifest(output_root))
    return output_root, output_root / "report.json"


def test_counterfactual_probe_uses_identical_probe_inputs() -> None:
    fixed = [_record("fixed")]
    mobile = [_record("mobile", waiting=5.0)]

    result = run_counterfactual_probe(fixed, mobile)

    assert result["paired_count"] == 1
    assert result["pairs"][0]["input_fingerprint"] == "same-input"
    assert result["paired_deltas"][0]["waiting_time_s"] == -5.0

    with pytest.raises(ValueError, match="identical probe inputs"):
        run_counterfactual_probe(fixed, [_record("mobile", fingerprint="different", waiting=5.0)])

    missing = _record("mobile", waiting=5.0)
    missing.pop("input_fingerprint")
    with pytest.raises(ValueError, match="input_fingerprint"):
        run_counterfactual_probe(fixed, [missing])


def test_counterfactual_probe_rejects_invalid_count_domain() -> None:
    fixed = _record("fixed")
    fixed["service_count"] = -1

    with pytest.raises(ValueError, match="non-negative integer"):
        run_counterfactual_probe([fixed], [_record("mobile")])


def test_g4_audit_rejects_g3_smoke_artifacts_as_endpoint_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    monkeypatch.setattr(g4_audit, "CANONICAL_G4_ROOT", output_root.resolve())
    _write_json(output_root / "activation-summary.json", {"records": []})
    _write_json(
        output_root / "artifact-manifest.json",
        {"artifacts": [{"path": "../g3/training-smoke.jsonl", "sha256": "bad"}]},
    )

    with pytest.raises(ValueError, match="G3.*endpoint evidence"):
        audit_g4_mechanism(CONTRACT, output_root, output_root / "report.json")


def test_g4_audit_rejects_validation_or_sealed_access_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    monkeypatch.setattr(g4_audit, "CANONICAL_G4_ROOT", output_root.resolve())
    _write_json(
        output_root / "provenance.json",
        {"validation_accessed": True, "sealed_test_accessed": False, "battery_replenishment_enabled": False},
    )

    with pytest.raises(ValueError, match="validation"):
        audit_g4_mechanism(CONTRACT, output_root, output_root / "report.json")


def test_g4_audit_rejects_recorded_hash_drift(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    artifact = output_root / "probe.json"
    artifact.write_text("original", encoding="utf-8")
    manifest = build_g4_artifact_manifest(output_root)
    manifest["artifacts"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="hash mismatch"):
        from problem2.experiments.g4_audit import _verify_manifest

        _verify_manifest(output_root, manifest)


def test_g4_audit_happy_path_recomputes_counterfactual(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)

    report = audit_g4_mechanism(CONTRACT, output_root, report_path)

    assert report["status"] == "pass"
    assert report["hard_boundary"]["validation_accessed"] is False
    assert report_path.exists()


def test_g4_audit_rejects_tampered_counterfactual_even_with_updated_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    counterfactual_path = output_root / "counterfactual-summary.json"
    audit_g4_mechanism(CONTRACT, output_root, report_path)
    payload = json.loads(counterfactual_path.read_text(encoding="utf-8"))
    payload["paired_deltas"][0]["waiting_time_reduction_s"] = 999.0
    _write_json(counterfactual_path, payload)
    manifest = json.loads((output_root / "artifact-manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["artifacts"] if item["path"] == "counterfactual-summary.json")
    entry["sha256"] = hashlib.sha256(counterfactual_path.read_bytes()).hexdigest()
    _write_json(output_root / "artifact-manifest.json", manifest)

    with pytest.raises(ValueError, match="recomputed"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_activation_band_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    mobile_path = output_root / "mobile" / "activation-summary.json"
    mobile = json.loads(mobile_path.read_text(encoding="utf-8"))
    mobile["activation_window"] = [1.0, 11.0]
    _write_json(mobile_path, mobile)
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="activation bands"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


@pytest.mark.parametrize(
    ("field", "message"),
    [("battery_replenishment_enabled", "battery"), ("sealed_test_accessed", "sealed")],
)
def test_g4_audit_rejects_boundary_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, message: str
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    provenance_path = output_root / "fixed" / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance[field] = True
    _write_json(provenance_path, provenance)

    with pytest.raises(ValueError, match=message):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_unrecorded_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    (output_root / "new-output.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="unrecorded G4 artifact"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_malformed_jsonl_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    (output_root / "fixed" / "raw-probe.jsonl").write_text("not-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="JSONL"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_non_finite_counterfactual_metric(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    fixed_path = output_root / "fixed" / "activation-summary.json"
    fixed = json.loads(fixed_path.read_text(encoding="utf-8"))
    fixed["records"][0]["waiting_time_s"] = float("nan")
    _write_json(fixed_path, fixed)
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="finite"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_paths_outside_canonical_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="canonical G4 root"):
        audit_g4_mechanism(CONTRACT, tmp_path / "g4", tmp_path / "report.json")


def test_g4_audit_rejects_report_path_outside_canonical_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, _ = _audit_fixture(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="report_path.*canonical G4 root"):
        audit_g4_mechanism(CONTRACT, output_root, tmp_path / "outside-report.json")
