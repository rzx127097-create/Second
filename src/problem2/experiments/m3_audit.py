"""Read-only readiness audit for the canonical controlled-simulation M3 pilot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from problem2.artifacts.validate_logs import validate_episode_records
from problem2.config import config_identity, load_config_bundle

from .m3_pilot import M3PilotProfile, load_m3_manifest
from .recovery import load_job_record
from .runner import JobRecord
from .specification import load_experiment_spec, protocol_identity


M3_REQUIRED_METRICS = (
    "reduction_rate",
    "success",
    "transferred_l",
    "request_count",
    "request_completion_rate",
    "requested_l",
    "request_wait_mean_s",
    "request_wait_p90_s",
    "wait_s",
    "pesticide_disabled_s",
    "effective_spray_s",
    "service_s",
    "rendezvous_road_distance_m",
    "uav_rendezvous_distance_m",
    "vehicle_distance_m",
    "vehicle_idle_s",
    "vehicle_inventory_initial_l",
    "vehicle_inventory_final_l",
    "vehicle_inventory_utilization",
    "decision_time_mean_ms",
)


@dataclass(frozen=True)
class AuditCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(name: str, issues: Sequence[str]) -> AuditCheck:
    return AuditCheck(name, not issues, "ok" if not issues else "; ".join(issues))


def _mapping_rows(value: object, name: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError(f"manifest {name} must be a list")
    rows: list[dict[str, object]] = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(f"manifest {name}[{index}] must be an object")
        rows.append(dict(row))
    return rows


def _relative_path(root: Path, value: object) -> Path:
    relative = Path(str(value))
    if relative.is_absolute():
        raise ValueError(f"manifest evidence path must be relative: {relative}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"manifest evidence path escapes output root: {relative}") from exc
    return resolved


def _canonical_context(
    manifest: Mapping[str, object],
) -> tuple[Any | None, Any | None, list[str]]:
    """Load the config/protocol named by the manifest for independent auditing."""

    issues: list[str] = []
    identity = manifest.get("identity")
    if not isinstance(identity, Mapping):
        return None, None, ["manifest identity is missing or malformed"]
    try:
        config_dir = Path(str(identity["config_dir"])).resolve()
        config = load_config_bundle(config_dir)
        if config_identity(config) != identity.get("config_hash"):
            issues.append("manifest config hash does not match its config directory")
        protocol_path = Path(str(identity["protocol_path"])).resolve()
        if protocol_identity(protocol_path) != identity.get("protocol_hash"):
            issues.append("manifest protocol hash does not match its protocol file")
        spec = load_experiment_spec(protocol_path, config)
        return config, spec, issues
    except (KeyError, OSError, TypeError, ValueError) as exc:
        issues.append(f"canonical config/protocol unavailable: {exc}")
        return None, None, issues


def _manifest_shape(
    manifest: Mapping[str, object],
    jobs: Sequence[Mapping[str, object]],
    evaluations: Sequence[Mapping[str, object]],
) -> AuditCheck:
    issues: list[str] = []
    profile = manifest.get("profile")
    expected = M3PilotProfile()
    if not isinstance(profile, Mapping):
        return _check("manifest_shape", ["profile is missing or malformed"])
    expected_profile = {
        "family": expected.family,
        "execution_profile": expected.execution_profile,
        "scales": list(expected.scales),
        "methods": list(expected.methods),
        "training_seeds": list(expected.training_seeds),
        "split": expected.split,
    }
    for field, value in expected_profile.items():
        if profile.get(field) != value:
            issues.append(f"profile {field} mismatch")
    config, spec, context_issues = _canonical_context(manifest)
    issues.extend(context_issues)
    expected_updates: int | None = None
    expected_horizon: int | None = None
    expected_rule: str | None = None
    expected_scenarios: dict[str, list[str]] = {}
    if config is not None and spec is not None:
        try:
            expected_updates = int(config.algorithm["total_updates"])
            expected_horizon = int(config.algorithm["rollout_horizon"])
            expected_rule = str(spec.execution["checkpoint_selection_rule"])
            declared = tuple(
                str(value) for value in config.experiments["validation_scenarios"]
            )
            for scale in expected.scales:
                expected_scenarios[scale] = [
                    scenario_id
                    for scenario_id in declared
                    if str(config.scenarios[scenario_id]["scale"]) == scale
                    and str(config.scenarios[scenario_id]["split"]) == "validation"
                ]
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"canonical M3 contract is malformed: {exc}")
    if expected_updates is not None:
        if profile.get("target_updates") != expected_updates:
            issues.append("profile target_updates is not the configured full budget")
    if expected_rule is not None:
        if profile.get("checkpoint_selection_rule") != expected_rule:
            issues.append("profile checkpoint selection rule mismatch")
    if expected_scenarios and profile.get("scenarios_by_scale") != expected_scenarios:
        issues.append("profile validation scenario map does not match configuration")
    if len(jobs) != 50:
        issues.append(f"expected 50 jobs, found {len(jobs)}")
    if len(evaluations) != 100:
        issues.append(f"expected 100 evaluations, found {len(evaluations)}")
    identities = {
        (row.get("scale"), row.get("method"), row.get("training_seed"))
        for row in jobs
    }
    expected_identities = {
        (scale, method, seed)
        for scale in expected.scales
        for method in expected.methods
        for seed in expected.training_seeds
    }
    if identities != expected_identities or len(identities) != len(jobs):
        issues.append("job cross-product is incomplete or duplicated")
    job_ids = [str(row.get("job_id", "")) for row in jobs]
    if any(not value for value in job_ids) or len(set(job_ids)) != len(job_ids):
        issues.append("job IDs are empty or duplicated")
    evaluation_keys = [
        (str(row.get("job_id", "")), str(row.get("scenario_id", "")))
        for row in evaluations
    ]
    if any(not all(key) for key in evaluation_keys) or len(set(evaluation_keys)) != len(evaluation_keys):
        issues.append("evaluation keys are empty or duplicated")
    if set(key[0] for key in evaluation_keys) != set(job_ids):
        issues.append("evaluation job set does not match the manifest job set")
    if any(sum(1 for key in evaluation_keys if key[0] == job_id) != 2 for job_id in job_ids):
        issues.append("each job must have exactly two validation evaluations")
    if expected_updates is not None or expected_horizon is not None:
        for row in jobs:
            if row.get("family") != expected.family:
                issues.append(f"job {row.get('job_id')}: family is not main_comparison")
            if row.get("execution_profile") != expected.execution_profile:
                issues.append(f"job {row.get('job_id')}: execution profile is not simulation")
            if expected_updates is not None and row.get("target_updates") != expected_updates:
                issues.append(f"job {row.get('job_id')}: target_updates is not full budget")
            if expected_horizon is not None and row.get("rollout_horizon") != expected_horizon:
                issues.append(f"job {row.get('job_id')}: rollout horizon mismatch")
            if row.get("condition_id") == "direct":
                issues.append(f"job {row.get('job_id')}: direct condition is not allowed")
            if row.get("scenario_split") != "train":
                issues.append(f"job {row.get('job_id')}: scenario split is not train")
            if row.get("git_dirty") is not False:
                issues.append(f"job {row.get('job_id')}: source is dirty")
    if expected_scenarios:
        scenario_sets = {scale: set(values) for scale, values in expected_scenarios.items()}
        for row in evaluations:
            scale = str(row.get("scale", ""))
            scenario_id = str(row.get("scenario_id", ""))
            if row.get("split") != expected.split:
                issues.append(f"evaluation {row.get('job_id')}:{scenario_id}: split is not validation")
            if scenario_id not in scenario_sets.get(scale, set()):
                issues.append(f"evaluation {row.get('job_id')}:{scenario_id}: scenario is not registered validation")
    counts = manifest.get("counts")
    if counts != {"jobs": 50, "evaluations": 100}:
        issues.append("manifest counts do not match the canonical M3 shape")
    return _check("manifest_shape", issues)


def _resource_activation(manifest: Mapping[str, object]) -> AuditCheck:
    issues: list[str] = []
    resource = manifest.get("resource_activation")
    identity = manifest.get("identity")
    if not isinstance(resource, Mapping) or not isinstance(identity, Mapping):
        return _check("resource_activation", ["resource or manifest identity is malformed"])
    path = Path(str(resource.get("path", "")))
    if not path.is_file():
        return _check("resource_activation", [f"resource report is missing: {path}"])
    try:
        if _sha256(path) != resource.get("sha256"):
            issues.append("resource report SHA-256 mismatch")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("resource report must be an object")
        for field, expected in (
            ("activated", True),
            ("diagnosis", "resource_service_chain_activated"),
            ("config_hash", identity.get("config_hash")),
            ("git_commit", identity.get("git_commit")),
            ("source_tree_hash", identity.get("source_tree_hash")),
        ):
            if payload.get(field) != expected or resource.get(field) != expected:
                issues.append(f"resource {field} mismatch")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        issues.append(str(exc))
    return _check("resource_activation", issues)


def _job_records(
    root: Path,
    jobs: Sequence[Mapping[str, object]],
) -> tuple[AuditCheck, dict[str, JobRecord]]:
    issues: list[str] = []
    records: dict[str, JobRecord] = {}
    identity_fields = (
        "method", "scale", "training_seed", "config_hash", "git_commit",
        "execution_profile", "target_updates", "rollout_horizon", "family",
        "condition_id", "scenario_split", "protocol_hash", "source_tree_hash", "git_dirty",
    )
    for expected in jobs:
        job_id = str(expected.get("job_id", ""))
        try:
            path = _relative_path(root, expected.get("job_record_path"))
            record = load_job_record(path)
            if record.job_id != job_id:
                raise ValueError("job ID mismatch")
            if record.status != "completed":
                raise ValueError(f"status is {record.status!r}, not completed")
            observed = record.identity.to_dict()
            mismatches = [field for field in identity_fields if observed.get(field) != expected.get(field)]
            if mismatches:
                raise ValueError(f"identity mismatch: {mismatches}")
            records[job_id] = record
        except (OSError, ValueError, TypeError) as exc:
            issues.append(f"{job_id or '<missing-job-id>'}: {exc}")
    if len(records) != len(jobs):
        issues.append(f"loaded {len(records)} of {len(jobs)} completed jobs")
    return _check("job_records", issues), records


def _checkpoint_integrity(
    root: Path,
    jobs: Sequence[Mapping[str, object]],
    records: Mapping[str, JobRecord],
) -> tuple[AuditCheck, dict[str, str]]:
    issues: list[str] = []
    hashes: dict[str, str] = {}
    for expected in jobs:
        job_id = str(expected.get("job_id", ""))
        record = records.get(job_id)
        if record is None:
            issues.append(f"{job_id}: completed job record unavailable")
            continue
        try:
            checkpoint = _relative_path(root, expected.get("checkpoint_path"))
            if not checkpoint.is_file():
                raise FileNotFoundError(f"checkpoint is missing: {checkpoint}")
            if record.checkpoint_path is None or record.checkpoint_path.resolve() != checkpoint:
                raise ValueError("checkpoint path does not match the manifest")
            digest = _sha256(checkpoint)
            if record.checkpoint_sha256 != digest:
                raise ValueError("checkpoint SHA-256 mismatch")
            if record.checkpoint_step != int(expected.get("target_updates", -1)):
                raise ValueError("checkpoint step is not the registered final update")
            hashes[job_id] = digest
        except (OSError, ValueError, TypeError) as exc:
            issues.append(f"{job_id}: {exc}")
    return _check("checkpoint_integrity", issues), hashes


def _evaluation_identity(
    root: Path,
    jobs: Sequence[Mapping[str, object]],
    evaluations: Sequence[Mapping[str, object]],
    checkpoint_hashes: Mapping[str, str],
) -> tuple[AuditCheck, list[dict[str, Any]]]:
    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    jobs_by_id = {str(row.get("job_id", "")): row for row in jobs}
    seen_run_ids: set[str] = set()
    for expected in evaluations:
        job_id = str(expected.get("job_id", ""))
        job = jobs_by_id.get(job_id)
        try:
            if job is None:
                raise ValueError("evaluation references an unknown job")
            path = _relative_path(root, expected.get("raw_path"))
            if not path.is_file():
                raise ValueError(f"missing evaluation file: {path}")
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) != 1 or not lines[0].strip():
                raise ValueError("expected exactly one JSON object in the evaluation file")
            value = json.loads(lines[0])
            if not isinstance(value, dict):
                raise ValueError("evaluation row must be a JSON object")
            rows.append(value)
            run_id = str(value.get("run_id", ""))
            if run_id in seen_run_ids:
                raise ValueError(f"duplicate run_id: {run_id}")
            seen_run_ids.add(run_id)
            expected_values = {
                "job_id": job_id,
                "run_id": f"{job_id}:0:{expected.get('scenario_id')}",
                "method": job.get("method"),
                "scale": job.get("scale"),
                "training_seed": job.get("training_seed"),
                "scenario_id": expected.get("scenario_id"),
                "split": "validation",
                "execution_profile": "simulation",
                "checkpoint_sha256": checkpoint_hashes.get(job_id),
                "checkpoint_step": job.get("target_updates"),
                "target_updates": job.get("target_updates"),
                "family": job.get("family"),
                "condition_id": job.get("condition_id"),
                "config_hash": job.get("config_hash"),
                "git_commit": job.get("git_commit"),
                "git_dirty": False,
                "protocol_hash": job.get("protocol_hash"),
                "source_tree_hash": job.get("source_tree_hash"),
            }
            mismatches = [field for field, expected_value in expected_values.items() if value.get(field) != expected_value]
            if mismatches:
                raise ValueError(f"evaluation identity mismatch: {mismatches}")
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            issues.append(f"{job_id}:{expected.get('scenario_id')}: {exc}")
    if len(rows) != len(evaluations):
        issues.append(f"loaded {len(rows)} of {len(evaluations)} expected evaluation rows")
    return _check("evaluation_identity", issues), rows


def _metric_finiteness(rows: Sequence[Mapping[str, Any]], expected_count: int) -> AuditCheck:
    issues: list[str] = []
    if len(rows) != expected_count:
        issues.append(f"metric audit received {len(rows)} of {expected_count} expected rows")
    missing = [
        str(row.get("run_id", "<missing-run-id>"))
        for row in rows
        if any(metric not in row for metric in M3_REQUIRED_METRICS)
    ]
    if missing:
        issues.append(f"required M3 metrics missing from {len(missing)} rows")
    for row in rows:
        for metric in M3_REQUIRED_METRICS:
            if metric not in row or metric == "success":
                continue
            value = row[metric]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                issues.append(f"{row.get('run_id')}: {metric} is not finite numeric evidence")
                break
    try:
        if rows:
            validate_episode_records(rows, strict=True)
    except ValueError as exc:
        issues.append(f"strict episode validation failed: {exc}")
    return _check("metric_finiteness", issues)


def _sealed_test_exclusion(
    manifest: Mapping[str, object],
    evaluations: Sequence[Mapping[str, object]],
    rows: Sequence[Mapping[str, Any]],
) -> AuditCheck:
    issues: list[str] = []
    profile = manifest.get("profile")
    if not isinstance(profile, Mapping) or profile.get("split") != "validation":
        issues.append("manifest profile is not validation-only")
    config, _spec, context_issues = _canonical_context(manifest)
    issues.extend(context_issues)
    validation_ids: set[str] = set()
    if config is not None:
        try:
            validation_ids = {
                str(value) for value in config.experiments["validation_scenarios"]
            }
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"validation scenario registry unavailable: {exc}")
    for source, values in (("manifest", evaluations), ("raw", rows)):
        if any(str(row.get("split", "")) != "validation" for row in values):
            issues.append(f"{source} evidence contains a non-validation split")
        if validation_ids and any(
            str(row.get("scenario_id", "")) not in validation_ids for row in values
        ):
            issues.append(f"{source} evidence contains an unregistered or sealed-test scenario identifier")
        if any("sealed" in str(row.get("scenario_id", "")).lower() for row in values):
            issues.append(f"{source} evidence contains a sealed-test scenario identifier")
    return _check("sealed_test_exclusion", issues)


def _provenance_chain(
    manifest: Mapping[str, object],
    jobs: Sequence[Mapping[str, object]],
    rows: Sequence[Mapping[str, Any]],
) -> AuditCheck:
    issues: list[str] = []
    identity = manifest.get("identity")
    if not isinstance(identity, Mapping):
        return _check("provenance_chain", ["manifest identity is malformed"])
    if identity.get("git_dirty") is not False:
        issues.append("manifest source is dirty")
    for field in ("config_hash", "protocol_hash", "source_tree_hash"):
        value = str(identity.get(field, ""))
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
            issues.append(f"manifest {field} is not a SHA-256 digest")
        if any(row.get(field) != identity.get(field) for row in jobs):
            issues.append(f"job {field} provenance is mixed")
        if rows and any(row.get(field) != identity.get(field) for row in rows):
            issues.append(f"evaluation {field} provenance is mixed")
    if any(row.get("git_commit") != identity.get("git_commit") for row in jobs):
        issues.append("job Git commit provenance is mixed")
    if rows and any(row.get("git_commit") != identity.get("git_commit") for row in rows):
        issues.append("evaluation Git commit provenance is mixed")
    return _check("provenance_chain", issues)


def _failure_report(manifest_path: Path, root: Path, detail: str) -> dict[str, object]:
    names = (
        "output_root_binding", "manifest_shape", "resource_activation", "job_records", "checkpoint_integrity",
        "evaluation_identity", "metric_finiteness", "sealed_test_exclusion", "provenance_chain",
    )
    checks = [AuditCheck(name, False, detail).to_dict() for name in names]
    base: dict[str, object] = {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "output_root": str(root),
        "manifest_semantic_sha256": "",
        "m3_ready": False,
        "highest_maturity": "M2",
        "counts": {
            "expected_jobs": 0, "completed_jobs": 0,
            "expected_evaluations": 0, "valid_evaluations": 0,
        },
        "checks": checks,
    }
    base["report_semantic_sha256"] = _canonical_sha256(base)
    return base


def audit_m3_pilot(
    manifest_path: str | Path,
    *,
    output_root: str | Path,
) -> dict[str, object]:
    """Return a complete diagnostic report without mutating source evidence."""

    source = Path(manifest_path).resolve()
    root = Path(output_root).resolve()
    try:
        manifest = load_m3_manifest(source)
        jobs = _mapping_rows(manifest.get("jobs"), "jobs")
        evaluations = _mapping_rows(manifest.get("evaluations"), "evaluations")
    except (OSError, ValueError, TypeError) as exc:
        return _failure_report(source, root, f"manifest unavailable: {exc}")

    shape = _manifest_shape(manifest, jobs, evaluations)
    identity = manifest.get("identity")
    expected_root = (
        Path(str(identity.get("output_root"))).resolve()
        if isinstance(identity, Mapping) and identity.get("output_root")
        else None
    )
    root_check = _check(
        "output_root_binding",
        [] if expected_root == root else [
            f"audit output root {root} does not match manifest output root {expected_root}"
        ],
    )
    resource = _resource_activation(manifest)
    job_check, records = _job_records(root, jobs)
    checkpoint_check, checkpoint_hashes = _checkpoint_integrity(root, jobs, records)
    evaluation_check, rows = _evaluation_identity(
        root, jobs, evaluations, checkpoint_hashes,
    )
    metric_check = _metric_finiteness(rows, len(evaluations))
    sealed_check = _sealed_test_exclusion(manifest, evaluations, rows)
    provenance_check = _provenance_chain(manifest, jobs, rows)
    checks = [
        root_check, shape, resource, job_check, checkpoint_check, evaluation_check,
        metric_check, sealed_check, provenance_check,
    ]
    ready = all(check.passed for check in checks)
    completed_jobs = sum(1 for record in records.values() if record.status == "completed")
    valid_evaluations = len(rows) if evaluation_check.passed and metric_check.passed else 0
    base: dict[str, object] = {
        "schema_version": 1,
        "manifest": str(source),
        "output_root": str(root),
        "manifest_semantic_sha256": str(manifest["semantic_sha256"]),
        "m3_ready": ready,
        "highest_maturity": "M3" if ready else "M2",
        "counts": {
            "expected_jobs": len(jobs),
            "completed_jobs": completed_jobs,
            "expected_evaluations": len(evaluations),
            "valid_evaluations": valid_evaluations,
        },
        "checks": [check.to_dict() for check in checks],
    }
    base["report_semantic_sha256"] = _canonical_sha256(base)
    return base


__all__ = ["AuditCheck", "M3_REQUIRED_METRICS", "audit_m3_pilot"]
