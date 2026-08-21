from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess

import pytest

import problem2.experiments.g4_audit as g4_audit
from problem2.experiments.g4_audit import audit_g4_mechanism, build_g4_artifact_manifest
from problem2.experiments.g4_counterfactual import run_counterfactual_probe

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/evidence/g4/g4_contract.yaml"


SCALES = ("g20x20_d2", "g20x30_d3", "g30x30_d3")
SEEDS = (42, 123, 2024)
LEVELS = (1.0, 6.5, 12.0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lineage() -> dict:
    return {
        "validation_accessed": False,
        "sealed_test_accessed": False,
        "battery_replenishment_enabled": False,
        "g4_contract_sha256": _sha256(CONTRACT),
        "probe_manifest_sha256": _sha256(ROOT / "docs/evidence/g4/g4_probe_manifest.yaml"),
        "g2_config_sha256": _sha256(ROOT / "configs/problem2/g2_deterministic.yaml"),
        "source_tree_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_tree_hash": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True
        ).strip(),
    }


def _record(
    policy: str,
    *,
    scale_id: str = "g20x20_d2",
    seed: int = 42,
    scarcity_level_l: float = 6.5,
    fingerprint: str = "same-input",
    waiting: float = 10.0,
) -> dict:
    return {
        "support_policy": policy,
        "scale_id": scale_id,
        "seed": seed,
        "scarcity_level_l": scarcity_level_l,
        "initial_vehicle_inventory_l": scarcity_level_l,
        "initial_uav_pesticide_l": 0.05,
        "input_fingerprint": fingerprint,
        "request_count": 2,
        "reservation_count": 2,
        "service_count": 2,
        "started_service_waiting_time_s": waiting,
        "euclidean_service_start_distance_m": 5.0 if policy == "fixed_support_probe" else 3.0,
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
    lineage = _lineage()
    fixed_rows = [
        _record(
            "fixed_support_probe",
            scale_id=scale_id,
            seed=seed,
            scarcity_level_l=level,
            fingerprint=f"{scale_id}-{seed}-{level}",
        )
        for scale_id in SCALES
        for seed in SEEDS
        for level in LEVELS
    ]
    mobile_rows = [
        _record(
            "mobile_support_probe",
            scale_id=row["scale_id"],
            seed=row["seed"],
            scarcity_level_l=row["scarcity_level_l"],
            fingerprint=row["input_fingerprint"],
            waiting=5.0,
        )
        for row in fixed_rows
    ]
    for row in [*fixed_rows, *mobile_rows]:
        row["lineage"] = lineage

    def summary(rows: list[dict], policy: str) -> dict:
        return {
        "activation_window": [1.0, 12.0],
        "scarcity_active": True,
        "records": rows,
        "support_policy": policy,
        "lineage": lineage,
        "request_count": sum(row["request_count"] for row in rows),
        "reservation_count": sum(row["reservation_count"] for row in rows),
        "service_count": sum(row["service_count"] for row in rows),
        "started_service_waiting_time_s": sum(row["started_service_waiting_time_s"] for row in rows),
        "euclidean_service_start_distance_m": sum(row["euclidean_service_start_distance_m"] for row in rows),
        "pesticide_disabled_time_s": sum(row["pesticide_disabled_time_s"] for row in rows),
        "sprayed_volume_l": sum(row["sprayed_volume_l"] for row in rows),
        "conservation_error_l": max(row["conservation_error_l"] for row in rows),
    }
    fixed = summary(fixed_rows, "fixed_support_probe")
    mobile = summary(mobile_rows, "mobile_support_probe")
    _write_json(output_root / "fixed" / "activation-summary.json", fixed)
    _write_json(output_root / "mobile" / "activation-summary.json", mobile)
    _write_json(output_root / "fixed" / "provenance.json", lineage)
    _write_json(output_root / "mobile" / "provenance.json", lineage)
    (output_root / "fixed" / "raw-probe.jsonl").write_text(
        "\n".join(json.dumps(row) for row in fixed_rows) + "\n", encoding="utf-8"
    )
    (output_root / "mobile" / "raw-probe.jsonl").write_text(
        "\n".join(json.dumps(row) for row in mobile_rows) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(g4_audit, "CANONICAL_G4_ROOT", output_root.resolve())
    run_counterfactual_probe(
        fixed,
        mobile,
        output_path=str(output_root / "counterfactual-summary.json"),
    )
    _write_json(
        output_root / "probe-matrix-summary.json",
        {
            "activation_window": [1.0, 12.0],
            "arms": [fixed, mobile],
            "paired_inputs": [
                {"fixed": fixed_row, "mobile": mobile_row}
                for fixed_row, mobile_row in zip(fixed_rows, mobile_rows)
            ],
            "lineage": lineage,
        },
    )
    _write_json(
        output_root / "activation-summary.json",
        {
            "schema_version": "g4-activation-index.v1",
            "status": "descriptive",
            "activation_window": [1.0, 12.0],
            "arms": {
                "fixed_support_probe": "fixed/activation-summary.json",
                "mobile_support_probe": "mobile/activation-summary.json",
            },
            "paired_counterfactual": "counterfactual-summary.json",
            **lineage,
        },
    )
    _write_json(output_root / "provenance.json", lineage)
    _write_json(output_root / "artifact-manifest.json", build_g4_artifact_manifest(output_root))
    return output_root, output_root / "report.json"


def test_counterfactual_probe_uses_identical_probe_inputs() -> None:
    fixed = [_record("fixed_support_probe")]
    mobile = [_record("mobile_support_probe", waiting=5.0)]

    result = run_counterfactual_probe(fixed, mobile)

    assert result["paired_count"] == 1
    assert result["pairs"][0]["input_fingerprint"] == "same-input"
    assert result["paired_deltas"][0]["started_service_waiting_time_s"] == -5.0

    with pytest.raises(ValueError, match="identical probe inputs"):
        run_counterfactual_probe(fixed, [_record("mobile_support_probe", fingerprint="different", waiting=5.0)])

    missing = _record("mobile_support_probe", waiting=5.0)
    missing.pop("input_fingerprint")
    with pytest.raises(ValueError, match="input_fingerprint"):
        run_counterfactual_probe(fixed, [missing])


def test_counterfactual_probe_rejects_invalid_count_domain() -> None:
    fixed = _record("fixed_support_probe")
    fixed["service_count"] = -1

    with pytest.raises(ValueError, match="non-negative integer"):
        run_counterfactual_probe([fixed], [_record("mobile_support_probe")])


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


def test_g4_artifact_manifest_excludes_self_generated_audit_report(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    _write_json(output_root / "probe.json", {"probe": "evidence"})
    _write_json(output_root / "g4-mechanism-audit.json", {"status": "pass"})

    manifest = build_g4_artifact_manifest(output_root)

    assert [entry["path"] for entry in manifest["artifacts"]] == ["probe.json"]


def test_g4_artifact_manifest_registers_nested_audit_named_evidence(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    nested_report = output_root / "fixed" / "g4-mechanism-audit.json"
    nested_report.parent.mkdir(parents=True)
    _write_json(output_root / "g4-mechanism-audit.json", {"status": "pass"})
    _write_json(nested_report, {"probe": "evidence"})

    manifest = build_g4_artifact_manifest(output_root)

    assert [entry["path"] for entry in manifest["artifacts"]] == ["fixed/g4-mechanism-audit.json"]


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
    payload["paired_deltas"][0]["started_service_waiting_time_reduction_s"] = 999.0
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

    with pytest.raises(ValueError, match="activation.*window"):
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


def test_g4_audit_rejects_blank_only_jsonl_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    (output_root / "fixed" / "raw-probe.jsonl").write_text("\n  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="JSONL evidence is empty"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_unsupported_textual_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    (output_root / "notes.txt").write_text('"validation_accessed": true\n', encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported G4 artifact file type"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_non_finite_counterfactual_metric(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    fixed_path = output_root / "fixed" / "activation-summary.json"
    fixed = json.loads(fixed_path.read_text(encoding="utf-8"))
    fixed["records"][0]["started_service_waiting_time_s"] = float("nan")
    _write_json(fixed_path, fixed)
    raw_path = output_root / "fixed" / "raw-probe.jsonl"
    raw_lines = raw_path.read_text(encoding="utf-8").splitlines()
    raw = json.loads(raw_lines[0])
    raw["started_service_waiting_time_s"] = float("nan")
    raw_lines[0] = json.dumps(raw)
    raw_path.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="finite"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_raw_summary_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    raw_path = output_root / "fixed" / "raw-probe.jsonl"
    raw_lines = raw_path.read_text(encoding="utf-8").splitlines()
    raw = json.loads(raw_lines[0])
    raw["service_count"] = 99
    raw_lines[0] = json.dumps(raw)
    raw_path.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="raw.*summary"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_missing_frozen_raw_matrix_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    raw_path = output_root / "mobile" / "raw-probe.jsonl"
    raw_path.write_text("\n".join(raw_path.read_text(encoding="utf-8").splitlines()[:-1]) + "\n", encoding="utf-8")
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="frozen raw matrix"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_extra_frozen_raw_matrix_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    raw_path = output_root / "mobile" / "raw-probe.jsonl"
    raw_path.write_text(
        raw_path.read_text(encoding="utf-8")
        + json.dumps(
            {
                **_record("mobile_support_probe", scale_id="g99x99_d9", fingerprint="extra"),
                "lineage": _lineage(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="frozen raw matrix"):
        audit_g4_mechanism(CONTRACT, output_root, report_path)


def test_g4_audit_rejects_duplicate_manifest_paths(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    artifact = output_root / "probe.json"
    _write_json(artifact, {"probe": "evidence"})
    manifest = build_g4_artifact_manifest(output_root)
    manifest["artifacts"].append(dict(manifest["artifacts"][0]))

    with pytest.raises(ValueError, match="duplicate"):
        from problem2.experiments.g4_audit import _verify_manifest

        _verify_manifest(output_root, manifest)


def test_g4_audit_rejects_case_variant_manifest_path_alias(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    artifact = output_root / "probe.json"
    _write_json(artifact, {"probe": "evidence"})
    manifest = build_g4_artifact_manifest(output_root)
    manifest["artifacts"].append({**manifest["artifacts"][0], "path": "PROBE.JSON"})

    with pytest.raises(ValueError, match="duplicate"):
        from problem2.experiments.g4_audit import _verify_manifest

        _verify_manifest(output_root, manifest)


def test_g4_audit_rejects_manifest_byte_drift(tmp_path: Path) -> None:
    output_root = tmp_path / "g4"
    output_root.mkdir()
    artifact = output_root / "probe.json"
    _write_json(artifact, {"probe": "evidence"})
    manifest = build_g4_artifact_manifest(output_root)
    manifest["artifacts"][0]["bytes"] += 1

    with pytest.raises(ValueError, match="byte mismatch"):
        from problem2.experiments.g4_audit import _verify_manifest

        _verify_manifest(output_root, manifest)


def test_g4_audit_rejects_unknown_generator_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root, report_path = _audit_fixture(tmp_path, monkeypatch)
    summary_path = output_root / "fixed" / "activation-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["lineage"]["source_tree_commit"] = "unknown"
    _write_json(summary_path, summary)
    (output_root / "artifact-manifest.json").unlink()

    with pytest.raises(ValueError, match="provenance"):
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
