"""Development-only G5 pilot orchestration and validation-candidate freezing."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from problem2.experiments.artifacts import artifact_sha256, atomic_write_bytes
from problem2.experiments.ecology_policy import DYNAMIC_OUTPUT_ROOT, HISTORICAL_OUTPUT_ROOT
from problem2.experiments.g5_contract import (
    BudgetDecision,
    FROZEN_CANDIDATE_BUDGETS,
    FROZEN_CHECKPOINT_COUNT,
    FROZEN_MAX_PROJECTED_HOURS,
    G5Contract,
    LEARNING_METHODS,
    PROBLEM2_CONDITIONS,
)

from .budget import aggregate_runtime
from .preflight import run_preflight
from .runner import METHODS, run_training_job
from .tuning import CanonicalValidationStore


PILOT_SCALES = ("g20x20_d2", "g30x50_d4")
PILOT_METHODS = METHODS
PILOT_CONDITIONS = (
    "sr_mappo_mobile",
    "sr_mappo_fixed",
    "sr_mappo_astar",
    "mappo_mobile",
    "sr_mappo_two_stage",
    "ippo_mobile",
    "maddpg_mobile",
    "iql_mobile",
)
PILOT_EXCLUDED_CONDITIONS = (
    "sr_mappo_nearest",
    "sr_mappo_urgency",
    "no_observation_normalization",
    "no_return_normalization",
    "no_network_stabilization",
    "no_robust_value_update",
    "no_learning_rate_decay",
    "learning_rate",
    "clip_range",
    "entropy_coef",
    "gamma",
    "gae_lambda",
)
PILOT_METHOD_BY_CONDITION = MappingProxyType({
    "sr_mappo_mobile": "sr_mappo_mobile",
    "sr_mappo_fixed": "sr_mappo_mobile",
    "sr_mappo_astar": "sr_mappo_mobile",
    "mappo_mobile": "mappo_mobile",
    "sr_mappo_two_stage": "sr_mappo_mobile",
    "ippo_mobile": "ippo_mobile",
    "maddpg_mobile": "maddpg_mobile",
    "iql_mobile": "iql_mobile",
})
PILOT_TRAINING_SEEDS = (51001, 51002, 51003)
PILOT_SCENARIO_IDS = tuple(range(10000, 10020))
VALIDATION_SCENARIO_IDS = tuple(range(20000, 20050))
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DYNAMIC_ECOLOGY_VERSION = "problem2-dynamic-pest-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class PilotJob:
    method: str
    condition_id: str
    scale: str
    training_seed: int
    scenario_id: int
    partition: str = "development"
    scenario_ids: tuple[int, ...] = PILOT_SCENARIO_IDS

    @property
    def identity(self) -> str:
        payload = json.dumps(
            {
                "condition_id": self.condition_id,
                "method": self.method,
                "partition": self.partition,
                "scale": self.scale,
                "scenario_id": self.scenario_id,
                "scenario_ids": self.scenario_ids,
                "training_seed": self.training_seed,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_commit(root: Path) -> str:
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("pilot provenance requires a Git source commit") from exc
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        raise ValueError("pilot provenance contains an invalid source commit")
    return commit


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError("pilot provenance requires Git ancestry verification") from exc
    if result.returncode not in (0, 1):
        raise ValueError("pilot generation commit cannot be resolved")
    return result.returncode == 0


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _contract_guard(contract: G5Contract) -> None:
    if contract.validation_accessed or contract.sealed_accessed:
        raise ValueError("pilot cannot proceed after validation or sealed access")
    observed_seeds = tuple(contract.partitions["development_training"])
    observed_scenarios = tuple(contract.partitions["development_scenarios"])
    if observed_seeds != PILOT_TRAINING_SEEDS or observed_scenarios != PILOT_SCENARIO_IDS:
        raise ValueError("development pilot partition drifted")


def _validate_dynamic_pilot_result(result: Mapping[str, Any]) -> None:
    """Require an executed physical dynamic-environment result.

    Missing fields are rejected instead of defaulting to a safe value.  This
    keeps a synthetic or historical runner from being promoted to replacement
    G5 evidence merely by returning identity and boundary flags.
    """

    if result.get("partition") != "development":
        raise ValueError("pilot runner must explicitly prove partition=development")
    if result.get("training_mode") != "physical_development":
        raise ValueError("pilot runner must prove physical_development training")
    if result.get("scenario_execution") is not True:
        raise ValueError("pilot runner must prove scenario_execution=true")
    if result.get("completion_validated") is not True:
        raise ValueError("pilot runner must prove completion_validated=true")
    if result.get("replenished_resource") != "pesticide":
        raise ValueError("pilot runner must prove pesticide-only replenishment")
    provenance = result.get("source_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("ecology_mode") != "dynamic":
        raise ValueError("pilot runner must provide dynamic ecology provenance")
    if provenance.get("ecology_version") != _DYNAMIC_ECOLOGY_VERSION:
        raise ValueError("pilot runner returned an invalid dynamic ecology version")
    implementation_version = provenance.get("ecology_implementation_version")
    if implementation_version != _DYNAMIC_ECOLOGY_VERSION:
        raise ValueError("pilot runner returned an invalid dynamic implementation version")
    for field in ("ecology_config_sha256", "ecology_scenario_sha256"):
        value = provenance.get(field)
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise ValueError(f"pilot runner returned invalid dynamic ecology {field}")
    source_commit = provenance.get("ecology_source_commit")
    if not isinstance(source_commit, str) or _HEX40.fullmatch(source_commit) is None:
        raise ValueError("pilot runner returned invalid dynamic ecology source commit")


def build_pilot_matrix(
    contract: G5Contract,
    *,
    scales: Sequence[str] = PILOT_SCALES,
    methods: Sequence[str] = PILOT_METHODS,
    conditions: Sequence[str] = PILOT_CONDITIONS,
    training_seeds: Sequence[int] = PILOT_TRAINING_SEEDS,
    scenario_ids: Sequence[int] = PILOT_SCENARIO_IDS,
) -> tuple[PilotJob, ...]:
    """Expand the complete small/large development pilot coverage matrix."""

    _contract_guard(contract)
    if tuple(scales) != PILOT_SCALES:
        raise ValueError("pilot must cover the frozen smallest and largest scales")
    if tuple(methods) != PILOT_METHODS:
        raise ValueError("pilot methods must match the five learning methods")
    if tuple(conditions) != PILOT_CONDITIONS:
        raise ValueError("pilot conditions must cover every registered condition type")
    if tuple(training_seeds) != PILOT_TRAINING_SEEDS or tuple(scenario_ids) != PILOT_SCENARIO_IDS:
        raise ValueError("pilot seeds/scenarios must match the development partition")
    if (
        set(PILOT_METHOD_BY_CONDITION) != set(PILOT_CONDITIONS)
        or set(PILOT_METHOD_BY_CONDITION.values()) != set(PILOT_METHODS)
    ):
        raise ValueError("pilot condition-method mapping is incomplete")
    jobs = tuple(
        PilotJob(PILOT_METHOD_BY_CONDITION[condition], condition, scale, seed, scenario)
        for scale in scales
        for seed in training_seeds
        for condition in conditions
        for scenario in (scenario_ids[0],)
    )
    identities = [job.identity for job in jobs]
    if len(identities) != len(set(identities)):
        raise ValueError("pilot matrix contains duplicate identities")
    return jobs


def _paths_for_output(output_root: Path) -> tuple[Path, Path]:
    base = _pilot_base_root(output_root)
    return base / "validated" / "pilot-episodes.jsonl", base / "audits" / "pilot-audit.json"


def _pilot_base_root(output_root: Path) -> Path:
    return output_root.parent if output_root.name == "pilots" else output_root


def _canonical_g5_root(contract: G5Contract) -> Path:
    return (_REPOSITORY_ROOT / DYNAMIC_OUTPUT_ROOT / "g5").resolve()


def _historical_g5_root() -> Path:
    return (_REPOSITORY_ROOT / HISTORICAL_OUTPUT_ROOT).resolve()


def _require_canonical_path(
    path: Path,
    contract: G5Contract,
    label: str,
    *,
    allow_noncanonical_output_root: bool,
    allow_historical_read: bool = False,
) -> Path:
    resolved = path.resolve()
    if contract.source_root.resolve() != _REPOSITORY_ROOT:
        raise ValueError("pilot contract source root is not the canonical repository")
    if allow_noncanonical_output_root:
        return resolved
    permitted_roots = [_canonical_g5_root(contract)]
    if allow_historical_read:
        permitted_roots.append(_historical_g5_root())
    if not any(resolved.is_relative_to(root) for root in permitted_roots):
        raise ValueError(f"{label} must be under the canonical G5 output root")
    return resolved


def _artifact_entry(base: Path, path: Path) -> dict[str, Any]:
    resolved_base = base.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError("pilot artifact escapes output root") from exc
    return {"path": relative.as_posix(), "sha256": artifact_sha256(resolved_path), "bytes": resolved_path.stat().st_size}


def write_pilot_artifact_manifest(
    contract: G5Contract,
    episodes_path: Path | str,
    audit_path: Path | str,
    *,
    manifest_path: Path | str | None = None,
    allow_noncanonical_output_root: bool = False,
) -> dict[str, Any]:
    """Write and verify the provenance-bound manifest for consolidated pilot artifacts."""

    episodes = Path(episodes_path).resolve()
    audit = Path(audit_path).resolve()
    base = episodes.parent.parent
    manifest = Path(manifest_path).resolve() if manifest_path is not None else base / "audits" / "pilot-artifact-manifest.json"
    _require_canonical_path(base, contract, "pilot output root", allow_noncanonical_output_root=allow_noncanonical_output_root)
    for path, label in ((episodes, "pilot episodes"), (audit, "pilot audit"), (manifest, "pilot artifact manifest")):
        _require_canonical_path(path, contract, label, allow_noncanonical_output_root=allow_noncanonical_output_root)
        if not path.is_file() and path != manifest:
            raise ValueError(f"{label} is missing")
    payload = {
        "schema_version": "g5-pilot-artifact-manifest-v1",
        "status": "pass",
        "maturity": "M2",
        "data_status": "development_pilot_descriptive",
        "source_commit": _source_commit(contract.source_root),
        "source_root": str(contract.source_root),
        "artifact_root": str(base),
        "artifacts": [_artifact_entry(base, episodes), _artifact_entry(base, audit)],
    }
    atomic_write_bytes(manifest, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    verify_pilot_artifacts(contract, episodes, audit, manifest, allow_noncanonical_output_root=allow_noncanonical_output_root)
    return {**payload, "path": str(manifest)}


def verify_pilot_artifacts(
    contract: G5Contract,
    episodes_path: Path | str,
    audit_path: Path | str,
    manifest_path: Path | str,
    *,
    allow_noncanonical_output_root: bool = False,
) -> dict[str, Any]:
    """Re-read the consolidated pilot artifacts and fail closed on drift."""

    episodes = Path(episodes_path).resolve()
    audit = Path(audit_path).resolve()
    manifest = Path(manifest_path).resolve()
    base = episodes.parent.parent
    _require_canonical_path(
        base,
        contract,
        "pilot output root",
        allow_noncanonical_output_root=allow_noncanonical_output_root,
        allow_historical_read=True,
    )
    try:
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("pilot artifact manifest is unreadable") from exc
    if recorded.get("schema_version") != "g5-pilot-artifact-manifest-v1" or recorded.get("status") != "pass":
        raise ValueError("pilot artifact manifest is invalid")
    current_commit = _source_commit(contract.source_root)
    generation_commit = recorded.get("source_commit")
    if not isinstance(generation_commit, str) or not _is_ancestor(contract.source_root, generation_commit, current_commit):
        raise ValueError("pilot artifact manifest source commit is not an ancestor of the current commit")
    if recorded.get("source_root") != str(contract.source_root.resolve()) or recorded.get("artifact_root") != str(base.resolve()):
        raise ValueError("pilot artifact manifest provenance is invalid")
    expected = {"validated/pilot-episodes.jsonl", "audits/pilot-audit.json"}
    artifacts = recorded.get("artifacts")
    if not isinstance(artifacts, list) or {item.get("path") for item in artifacts if isinstance(item, Mapping)} != expected:
        raise ValueError("pilot artifact manifest does not match consolidated artifacts")
    for item in artifacts:
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
            raise ValueError("pilot artifact manifest entry is invalid")
        candidate = (base / item["path"]).resolve()
        try:
            candidate.relative_to(base.resolve())
        except ValueError as exc:
            raise ValueError("pilot artifact path escapes output root") from exc
        if not candidate.is_file():
            raise ValueError(f"pilot artifact is missing: {item['path']}")
        if artifact_sha256(candidate) != item.get("sha256"):
            raise ValueError(f"pilot artifact hash mismatch: {item['path']}")
        if candidate.stat().st_size != item.get("bytes"):
            raise ValueError(f"pilot artifact byte mismatch: {item['path']}")
    try:
        audit_payload = json.loads(audit.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("pilot audit is unreadable") from exc
    if not isinstance(audit_payload, Mapping) or audit_payload.get("artifact_manifest_path") != str(manifest) or audit_payload.get("episodes_path") != str(episodes):
        raise ValueError("pilot audit does not bind its artifact manifest")
    historical_artifact = base.is_relative_to(_historical_g5_root())
    if not historical_artifact:
        expected_job_identities = [job.identity for job in build_pilot_matrix(contract)]
        if audit_payload.get("expected_job_identities") != expected_job_identities:
            raise ValueError("pilot audit expected identity set drifted")
        completed_job_identities = audit_payload.get("completed_job_identities")
        if not isinstance(completed_job_identities, list) or len(completed_job_identities) != len(set(completed_job_identities)):
            raise ValueError("pilot audit completed identity set is invalid")
        if not set(completed_job_identities).issubset(set(expected_job_identities)):
            raise ValueError("pilot audit completed identity set is outside the replacement matrix")
        replacement_scope = audit_payload.get("replacement_scope")
        expected_scope = {
            "job_count": len(expected_job_identities),
            "conditions": list(PILOT_CONDITIONS),
            "methods": list(PILOT_METHODS),
            "scales": list(PILOT_SCALES),
            "training_seeds": list(PILOT_TRAINING_SEEDS),
            "scenario_ids": list(PILOT_SCENARIO_IDS),
        }
        if replacement_scope != expected_scope:
            raise ValueError("pilot audit replacement scope drifted")
        matrix_complete = audit_payload.get("matrix_complete")
        if matrix_complete is not (
            audit_payload.get("status") == "pass"
            and len(completed_job_identities) == len(expected_job_identities)
            and set(completed_job_identities) == set(expected_job_identities)
        ):
            raise ValueError("pilot audit matrix completeness declaration is invalid")
    if not isinstance(audit_payload.get("provenance"), Mapping) or audit_payload["provenance"].get("source_commit") != recorded.get("source_commit"):
        raise ValueError("pilot audit source commit mismatch")
    recorded_hashes = audit_payload["provenance"].get("contract_hashes")
    if not isinstance(recorded_hashes, Mapping):
        raise ValueError("pilot audit lacks frozen contract hashes")
    governance_state_paths = {
        "configs/problem2/g5/protocol.yaml",
        "docs/evidence/g5/checkpoint_selection.yaml",
        "docs/evidence/g1/sealed_test_lock.yaml",
    }
    for relative, expected_hash in recorded_hashes.items():
        if relative in governance_state_paths:
            continue
        if contract.file_hashes.get(relative) != expected_hash:
            raise ValueError(f"pilot frozen contract scope drifted: {relative}")
    try:
        records = [json.loads(line.decode("utf-8")) for line in episodes.read_bytes().splitlines()]
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
        raise ValueError("pilot episodes are unreadable") from exc
    if len(records) != audit_payload.get("episode_count"):
        raise ValueError("pilot episode count mismatch")
    expected_jobs_by_identity = {job.identity: job for job in build_pilot_matrix(contract)}
    observed_identities: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping) or record.get("data_status") != "development_pilot_descriptive" or record.get("record_type") != "scenario_reference" or record.get("scenario_execution") is not False or record.get("partition") != "development":
            raise ValueError("pilot episode record is invalid")
        if historical_artifact:
            continue
        identity = record.get("pilot_job_identity")
        job = expected_jobs_by_identity.get(identity) if isinstance(identity, str) else None
        if job is None:
            raise ValueError("pilot episode identity is outside the replacement matrix")
        observed_identities.add(identity)
        for field, expected_value in {
            "method": job.method,
            "algorithm_id": job.method,
            "condition_id": job.condition_id,
            "scale": job.scale,
            "training_seed": job.training_seed,
            "partition": "development",
        }.items():
            if record.get(field) != expected_value:
                raise ValueError(f"pilot episode identity field drifted: {field}")
        if record.get("scenario_id") not in PILOT_SCENARIO_IDS:
            raise ValueError("pilot episode scenario is outside the development panel")
        training_result = record.get("training_result")
        if not isinstance(training_result, Mapping):
            raise ValueError("pilot episode training result is missing")
        if training_result.get("training_scenario_id") != job.scenario_id or training_result.get("scenario_ids") != list(job.scenario_ids):
            raise ValueError("pilot episode training scenario panel drifted")
        _validate_dynamic_pilot_result(training_result)
        if training_result.get("method") != job.method or training_result.get("condition_id") != job.condition_id:
            raise ValueError("pilot episode training identity drifted")
    if not historical_artifact and observed_identities != set(audit_payload.get("completed_job_identities", ())):
        raise ValueError("pilot audit completed identities do not match episode records")
    return dict(recorded)


def run_pilot_matrix(
    contract: G5Contract,
    output_root: Path | str,
    *,
    jobs: Sequence[PilotJob] | None = None,
    interactions: int = 128,
    device: str = "cpu",
    runner: Callable[[Mapping[str, Any], str, int, Path], Mapping[str, Any]] = run_training_job,
    allow_noncanonical_output_root: bool = False,
) -> dict[str, Any]:
    """Run or inject the development pilot path and persist descriptive records."""

    _contract_guard(contract)
    if isinstance(interactions, bool) or not isinstance(interactions, int) or interactions <= 0:
        raise ValueError("pilot interactions must be a positive integer")
    selected_jobs = tuple(jobs) if jobs is not None else build_pilot_matrix(contract)
    identities = [job.identity for job in selected_jobs]
    if len(identities) != len(set(identities)):
        raise ValueError("pilot jobs contain duplicate identities")
    expected_jobs = build_pilot_matrix(contract)
    expected_job_identities = [job.identity for job in expected_jobs]
    expected_identities = set(expected_job_identities)
    for job in selected_jobs:
        if job.partition != "development":
            raise ValueError("pilot jobs must use the development partition")
        if job.method not in PILOT_METHODS or job.condition_id not in PILOT_CONDITIONS:
            raise ValueError("pilot job method or condition is outside the frozen matrix")
        if job.scale not in PILOT_SCALES or job.training_seed not in PILOT_TRAINING_SEEDS:
            raise ValueError("pilot job scale or training seed is outside the frozen matrix")
        if job.scenario_id != PILOT_SCENARIO_IDS[0] or tuple(job.scenario_ids) != PILOT_SCENARIO_IDS:
            raise ValueError("pilot job scenario IDs must match the frozen development scenario panel")
    if {job.identity for job in selected_jobs} != expected_identities:
        raise ValueError("pilot matrix must contain the complete frozen training-job coverage")
    root = _require_canonical_path(Path(output_root), contract, "pilot output root", allow_noncanonical_output_root=allow_noncanonical_output_root)
    root.mkdir(parents=True, exist_ok=True)
    episodes_path, audit_path = _paths_for_output(root)
    preflight = run_preflight(device, contract.source_root)
    if (
        preflight.get("status") != "pass"
        or preflight.get("validation_accessed") is not False
        or preflight.get("sealed_accessed") is not False
        or preflight.get("battery_replenishment_enabled") is not False
    ):
        raise ValueError(preflight.get("reason", "pilot device preflight failed"))
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    completed_identities: list[str] = []
    boundary_flags = {"validation_accessed": False, "sealed_accessed": False, "battery_replenishment_enabled": False}
    boundary_status = {field: "unknown" for field in boundary_flags}
    for job in selected_jobs:
        job_root = root / f"{job.scale}__{job.scenario_id}__{job.method}__{job.condition_id}__{job.training_seed}"
        payload = {
            "method": job.method,
            "condition_id": job.condition_id,
            "training_seed": job.training_seed,
            "scenario_id": job.scenario_id,
            "partition": job.partition,
            "scale": job.scale,
            "scenario_ids": list(job.scenario_ids),
            "source_root": str(contract.source_root),
            "_contract": contract,
            "_preflight": preflight,
        }
        started = time.perf_counter()
        try:
            result = dict(runner(payload, device, interactions, job_root))
            elapsed = time.perf_counter() - started
            for field in ("validation_accessed", "sealed_accessed", "battery_replenishment_enabled"):
                value = result.get(field)
                boundary_flags[field] = boundary_flags[field] or value is True
                if type(value) is bool and value is False:
                    boundary_status[field] = "safe"
                else:
                    boundary_status[field] = "unsafe" if value is True else "unknown"
                    raise ValueError(f"pilot runner did not prove {field}=false")
            expected_result_identity = {
                "method": job.method,
                "algorithm_id": job.method,
                "condition_id": job.condition_id,
                "scale": job.scale,
                "training_seed": job.training_seed,
                "scenario_id": job.scenario_id,
            }
            for field, expected in expected_result_identity.items():
                if result.get(field) != expected:
                    raise ValueError(f"pilot runner returned mismatched {field}")
            if result.get("scenario_ids") != list(job.scenario_ids):
                raise ValueError("pilot runner returned mismatched scenario_ids")
            _validate_dynamic_pilot_result(result)
            if result.get("finite_metrics") is not True or result.get("evaluation_frozen") is not True:
                raise ValueError("pilot runner did not prove finite metrics and frozen evaluation")
            result_interactions = result.get("interactions", interactions)
            if isinstance(result_interactions, bool) or not isinstance(result_interactions, int) or result_interactions <= 0:
                raise ValueError("pilot runner returned invalid interactions")
            for episode_index, scenario_id in enumerate(job.scenario_ids):
                scenario_result = dict(result)
                # These are scenario-reference rows for one shared training run;
                # they are never presented as independent scenario executions.
                scenario_result["training_scenario_id"] = job.scenario_id
                scenario_result["scenario_id"] = scenario_id
                record = {
                    "schema_version": "g5-pilot-episode-v1",
                    "data_status": "development_pilot_descriptive",
                    "record_type": "scenario_reference",
                    "scenario_execution": False,
                    "pilot_job_identity": job.identity,
                    "episode_index": episode_index,
                    "method": job.method,
                "algorithm_id": job.method,
                "condition_id": job.condition_id,
                "scale": job.scale,
                "training_seed": job.training_seed,
                "scenario_id": scenario_id,
                    "partition": "development",
                    "interactions": result_interactions,
                    "elapsed_seconds": elapsed,
                    "seconds_per_interaction": elapsed / result_interactions,
                    "finite_metrics": True,
                    "evaluation_frozen": True,
                    "training_result": scenario_result,
                    "validation_accessed": False,
                    "sealed_accessed": False,
                    "battery_replenishment_enabled": False,
                }
                records.append(record)
            runtime_rows.append({
                "method_id": job.method,
                "scale_id": job.scale,
                "interactions": result_interactions,
                "elapsed_seconds": elapsed,
            })
            completed_identities.append(job.identity)
        except Exception as exc:
            failures.append({"pilot_job_identity": job.identity, "error": f"{type(exc).__name__}: {exc}"})
            break
    episodes_path.parent.mkdir(parents=True, exist_ok=True)
    episode_bytes = "".join(json.dumps(record, sort_keys=True, allow_nan=False) + "\n" for record in records).encode("utf-8")
    atomic_write_bytes(episodes_path, episode_bytes)
    coverage = {
        "expected_job_count": len(selected_jobs),
        "completed_job_count": len(runtime_rows),
        "scales": sorted({record["scale"] for record in records}),
        "methods": sorted({record["method"] for record in records}),
        "conditions": sorted({record["condition_id"] for record in records}),
        "training_seeds": sorted({record["training_seed"] for record in records}),
        "scenario_ids": sorted({record["scenario_id"] for record in records}),
    }
    matrix_complete = (
        not failures
        and len(completed_identities) == len(expected_job_identities)
        and set(completed_identities) == set(expected_job_identities)
        and len(records) == len(expected_job_identities) * len(PILOT_SCENARIO_IDS)
    )
    replacement_scope = {
        "job_count": len(expected_job_identities),
        "conditions": list(PILOT_CONDITIONS),
        "methods": list(PILOT_METHODS),
        "scales": list(PILOT_SCALES),
        "training_seeds": list(PILOT_TRAINING_SEEDS),
        "scenario_ids": list(PILOT_SCENARIO_IDS),
    }
    artifact_manifest_path = _pilot_base_root(root) / "audits" / "pilot-artifact-manifest.json"
    audit: dict[str, Any] = {
        "schema_version": "g5-pilot-audit-v1",
        "status": "pass" if not failures and len(runtime_rows) == len(selected_jobs) and len(records) == len(selected_jobs) * len(PILOT_SCENARIO_IDS) else "fail",
        "maturity": "M2",
        "data_status": "development_pilot_descriptive",
        "job_count": len(selected_jobs),
        "episode_count": len(records),
        "training_job_count": len(selected_jobs),
        "matrix_complete": matrix_complete,
        "expected_job_identities": expected_job_identities,
        "completed_job_identities": completed_identities,
        "replacement_scope": replacement_scope,
        "coverage": coverage,
        "runtime_aggregates": aggregate_runtime(runtime_rows) if runtime_rows else {},
        "failures": failures,
        "validation_accessed": boundary_flags["validation_accessed"],
        "sealed_accessed": boundary_flags["sealed_accessed"],
        "battery_replenishment_enabled": boundary_flags["battery_replenishment_enabled"],
        "boundary_status": boundary_status,
        "formal_training_performed": False,
        "episodes_path": str(episodes_path),
        "artifact_manifest_path": str(artifact_manifest_path),
        "provenance": {
            "source_commit": _source_commit(contract.source_root),
            "contract_hashes": dict(sorted(contract.file_hashes.items())),
        },
    }
    atomic_write_bytes(audit_path, (json.dumps(audit, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    write_pilot_artifact_manifest(
        contract,
        episodes_path,
        audit_path,
        manifest_path=artifact_manifest_path,
        allow_noncanonical_output_root=allow_noncanonical_output_root,
    )
    return {**audit, "episodes_path": str(episodes_path), "audit_path": str(audit_path), "artifact_manifest_path": str(artifact_manifest_path)}


def _candidate_payload(contract: G5Contract, decision: BudgetDecision) -> dict[str, Any]:
    if not isinstance(decision, BudgetDecision) or (
        type(decision.selected_budget) is not int
        or type(decision.checkpoint_interval) is not int
        or type(decision.checkpoint_count) is not int
        or decision.selected_budget <= 0
        or decision.checkpoint_interval <= 0
        or decision.checkpoint_count <= 0
        or decision.selected_budget not in FROZEN_CANDIDATE_BUDGETS
        or decision.checkpoint_count != FROZEN_CHECKPOINT_COUNT
        or decision.checkpoint_interval * decision.checkpoint_count != decision.selected_budget
        or isinstance(decision.projected_slowest_hours, bool)
        or not isinstance(decision.projected_slowest_hours, (int, float))
        or not math.isfinite(float(decision.projected_slowest_hours))
        or decision.projected_slowest_hours <= 0
        or decision.projected_slowest_hours > FROZEN_MAX_PROJECTED_HOURS
    ):
        raise ValueError("invalid frozen budget decision")
    scenario_hash = _json_hash(list(VALIDATION_SCENARIO_IDS))
    candidates = {
        method: [
            {
                "candidate_id": item.candidate_id,
                "config_hash": item.config_hash,
                "parameters": dict(item.parameters),
                "environment_interactions": decision.selected_budget,
                "checkpoint_interval": decision.checkpoint_interval,
                "scenario_panel_hash": scenario_hash,
            }
            for item in contract.tuning_candidates[method]
        ]
        for method in LEARNING_METHODS
    }
    return {
        "schema_version": "g5.v1",
        "manifest_id": "G5-VALIDATION-CANDIDATES",
        "status": "frozen_before_validation",
        "maturity": "M2",
        "partition": "validation",
        "candidate_edits_after_validation_access": False,
        "validation_accessed": False,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
        "equal_environment_interactions": decision.selected_budget,
        "checkpoint_interval": decision.checkpoint_interval,
        "checkpoint_count": decision.checkpoint_count,
        "projected_slowest_hours": decision.projected_slowest_hours,
        "scenario_panel": {
            "start": VALIDATION_SCENARIO_IDS[0],
            "end": VALIDATION_SCENARIO_IDS[-1],
            "count": len(VALIDATION_SCENARIO_IDS),
            "scenario_ids_hash": scenario_hash,
            "scenario_content_included": False,
        },
        "selection_rule": {
            "primary": "mean_validation_reduction_rate",
            "tie_breakers": [
                "higher_success_probability",
                "lower_interaction_count",
                "lexicographically_smaller_config_hash",
            ],
        },
        "candidates": candidates,
        "provenance": {
            "source_commit": _source_commit(contract.source_root),
            "contract_hashes": dict(sorted(contract.file_hashes.items())),
            "generator": "problem2.training.pilot.freeze_validation_candidates",
        },
    }


def freeze_validation_candidates(
    contract: G5Contract,
    decision: BudgetDecision,
    output_path: Path | str,
    *,
    allow_noncanonical_output_root: bool = False,
) -> dict[str, Any]:
    """Freeze four hashed candidates per method before any validation access."""

    _contract_guard(contract)
    path = Path(output_path).resolve()
    _require_canonical_path(path, contract, "candidate manifest", allow_noncanonical_output_root=allow_noncanonical_output_root)
    if not allow_noncanonical_output_root:
        CanonicalValidationStore.assert_candidate_generation_allowed(contract.source_root)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("existing candidate manifest is unreadable") from exc
        if existing.get("validation_accessed") is True or existing.get("sealed_accessed") is True:
            raise ValueError("validation access makes candidate manifest immutable")
    payload = _candidate_payload(contract, decision)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError("candidate manifest drift before validation")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    return payload


__all__ = [
    "PILOT_CONDITIONS",
    "PILOT_EXCLUDED_CONDITIONS",
    "PILOT_METHOD_BY_CONDITION",
    "PILOT_METHODS",
    "PILOT_SCALES",
    "PilotJob",
    "build_pilot_matrix",
    "freeze_validation_candidates",
    "run_pilot_matrix",
    "verify_pilot_artifacts",
    "write_pilot_artifact_manifest",
]
