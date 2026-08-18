"""Manifest-bound evidence package for the validation-only M3 pilot."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.m3_pilot import M3PilotProfile, load_m3_manifest
from problem2.experiments.specification import load_experiment_spec, protocol_identity

from .chapter45 import METRICS, METRIC_DEFINITIONS
from .figures import build_chapter45_figures
from .summarize import hierarchical_paired_summary, summarize_metric_groups
from .tables import build_chapter45_tables
from .validate_logs import validate_episode_records


@dataclass(frozen=True)
class M3ArtifactBundle:
    paths: dict[str, Path]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _relative_path(root: Path, value: object) -> Path:
    relative = Path(str(value))
    if relative.is_absolute():
        raise ValueError(f"manifest evaluation path must be relative: {relative}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"manifest evaluation path escapes output root: {relative}") from exc
    return resolved


def _validate_readiness(
    manifest_path: Path,
    manifest: Mapping[str, object],
    readiness_path: Path,
) -> tuple[dict[str, object], Path]:
    from problem2.experiments.m3_audit import audit_m3_pilot

    readiness = _read_object(readiness_path, "M3 readiness report")
    observed_hash = readiness.get("report_semantic_sha256")
    semantic = {
        key: value for key, value in readiness.items() if key != "report_semantic_sha256"
    }
    if observed_hash != _canonical_sha256(semantic):
        raise ValueError("M3 readiness report semantic SHA-256 mismatch")
    if readiness.get("m3_ready") is not True:
        raise ValueError("M3 artifact build requires m3_ready=true")
    if readiness.get("highest_maturity") != "M3":
        raise ValueError("M3 readiness report does not declare maturity M3")
    if readiness.get("manifest_semantic_sha256") != manifest.get("semantic_sha256"):
        raise ValueError("M3 readiness manifest SHA-256 mismatch")
    if Path(str(readiness.get("manifest", ""))).resolve() != manifest_path:
        raise ValueError("M3 readiness report references a different manifest path")
    output_root = Path(str(readiness.get("output_root", ""))).resolve()
    fresh = audit_m3_pilot(manifest_path, output_root=output_root)
    if fresh.get("m3_ready") is not True:
        failed = [
            f"{check['name']}: {check['detail']}"
            for check in fresh.get("checks", [])
            if check.get("passed") is not True
        ]
        raise ValueError("M3 evidence is no longer audit-ready: " + "; ".join(failed))
    if fresh.get("report_semantic_sha256") != observed_hash:
        raise ValueError("M3 readiness report no longer matches current evidence")
    return readiness, output_root


def _validate_manifest_shape(manifest: Mapping[str, object]) -> None:
    profile = manifest.get("profile")
    jobs = manifest.get("jobs")
    evaluations = manifest.get("evaluations")
    fixed = M3PilotProfile()
    if not isinstance(profile, Mapping):
        raise ValueError("M3 manifest profile is malformed")
    if (
        profile.get("family") != fixed.family
        or profile.get("execution_profile") != fixed.execution_profile
        or profile.get("scales") != list(fixed.scales)
        or profile.get("methods") != list(fixed.methods)
        or profile.get("training_seeds") != list(fixed.training_seeds)
        or profile.get("split") != fixed.split
    ):
        raise ValueError("M3 manifest profile differs from the fixed pilot")
    if not isinstance(jobs, list) or len(jobs) != 50:
        raise ValueError("M3 artifact build requires exactly 50 jobs")
    if not isinstance(evaluations, list) or len(evaluations) != 100:
        raise ValueError("M3 artifact build requires exactly 100 evaluations")
    if manifest.get("counts") != {"jobs": 50, "evaluations": 100}:
        raise ValueError("M3 manifest count declaration is inconsistent")


def _load_rows(
    manifest: Mapping[str, object],
    run_root: Path,
) -> tuple[list[dict[str, Any]], list[Path]]:
    evaluations = manifest["evaluations"]
    jobs = {str(row["job_id"]): row for row in manifest["jobs"]}
    rows: list[dict[str, Any]] = []
    paths: list[Path] = []
    seen_paths: set[Path] = set()
    for expected in evaluations:
        path = _relative_path(run_root, expected.get("raw_path"))
        if path in seen_paths:
            raise ValueError(f"duplicate manifest evaluation path: {path}")
        seen_paths.add(path)
        if not path.is_file():
            raise ValueError(f"missing evaluation input: {path}")
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) != 1 or not lines[0].strip():
            raise ValueError(f"evaluation input must contain exactly one row: {path}")
        try:
            value = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid evaluation JSON: {path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"evaluation row must be an object: {path}")
        job = jobs.get(str(expected.get("job_id", "")))
        if job is None:
            raise ValueError("evaluation references a job absent from the M3 manifest")
        for field, expected_value in (
            ("job_id", expected.get("job_id")),
            ("run_id", expected.get("run_id")),
            ("scenario_id", expected.get("scenario_id")),
            ("method", job.get("method")),
            ("scale", job.get("scale")),
            ("training_seed", job.get("training_seed")),
            ("family", job.get("family")),
            ("condition_id", job.get("condition_id")),
            ("config_hash", job.get("config_hash")),
            ("git_commit", job.get("git_commit")),
            ("protocol_hash", job.get("protocol_hash")),
            ("source_tree_hash", job.get("source_tree_hash")),
            ("checkpoint_step", job.get("target_updates")),
            ("split", "validation"),
            ("execution_profile", "simulation"),
        ):
            if value.get(field) != expected_value:
                label = "sealed-test" if field == "split" else field
                raise ValueError(f"evaluation {label} identity mismatch: {path}")
        if value.get("checkpoint_sha256") is None:
            raise ValueError(f"evaluation checkpoint provenance is missing: {path}")
        rows.append(value)
        paths.append(path)
    return validate_episode_records(rows, strict=True), paths


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _write_artifact_manifest(
    path: Path,
    *,
    manifest_path: Path,
    readiness_path: Path,
    resource_path: Path,
    protocol_path: Path,
    raw_paths: list[Path],
    outputs: Mapping[str, Path],
    rows: list[Mapping[str, object]],
) -> None:
    payload: dict[str, object] = {
        "schema_version": 1,
        "maturity": "m3_pilot_validation_controlled_simulation",
        "labels": ["pilot", "validation", "controlled_simulation"],
        "m3_manifest": {"path": str(manifest_path), "sha256": _sha256(manifest_path)},
        "readiness": {"path": str(readiness_path), "sha256": _sha256(readiness_path)},
        "resource_activation": {"path": str(resource_path), "sha256": _sha256(resource_path)},
        "protocol": {"path": str(protocol_path), "sha256": _sha256(protocol_path)},
        "raw_evaluations": [
            {"path": str(value), "sha256": _sha256(value)} for value in raw_paths
        ],
        "outputs": {
            name: {"path": str(value), "sha256": _sha256(value)}
            for name, value in sorted(outputs.items())
        },
        "identity": {
            "config_hash": sorted({str(row["config_hash"]) for row in rows}),
            "protocol_hash": sorted({str(row["protocol_hash"]) for row in rows}),
            "git_commit": sorted({str(row["git_commit"]) for row in rows}),
            "source_tree_hash": sorted({str(row["source_tree_hash"]) for row in rows}),
            "checkpoint_sha256": sorted({str(row["checkpoint_sha256"]) for row in rows}),
            "method": sorted({str(row["method"]) for row in rows}),
            "scale": sorted({str(row["scale"]) for row in rows}),
            "split": sorted({str(row["split"]) for row in rows}),
        },
        "script_sha256": _sha256(Path(__file__).resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "self": {
            "path": str(path),
            "sha256": None,
            "sha256_note": "self-hash omitted because serialization changes its own bytes",
        },
    }
    _write_json(path, payload)


def build_m3_pilot_artifacts(
    manifest_path: str | Path,
    readiness_path: str | Path,
    output_root: str | Path,
    *,
    config_dir: str | Path,
    protocol_path: str | Path,
) -> M3ArtifactBundle:
    """Build validation-only pilot artifacts after re-auditing every input."""

    manifest_source = Path(manifest_path).resolve()
    readiness_source = Path(readiness_path).resolve()
    protocol_source = Path(protocol_path).resolve()
    manifest = load_m3_manifest(manifest_source)
    _validate_manifest_shape(manifest)
    readiness, run_root = _validate_readiness(
        manifest_source, manifest, readiness_source,
    )
    config = load_config_bundle(Path(config_dir).resolve())
    spec = load_experiment_spec(protocol_source, config)
    identity = manifest.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("M3 manifest identity is malformed")
    if identity.get("config_hash") != config_identity(config):
        raise ValueError("M3 manifest does not match the supplied configuration")
    if identity.get("protocol_hash") != protocol_identity(protocol_source):
        raise ValueError("M3 manifest does not match the supplied protocol")
    if tuple(spec.main_methods) != M3PilotProfile().methods:
        raise ValueError("supplied protocol methods do not match the M3 profile")

    rows, raw_paths = _load_rows(manifest, run_root)
    prepared = [{**row, "analysis_group": str(row["method"])} for row in rows]
    draws = int(spec.statistics["bootstrap_draws"])
    confidence_level = float(spec.statistics["confidence_level"])
    margin_raw = spec.statistics["practical_equivalence_margin"]
    margin = None if margin_raw is None else float(margin_raw)
    summary_rows = summarize_metric_groups(
        prepared,
        group_fields=("family", "analysis_group", "method", "scale"),
        metrics=METRICS + (
            "vehicle_inventory_initial_l", "vehicle_inventory_final_l",
        ),
        draws=draws,
        seed=0,
        confidence_level=confidence_level,
    )
    paired_reduction = hierarchical_paired_summary(
        prepared,
        reference="sr_mappo_mobile",
        metric="reduction_rate",
        draws=draws,
        seed=0,
        confidence_level=confidence_level,
        practical_equivalence_margin=margin,
        confirmatory=False,
        group_field="method",
    )
    paired_success = hierarchical_paired_summary(
        prepared,
        reference="sr_mappo_mobile",
        metric="success",
        draws=draws,
        seed=0,
        confidence_level=confidence_level,
        practical_equivalence_margin=margin,
        confirmatory=False,
        group_field="method",
    )
    summary_identity = {
        "config_hash": sorted({str(row["config_hash"]) for row in rows}),
        "protocol_hash": sorted({str(row["protocol_hash"]) for row in rows}),
        "git_commit": sorted({str(row["git_commit"]) for row in rows}),
        "split": sorted({str(row["split"]) for row in rows}),
        "source_tree_hash": sorted({str(row["source_tree_hash"]) for row in rows}),
        "checkpoint_sha256": sorted({str(row["checkpoint_sha256"]) for row in rows}),
    }
    uncertainty = {
        "pairing_unit": spec.statistics["pairing_unit"],
        "bootstrap_draws": draws,
        "confidence_level": confidence_level,
        "multiplicity": spec.statistics["multiplicity"],
        "practical_equivalence_margin": margin,
        "practical_equivalence_basis": spec.statistics["practical_equivalence_basis"],
        "confirmatory": False,
    }
    locked_summary: dict[str, object] = {
        "schema_version": 1,
        "locked": True,
        "maturity": "m3_pilot_validation_controlled_simulation",
        "record_count": len(rows),
        "identity": summary_identity,
        "uncertainty": uncertainty,
        "metric_definitions": METRIC_DEFINITIONS,
        "families": {"main_comparison": summary_rows},
        "paired": {
            "main_reduction": paired_reduction,
            "main_success": paired_success,
        },
    }

    root = Path(output_root).resolve()
    validated_csv = root / "m3-validation-long.csv"
    locked_summary_path = root / "locked_summary.json"
    _write_csv(validated_csv, rows)
    _write_json(locked_summary_path, locked_summary)
    consumed = json.loads(locked_summary_path.read_text(encoding="utf-8"))
    outputs: dict[str, Path] = {
        "validated_csv": validated_csv,
        "locked_summary_json": locked_summary_path,
    }
    outputs.update(
        build_chapter45_figures(consumed, root / "figures", allow_partial=True)
    )
    outputs.update(
        build_chapter45_tables(consumed, root / "tables", allow_partial=True)
    )
    resource_path = Path(str(manifest["resource_activation"]["path"])).resolve()
    artifact_manifest = root / "m3-artifact-manifest.json"
    _write_artifact_manifest(
        artifact_manifest,
        manifest_path=manifest_source,
        readiness_path=readiness_source,
        resource_path=resource_path,
        protocol_path=protocol_source,
        raw_paths=raw_paths,
        outputs=outputs,
        rows=rows,
    )
    outputs["manifest_json"] = artifact_manifest
    return M3ArtifactBundle(paths=outputs)


__all__ = ["M3ArtifactBundle", "build_m3_pilot_artifacts"]
