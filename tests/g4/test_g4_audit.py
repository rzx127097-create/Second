from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_counterfactual_probe_uses_identical_probe_inputs() -> None:
    fixed = [_record("fixed")]
    mobile = [_record("mobile", waiting=5.0)]

    result = run_counterfactual_probe(fixed, mobile)

    assert result["paired_count"] == 1
    assert result["pairs"][0]["input_fingerprint"] == "same-input"
    assert result["paired_deltas"][0]["waiting_time_s"] == -5.0

    with pytest.raises(ValueError, match="identical probe inputs"):
        run_counterfactual_probe(fixed, [_record("mobile", fingerprint="different", waiting=5.0)])


def test_g4_audit_rejects_g3_smoke_artifacts_as_endpoint_evidence(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    _write_json(output_root / "activation-summary.json", {"records": []})
    _write_json(
        output_root / "artifact-manifest.json",
        {"artifacts": [{"path": "../g3/training-smoke.jsonl", "sha256": "bad"}]},
    )

    with pytest.raises(ValueError, match="G3.*endpoint evidence"):
        audit_g4_mechanism(CONTRACT, output_root, tmp_path / "report.json")


def test_g4_audit_rejects_validation_or_sealed_access_flags(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    _write_json(
        output_root / "provenance.json",
        {"validation_accessed": True, "sealed_test_accessed": False, "battery_replenishment_enabled": False},
    )

    with pytest.raises(ValueError, match="validation"):
        audit_g4_mechanism(CONTRACT, output_root, tmp_path / "report.json")


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
