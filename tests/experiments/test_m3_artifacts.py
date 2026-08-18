from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from problem2.artifacts.m3_pilot import build_m3_pilot_artifacts
from problem2.experiments.job_identity import GitProvenance
from problem2.experiments.m3_audit import audit_m3_pilot
from problem2.experiments.m3_pilot import build_m3_manifest, write_m3_manifest
from problem2.experiments.orchestrator import Chapter45Orchestrator
from tests.m3_fixtures import materialize_complete_m3_evidence


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"
PROTOCOL = CONFIG_DIR / "experiments" / "chapter4_5.yaml"


def _canonical_hash(payload: dict[str, object], *excluded: str) -> str:
    value = {key: item for key, item in payload.items() if key not in set(excluded)}
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def _write_jsonl_object(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, object]]:
    run_root = tmp_path / "runs"
    orchestrator = Chapter45Orchestrator(CONFIG_DIR, run_root)
    orchestrator.git_provenance = GitProvenance(
        orchestrator.git_commit,
        "a" * 64,
        False,
    )
    resource = tmp_path / "resource.json"
    _write_json(resource, {
        "activated": True,
        "diagnosis": "resource_service_chain_activated",
        "config_hash": orchestrator.config_hash,
        "git_commit": orchestrator.git_provenance.commit,
        "source_tree_hash": orchestrator.git_provenance.source_tree_hash,
        "simulation_profile_sha256": "b" * 64,
        "record_count": 45,
        "provisional": True,
    })
    manifest = build_m3_manifest(
        orchestrator,
        resource_report_path=resource,
        created_at="2026-08-18T00:00:00+00:00",
    )
    manifest_path = tmp_path / "m3.json"
    write_m3_manifest(manifest_path, manifest)
    materialize_complete_m3_evidence(manifest, run_root)
    readiness = audit_m3_pilot(manifest_path, output_root=run_root)
    assert readiness["m3_ready"] is True
    readiness_path = tmp_path / "readiness.json"
    _write_json(readiness_path, readiness)
    return manifest_path, readiness_path, run_root, manifest


def _rewrite_readiness(path: Path, mutate) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload["report_semantic_sha256"] = _canonical_hash(payload, "report_semantic_sha256")
    _write_json(path, payload)
    return payload


def test_m3_artifact_builder_emits_exact_traceable_pilot_package(tmp_path: Path) -> None:
    manifest_path, readiness_path, _, _ = _fixture(tmp_path)

    bundle = build_m3_pilot_artifacts(
        manifest_path,
        readiness_path,
        tmp_path / "artifacts",
        config_dir=CONFIG_DIR,
        protocol_path=PROTOCOL,
    )

    assert bundle.paths["validated_csv"].is_file()
    assert bundle.paths["locked_summary_json"].is_file()
    assert bundle.paths["main_comparison_svg"].is_file()
    assert bundle.paths["main_comparison_pdf"].is_file()
    assert bundle.paths["main_comparison_png"].is_file()
    assert bundle.paths["main_comparison_table_tsv"].is_file()
    summary = json.loads(bundle.paths["locked_summary_json"].read_text(encoding="utf-8"))
    assert summary["maturity"] == "m3_pilot_validation_controlled_simulation"
    assert summary["record_count"] == 100
    assert summary["identity"]["split"] == ["validation"]
    assert summary["uncertainty"]["confirmatory"] is False
    artifact_manifest = json.loads(bundle.paths["manifest_json"].read_text(encoding="utf-8"))
    assert len(artifact_manifest["raw_evaluations"]) == 100
    assert artifact_manifest["outputs"]["locked_summary_json"]["sha256"] == hashlib.sha256(
        bundle.paths["locked_summary_json"].read_bytes()
    ).hexdigest()


def test_m3_artifact_builder_rejects_false_readiness(tmp_path: Path) -> None:
    manifest_path, readiness_path, _, _ = _fixture(tmp_path)
    _rewrite_readiness(readiness_path, lambda payload: payload.update({"m3_ready": False}))

    with pytest.raises(ValueError, match="m3_ready"):
        build_m3_pilot_artifacts(
            manifest_path, readiness_path, tmp_path / "artifacts",
            config_dir=CONFIG_DIR, protocol_path=PROTOCOL,
        )
    assert not (tmp_path / "artifacts").exists()


def test_m3_artifact_builder_rejects_tampered_readiness_hash(tmp_path: Path) -> None:
    manifest_path, readiness_path, _, _ = _fixture(tmp_path)
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["highest_maturity"] = "M2"
    _write_json(readiness_path, readiness)

    with pytest.raises(ValueError, match="readiness.*SHA-256"):
        build_m3_pilot_artifacts(
            manifest_path, readiness_path, tmp_path / "artifacts",
            config_dir=CONFIG_DIR, protocol_path=PROTOCOL,
        )


def test_m3_artifact_builder_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    manifest_path, readiness_path, _, _ = _fixture(tmp_path)
    _rewrite_readiness(
        readiness_path,
        lambda payload: payload.update({"manifest_semantic_sha256": "c" * 64}),
    )
    with pytest.raises(ValueError, match="manifest.*SHA-256"):
        build_m3_pilot_artifacts(
            manifest_path, readiness_path, tmp_path / "artifacts",
            config_dir=CONFIG_DIR, protocol_path=PROTOCOL,
        )


@pytest.mark.parametrize("case", ["missing", "mixed_checkpoint", "sealed_test"])
def test_m3_artifact_builder_revalidates_every_raw_input(
    tmp_path: Path,
    case: str,
) -> None:
    manifest_path, readiness_path, run_root, manifest = _fixture(tmp_path)
    raw = run_root / str(manifest["evaluations"][0]["raw_path"])
    if case == "missing":
        raw.unlink()
        message = "missing evaluation"
    else:
        row = json.loads(raw.read_text(encoding="utf-8"))
        if case == "mixed_checkpoint":
            row["checkpoint_sha256"] = "d" * 64
            message = "checkpoint"
        else:
            row["split"] = "sealed_test"
            message = "sealed"
        _write_jsonl_object(raw, row)

    with pytest.raises(ValueError, match=message):
        build_m3_pilot_artifacts(
            manifest_path, readiness_path, tmp_path / "artifacts",
            config_dir=CONFIG_DIR, protocol_path=PROTOCOL,
        )


def test_m3_artifact_builder_rejects_extra_manifest_evaluation(tmp_path: Path) -> None:
    manifest_path, readiness_path, _, manifest = _fixture(tmp_path)
    manifest["evaluations"].append(dict(manifest["evaluations"][0]))
    manifest["semantic_sha256"] = _canonical_hash(
        manifest, "created_at", "semantic_sha256",
    )
    _write_json(manifest_path, manifest)
    _rewrite_readiness(
        readiness_path,
        lambda payload: payload.update({
            "manifest_semantic_sha256": manifest["semantic_sha256"],
        }),
    )

    with pytest.raises(ValueError, match="100 evaluations"):
        build_m3_pilot_artifacts(
            manifest_path, readiness_path, tmp_path / "artifacts",
            config_dir=CONFIG_DIR, protocol_path=PROTOCOL,
        )
