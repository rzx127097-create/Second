"""Immutable, recoverable execution of one frozen G6 training identity.

The module deliberately owns only the G6 orchestration boundary.  Algorithm
updates and physical transition construction remain in the tested G5 helpers;
this layer binds them to the frozen job identity, checkpoint schedule, ledger,
and validation panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import time
from typing import Any, Mapping

import numpy as np
import torch

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_training_checkpoint, save_training_checkpoint
from problem2.experiments.artifacts import append_jsonl, artifact_sha256, atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.identity import canonical_evaluation_identity, canonical_training_identity
from problem2.experiments.ledger import AppendOnlyLedger, JobState, LedgerError
from problem2.evaluation.runner import evaluate_episode
from problem2.evaluation.selection import select_frozen_checkpoint
from problem2.evaluation.validator import validate_dynamic_episode, validate_long_table
from problem2.training.conditions import resolve_condition_execution
from problem2.training.physical_training import (
    _as_action_result,
    _observe_physical_algorithm,
    _terminal_buffer_counts,
    _update_interval,
    _update_physical_algorithm,
    build_physical_envelope,
)
from problem2.training.tuning import build_development_environment, build_validation_environment


ROOT = Path(__file__).resolve().parents[3]
DYNAMIC_G6_RELATIVE = Path("outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6")
DYNAMIC_G5_MANIFEST_RELATIVE = Path("outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests")
TRAINING_MANIFEST_NAME = "g6-training-jobs.json"
VALIDATION_MANIFEST_NAME = "g6-validation-evaluations.json"
TRAINING_SCENARIOS = tuple(range(10000, 10020))
VALIDATION_SCENARIOS = tuple(range(20000, 20050))
FORMAL_METHODS = {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"}
SCALE_HORIZONS = {
    "g20x20_d2": 150,
    "g20x30_d3": 180,
    "g20x40_d3": 220,
    "g30x30_d3": 220,
    "g30x40_d4": 280,
    "g30x50_d4": 350,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_CHECKPOINT_NAME = re.compile(r"^checkpoint-(\d{9})\.pt$")


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(payload), sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


@dataclass(frozen=True)
class FormalJobPaths:
    root: Path
    attempts: Path
    checkpoints: Path
    training_events: Path
    validation_events: Path
    summary: Path
    manifest: Path
    selected_checkpoint: Path
    ledger: Path


def formal_job_paths(repository_root: Path | str, job: Mapping[str, Any], *, output_root: Path | str | None = None) -> FormalJobPaths:
    """Resolve one identity's G6 paths and reject output-root escapes."""

    root = Path(repository_root).resolve()
    configured = root / DYNAMIC_G6_RELATIVE
    base = configured if output_root is None else Path(output_root).resolve()
    if output_root is None and str(job.get("output_root")) != DYNAMIC_G6_RELATIVE.as_posix():
        raise ValueError("frozen job output root is not dynamic G6")
    identity = job.get("canonical_training_identity")
    if not isinstance(identity, str) or _SHA256.fullmatch(identity) is None:
        raise ValueError("formal job identity is invalid")
    if output_root is None and not base.is_relative_to(configured):
        raise ValueError("formal output root escapes dynamic G6 root")
    job_root = (base / "jobs" / identity).resolve()
    if not job_root.is_relative_to(base):
        raise ValueError("formal job path escapes output root")
    attempts = job_root / "attempts"
    return FormalJobPaths(
        root=job_root,
        attempts=attempts,
        checkpoints=job_root / "checkpoints",
        training_events=job_root / "training-events.jsonl",
        validation_events=job_root / "validation-episodes.jsonl",
        summary=job_root / "summary.json",
        manifest=job_root / "manifest.json",
        selected_checkpoint=job_root / "selected-checkpoint.json",
        ledger=base / "manifests" / "job-events.jsonl",
    )


def _training_manifest(root: Path) -> dict[str, Any]:
    return _load_json(root / DYNAMIC_G5_MANIFEST_RELATIVE / TRAINING_MANIFEST_NAME, "G6 training manifest")


def load_frozen_job(repository_root: Path | str, *, index: int = 0, expected_identity: str | None = None) -> dict[str, Any]:
    """Return one exact job from the immutable dynamic G6 manifest."""

    root = Path(repository_root).resolve()
    payload = _training_manifest(root)
    jobs = payload.get("jobs")
    if payload.get("status") != "frozen_unexecuted" or payload.get("ecology_id") != "dynamic_pest_v1":
        raise ValueError("dynamic G6 training manifest is not frozen and dynamic")
    scheduler_order = payload.get("scheduler_order")
    if not isinstance(jobs, list) or not isinstance(scheduler_order, list):
        raise ValueError("formal job scheduler order is missing")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= len(scheduler_order):
        raise ValueError("formal job index is out of range")
    identities = [entry.get("canonical_training_identity") for entry in jobs if isinstance(entry, dict)]
    if (
        len(identities) != len(jobs)
        or len(set(identities)) != len(identities)
        or len(scheduler_order) != len(jobs)
        or any(not isinstance(identity, str) or _SHA256.fullmatch(identity) is None for identity in scheduler_order)
        or len(set(scheduler_order)) != len(scheduler_order)
        or set(scheduler_order) != set(identities)
    ):
        raise ValueError("formal job scheduler order does not match manifest identities")
    selected_identity = scheduler_order[index]
    job = next((entry for entry in jobs if isinstance(entry, dict) and entry.get("canonical_training_identity") == selected_identity), None)
    if job is None:
        raise ValueError("formal scheduler identity is not present in jobs")
    if not isinstance(job, dict):
        raise ValueError("formal job entry is invalid")
    calculated = canonical_training_identity(
        str(job.get("method")), str(job.get("scale")), int(job.get("training_seed")), str(job.get("config_hash")), str(job.get("git_commit"))
    )
    if job.get("canonical_training_identity") != calculated:
        raise ValueError("formal job identity drifted")
    if expected_identity is not None and job["canonical_training_identity"] != expected_identity:
        raise ValueError("formal job identity does not match expected identity")
    if any(30000 <= int(value) <= 30099 for value in job.get("validation_scenario_ids", ())):
        raise ValueError("sealed scenario identity is present in a G6 job")
    return dict(job)


def _source_commit(root: Path) -> str:
    import subprocess

    value = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if _SHA1.fullmatch(value) is None:
        raise ValueError("current Git commit is invalid")
    return value


def _source_scope_hash(root: Path) -> str:
    from scripts.freeze_g5 import _source_scope_hash as compute_source_scope_hash

    return str(compute_source_scope_hash(root))


def _source_commit_compatible(root: Path, frozen_commit: str, source_scope: str) -> bool:
    """Allow evidence-only commits after freeze when the scientific scope is unchanged."""

    if not isinstance(frozen_commit, str) or _SHA1.fullmatch(frozen_commit) is None:
        return False
    current = _source_commit(root)
    if frozen_commit == current:
        return True
    import subprocess

    ancestry = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", frozen_commit, current],
        capture_output=True,
        text=True,
        check=False,
    )
    if ancestry.returncode != 0:
        return False
    try:
        return _source_scope_hash(root) == source_scope
    except Exception:
        return False


def _validate_job(root: Path, job: Mapping[str, Any]) -> tuple[Any, Any, Any, str]:
    required = {
        "method", "condition_id", "scale", "candidate_id", "selected_candidate_config_hash", "training_seed", "config_hash", "git_commit",
        "canonical_training_identity", "environment_interactions", "checkpoint_interval",
        "checkpoint_count", "max_physical_decision_steps", "validation_scenario_ids",
        "validation_scenario_panel_hash", "protocol_hash", "source_scope_sha256",
        "dependency_graph", "ecology_id", "output_root", "deterministic_evaluation",
    }
    if not required <= set(job):
        raise ValueError("formal job is missing frozen fields")
    method = str(job["method"])
    if method not in FORMAL_METHODS:
        raise ValueError("formal job method is not registered")
    condition = str(job["condition_id"])
    execution = resolve_condition_execution(condition)
    contract = load_g5_contract(root)
    candidate_id = job["candidate_id"]
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("formal job candidate is invalid")
    candidates = contract.tuning_candidates.get(method, ())
    candidate = next((item for item in candidates if item.candidate_id == candidate_id), None)
    if candidate is None:
        raise ValueError("formal job candidate is not registered")
    if job["selected_candidate_config_hash"] != candidate.config_hash:
        raise ValueError("formal job candidate configuration drifted")
    dependency = job["dependency_graph"]
    if not isinstance(dependency, Mapping):
        raise ValueError("formal job dependency graph drifted")
    if dependency.get("candidate_id") != candidate_id or dependency.get("candidate_config_hash") != candidate.config_hash:
        raise ValueError("formal job candidate dependency drifted")
    for field in (
        "config_hash",
        "protocol_hash",
        "validation_scenario_panel_hash",
        "source_scope_sha256",
        "selected_candidate_config_hash",
    ):
        value = job.get(field)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"formal job hash is invalid: {field}")
    for field in (
        "candidate_manifest_sha256",
        "budget_manifest_sha256",
        "physical_scenario_contract_sha256",
    ):
        value = dependency.get(field)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"formal job dependency hash is invalid: {field}")
    if dependency.get("protocol_hash") != job["protocol_hash"]:
        raise ValueError("formal job protocol dependency drifted")
    seed = job["training_seed"]
    if type(seed) is not int or seed not in contract.partitions["formal_training"]:
        raise ValueError("formal training seed is outside the frozen partition")
    if str(job["output_root"]) != DYNAMIC_G6_RELATIVE.as_posix() or job["ecology_id"] != "dynamic_pest_v1":
        raise ValueError("formal job is not bound to dynamic G6 output")
    if job["deterministic_evaluation"] is not True or tuple(job["validation_scenario_ids"]) != VALIDATION_SCENARIOS:
        raise ValueError("formal validation protocol drifted")
    scale = job["scale"]
    if scale not in SCALE_HORIZONS or job["max_physical_decision_steps"] != SCALE_HORIZONS[scale]:
        raise ValueError("formal job scale horizon drifted")
    interactions = job["environment_interactions"]
    interval = job["checkpoint_interval"]
    count = job["checkpoint_count"]
    if type(interactions) is not int or interactions <= 0 or type(interval) is not int or interval <= 0 or type(count) is not int or count <= 0 or interval * count != interactions:
        raise ValueError("formal checkpoint schedule is inconsistent")
    expected_identity = canonical_training_identity(method, str(job["scale"]), seed, str(job["config_hash"]), str(job["git_commit"]))
    if expected_identity != job["canonical_training_identity"]:
        raise ValueError("formal canonical training identity mismatch")
    if not isinstance(job["source_scope_sha256"], str) or _SHA256.fullmatch(job["source_scope_sha256"]) is None:
        raise ValueError("formal job source scope hash is invalid")
    if not _source_commit_compatible(root, str(job["git_commit"]), str(job["source_scope_sha256"])):
        raise ValueError("formal job source commit or scope differs from current source")
    if dependency.get("source_commit") != job["git_commit"] or dependency.get("source_scope_sha256") != job["source_scope_sha256"]:
        raise ValueError("formal job dependency graph drifted")
    return contract, execution, dependency, expected_identity


def _provenance(job: Mapping[str, Any], identity: str) -> dict[str, str]:
    return {
        "source_commit": str(job["git_commit"]),
        "source_bundle_sha256": str(job["source_scope_sha256"]),
        "config_hash": str(job["config_hash"]),
        "protocol_hash": str(job["protocol_hash"]),
        "ancestry_hash": _stable_hash({"identity": identity, "source_scope_sha256": job["source_scope_sha256"]}),
    }


def _latest_checkpoint(paths: FormalJobPaths) -> Path | None:
    candidates = sorted(paths.checkpoints.glob("checkpoint-*.pt"))
    return candidates[-1] if candidates else None


def _current_evaluator_hash(root: Path) -> str:
    return _stable_hash(
        {
            "runner": artifact_sha256(root / "src/problem2/evaluation/runner.py"),
            "selector": artifact_sha256(root / "src/problem2/evaluation/selection.py"),
            "formal_g6": artifact_sha256(root / "src/problem2/training/formal_g6.py"),
        }
    )


def _validate_validation_manifest(root: Path, job: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the immutable validation-panel contract before any evaluation."""

    manifest = _load_json(root / DYNAMIC_G5_MANIFEST_RELATIVE / VALIDATION_MANIFEST_NAME, "G6 validation manifest")
    if (
        manifest.get("status") != "frozen_unexecuted"
        or manifest.get("manifest_id") != "G6-VALIDATION-EVALUATIONS"
        or manifest.get("partition") != "validation"
        or manifest.get("ecology_id") != "dynamic_pest_v1"
        or manifest.get("output_root") != DYNAMIC_G6_RELATIVE.as_posix()
        or manifest.get("scenario_ids") != list(VALIDATION_SCENARIOS)
        or manifest.get("scenario_content") is not None
        or manifest.get("deterministic_policy") is not True
        or manifest.get("sealed_accessed") is not False
        or manifest.get("evaluation_results") != []
    ):
        raise ValueError("G6 validation manifest is unsafe or drifted")
    checkpoint_count = manifest.get("checkpoint_count_per_job")
    if isinstance(checkpoint_count, bool) or not isinstance(checkpoint_count, int) or checkpoint_count <= 0:
        raise ValueError("G6 validation checkpoint count is invalid")
    training = _training_manifest(root)
    training_jobs = training.get("jobs")
    if (
        not isinstance(training_jobs, list)
        or manifest.get("expected_evaluation_count")
        != len(training_jobs) * checkpoint_count * len(VALIDATION_SCENARIOS)
    ):
        raise ValueError("G6 validation evaluation count does not match training manifest")
    if checkpoint_count != job.get("checkpoint_count"):
        raise ValueError("G6 validation checkpoint count differs from job")
    evaluator_hash = manifest.get("evaluator_hash")
    if not isinstance(evaluator_hash, str) or _SHA256.fullmatch(evaluator_hash) is None:
        raise ValueError("G6 evaluator hash is invalid")
    if manifest.get("scenario_panel_hash") != job.get("validation_scenario_panel_hash"):
        raise ValueError("G6 validation scenario panel differs from job")
    if manifest.get("source_scope_sha256") != job.get("source_scope_sha256"):
        raise ValueError("G6 validation source scope differs from job")
    provenance = manifest.get("provenance")
    if (
        not isinstance(provenance, Mapping)
        or provenance.get("source_commit") != job.get("git_commit")
        or provenance.get("protocol_hash") != job.get("protocol_hash")
    ):
        raise ValueError("G6 validation provenance differs from job")
    if evaluator_hash != _current_evaluator_hash(root):
        raise ValueError("G6 evaluator hash differs from current evaluator")
    return manifest


def _existing_checkpoint_records(paths: FormalJobPaths) -> list[dict[str, Any]]:
    """Recover the immutable checkpoint index written by an earlier attempt."""

    if not paths.manifest.is_file():
        records: list[dict[str, Any]] = []
        for path in sorted(paths.checkpoints.glob("checkpoint-*.pt")):
            match = _CHECKPOINT_NAME.fullmatch(path.name)
            if match is None or not path.is_file():
                raise ValueError("formal checkpoint artifact is invalid")
            records.append(
                {
                    "path": f"checkpoints/{path.name}",
                    "sha256": artifact_sha256(path),
                    "bytes": path.stat().st_size,
                    "interaction_count": int(match.group(1)),
                    "validation_rows": 0,
                }
            )
        return records
    payload = _load_json(paths.manifest, "formal job manifest")
    raw_records = payload.get("checkpoints")
    if not isinstance(raw_records, list):
        raise ValueError("formal job checkpoint manifest is incomplete")
    records: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in raw_records:
        if not isinstance(raw, Mapping):
            raise ValueError("formal checkpoint manifest entry is invalid")
        relative = raw.get("path")
        interaction_count = raw.get("interaction_count")
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError("formal checkpoint path is invalid")
        match = _CHECKPOINT_NAME.fullmatch(Path(relative).name)
        if match is None or Path(relative).parent != Path("checkpoints"):
            raise ValueError("formal checkpoint path is outside the checkpoint directory")
        if isinstance(interaction_count, bool) or not isinstance(interaction_count, int) or interaction_count != int(match.group(1)) or interaction_count in seen:
            raise ValueError("formal checkpoint interaction index is invalid")
        path = (paths.root / relative).resolve()
        if not path.is_relative_to(paths.checkpoints.resolve()) or not path.is_file():
            raise ValueError("formal checkpoint artifact is missing")
        digest = artifact_sha256(path)
        if raw.get("sha256") != digest or raw.get("bytes") != path.stat().st_size:
            raise ValueError("formal checkpoint artifact hash drifted")
        record = dict(raw)
        record["path"] = relative.replace("\\", "/")
        record["sha256"] = digest
        record["bytes"] = path.stat().st_size
        record["interaction_count"] = interaction_count
        validation_rows = raw.get("validation_rows", 0)
        if isinstance(validation_rows, bool) or not isinstance(validation_rows, int) or validation_rows < 0:
            raise ValueError("formal checkpoint validation row count is invalid")
        record["validation_rows"] = validation_rows
        records.append(record)
        seen.add(interaction_count)
    records.sort(key=lambda item: item["interaction_count"])
    return records


def _checkpoint_state(algorithm: Any, environment: Any, *, interaction_count: int, update_count: int, scenario_cursor: int, episode_interactions: int, episode_reward: float, fresh_since_update: int, executed_scenarios: list[int]) -> dict[str, Any]:
    return {
        "algorithm": algorithm.state_dict(),
        "formal_state": {
            "schema_version": "g6-formal-state-v1",
            "interaction_count": int(interaction_count),
            "update_count": int(update_count),
            "scenario_cursor": int(scenario_cursor),
            "episode_interactions": int(episode_interactions),
            "episode_reward": float(episode_reward),
            "fresh_since_update": int(fresh_since_update),
            "executed_scenarios": list(executed_scenarios),
            "environment": environment.state_dict(),
        },
    }


def _restore_checkpoint(path: Path, job: Mapping[str, Any], contract: Any, device: str, environment: Any) -> tuple[Any, dict[str, Any], str]:
    identity = str(job["canonical_training_identity"])
    provenance = _provenance(job, identity)
    algorithm, record = load_training_checkpoint(
        path,
        lambda: build_algorithm(str(job["method"]), contract, device, candidate_id=str(job["candidate_id"]), scale=str(job["scale"])),
        provenance,
    )
    state = record.state.get("formal_state")
    if not isinstance(state, Mapping) or state.get("schema_version") != "g6-formal-state-v1":
        raise ValueError("formal checkpoint state is incomplete")
    environment.load_state_dict(state["environment"])  # type: ignore[arg-type]
    return algorithm, dict(state), record.sha256


def _episode_row(environment: Any, job: Mapping[str, Any], *, checkpoint_hash: str, checkpoint_interactions: int, scenario_id: int, evaluator_hash: str, panel_hash: str, locator: str) -> dict[str, Any]:
    record = environment.episode_record()
    initial = float(np.sum(environment.initial_prey))
    final = float(np.sum(environment.prey))
    remaining = math.fsum(float(item.pesticide_l) for item in environment.state.uavs) + float(environment.state.vehicle.inventory_l)
    sprayed = float(environment.state.ledger.cumulative_sprayed_l)
    wind = environment.ecology.wind_state
    row = {
        "evaluation_identity": canonical_evaluation_identity(str(job["canonical_training_identity"]), str(job["condition_id"]), str(job["scale"]), int(job["training_seed"]), int(scenario_id), "validation", checkpoint_hash, evaluator_hash, panel_hash),
        "canonical_training_identity": str(job["canonical_training_identity"]),
        "method": str(job["method"]), "candidate_id": str(job["candidate_id"]), "condition_id": str(job["condition_id"]), "scale": str(job["scale"]),
        "training_seed": int(job["training_seed"]), "scenario_id": int(scenario_id), "partition": "validation", "source_commit": str(job["git_commit"]),
        "config_hash": str(job["config_hash"]), "protocol_hash": str(job["protocol_hash"]), "checkpoint_hash": checkpoint_hash,
        "evaluator_hash": evaluator_hash, "scenario_panel_hash": panel_hash,
        "candidate_manifest_sha256": str(job["dependency_graph"]["candidate_manifest_sha256"]),
        "budget_manifest_sha256": str(job["dependency_graph"]["budget_manifest_sha256"]),
        "physical_scenario_contract_sha256": str(job["dependency_graph"]["physical_scenario_contract_sha256"]),
        "episode_index": 0, "interaction_count": int(checkpoint_interactions), "termination_reason": "horizon", "terminated": True,
        "initial_total_pest": initial, "final_total_pest": final, "reduction_rate": 1.0 - final / initial,
        "success_at_0_85": (1.0 - final / initial) >= 0.85,
        "pesticide_initial_l": float(environment.state.ledger.initial_total_l), "pesticide_remaining_l": remaining,
        "pesticide_transferred_l": sprayed, "resource_conservation_residual_l": float(environment.episode_record().resource_residual_l),
        "battery_replenishment_l": 0.0, "action_uav": 0, "action_vehicle_slot": 0,
        "rendezvous_distance_m": float(record.rendezvous_distance_m), "vehicle_service_travel_m": float(record.vehicle_service_travel_m),
        "waiting_steps": float(record.waiting_steps), "completed_request_waiting_steps": float(record.completed_request_waiting_steps),
        "pesticide_disabled_steps": float(record.pesticide_disabled_steps), "return_steps": float(record.return_steps),
        "effective_spray_steps": float(record.effective_spray_steps), "decision_runtime_s": float(record.decision_runtime_s),
        "source_locator": locator,
        "metric_source": "dynamic_ecology_environment", "ecology_version": environment.ecology.config.version,
        "ecology_config_sha256": environment.ecology.config.contract_sha256, "ecology_scenario_sha256": environment.ecology.scenario.scenario_sha256,
        "ecology_source_commit": environment.ecology.scenario.source_commit, "ecology_implementation_version": environment.ecology.scenario.implementation_version,
        "initial_total_predator": float(np.sum(environment.initial_predator)), "final_total_predator": float(np.sum(environment.predator)),
        "cumulative_deposited_effect": float(environment.ecology.deposited_effect), "terminal_mean_concentration": float(np.mean(environment.ecology.concentration)),
        "terminal_max_concentration": float(np.max(environment.ecology.concentration)), "terminal_wind_direction": float(wind.direction),
        "terminal_wind_strength": float(wind.strength), "dynamic_step_count": int(environment.ecology.step_count),
    }
    validate_dynamic_episode(row)
    return row


def _evaluator_hash(root: Path) -> str:
    manifest = _load_json(root / DYNAMIC_G5_MANIFEST_RELATIVE / VALIDATION_MANIFEST_NAME, "G6 validation manifest")
    value = manifest.get("evaluator_hash")
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError("G6 evaluator hash is invalid")
    if value != _current_evaluator_hash(root):
        raise ValueError("G6 evaluator hash differs from current evaluator")
    return value


def evaluate_formal_checkpoint(root: Path | str, job: Mapping[str, Any], checkpoint: Path | str, *, device: str = "cpu", output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Evaluate one verified checkpoint on exactly the frozen validation panel."""

    repository_root = Path(root).resolve()
    contract, execution, _, identity = _validate_job(repository_root, job)
    checkpoint_path = Path(checkpoint).resolve()
    paths = formal_job_paths(repository_root, job)
    if not checkpoint_path.is_relative_to(paths.checkpoints.resolve()) or checkpoint_path.parent != paths.checkpoints.resolve():
        raise ValueError("formal evaluation checkpoint is outside the job checkpoint directory")
    if not checkpoint_path.is_file() or _CHECKPOINT_NAME.fullmatch(checkpoint_path.name) is None:
        raise ValueError("formal evaluation checkpoint is invalid")
    checkpoint_hash = artifact_sha256(checkpoint_path)
    validation_manifest = _validate_validation_manifest(repository_root, job)
    evaluator_hash = str(validation_manifest["evaluator_hash"])
    panel_hash = str(validation_manifest["scenario_panel_hash"])
    if output_path is not None:
        output = Path(output_path).resolve()
        if output != paths.validation_events.resolve():
            raise ValueError("formal validation output is outside the job directory")
    provenance = _provenance(job, identity)
    algorithm, _ = load_training_checkpoint(
        checkpoint_path,
        lambda: build_algorithm(str(job["method"]), contract, device, candidate_id=str(job["candidate_id"]), scale=str(job["scale"])),
        provenance,
    )
    algorithm.set_evaluation(True)
    rows: list[dict[str, Any]] = []
    for scenario_id in VALIDATION_SCENARIOS:
        environment = build_validation_environment(repository_root, scenario_id=scenario_id, scale=str(job["scale"]), condition_id=str(job["condition_id"]))
        evaluate_episode(environment, algorithm, "validation", scenario_id, deterministic=True)
        row = _episode_row(
            environment, job, checkpoint_hash=checkpoint_hash, checkpoint_interactions=int(job["environment_interactions"]),
            scenario_id=scenario_id, evaluator_hash=evaluator_hash, panel_hash=panel_hash,
            locator=str((output_path or checkpoint_path.parent) / f"validation-{scenario_id}.json"),
        )
        rows.append(row)
    expected_provenance = {
        "source_commit": str(job["git_commit"]), "config_hash": str(job["config_hash"]), "protocol_hash": str(job["protocol_hash"]),
        "checkpoint_hash": checkpoint_hash, "evaluator_hash": evaluator_hash, "scenario_panel_hash": panel_hash,
        "candidate_manifest_sha256": str(job["dependency_graph"]["candidate_manifest_sha256"]),
        "budget_manifest_sha256": str(job["dependency_graph"]["budget_manifest_sha256"]),
        "physical_scenario_contract_sha256": str(job["dependency_graph"]["physical_scenario_contract_sha256"]),
    }
    validate_long_table(rows, expected_provenance=expected_provenance, allow_validation_access=True)
    if output_path is not None:
        path = Path(output_path)
        for row in rows:
            append_jsonl(path, row)
    return rows


def _write_checkpoint(paths: FormalJobPaths, job: Mapping[str, Any], contract: Any, algorithm: Any, environment: Any, *, interaction_count: int, update_count: int, scenario_cursor: int, episode_interactions: int, episode_reward: float, fresh_since_update: int, executed_scenarios: list[int]) -> tuple[Path, str]:
    path = paths.checkpoints / f"checkpoint-{interaction_count:09d}.pt"
    provenance = _provenance(job, str(job["canonical_training_identity"]))
    record = save_training_checkpoint(path, _checkpoint_state(algorithm, environment, interaction_count=interaction_count, update_count=update_count, scenario_cursor=scenario_cursor, episode_interactions=episode_interactions, episode_reward=episode_reward, fresh_since_update=fresh_since_update, executed_scenarios=executed_scenarios), provenance)
    # A checkpoint is evidence only after its strict reload and state schema pass.
    restored, loaded = load_training_checkpoint(
        path,
        lambda: build_algorithm(str(job["method"]), contract, "cpu", candidate_id=str(job["candidate_id"]), scale=str(job["scale"])),
        provenance,
    )
    del restored
    if loaded.sha256 != record.sha256 or loaded.state.get("formal_state", {}).get("interaction_count") != interaction_count:
        raise RuntimeError("formal checkpoint reload verification failed")
    return path, record.sha256


def run_formal_job(root: Path | str, job: Mapping[str, Any], *, device: str = "cpu", output_root: Path | str | None = None, stop_after_interactions: int | None = None, evaluate_validation: bool = True, preflight: Mapping[str, Any] | None = None, resume_checkpoint: Path | str | None = None) -> dict[str, Any]:
    """Execute exactly one frozen formal job; short stops are test-only interruptions."""

    repository_root = Path(root).resolve()
    contract, execution, _, identity = _validate_job(repository_root, job)
    if preflight is not None and preflight.get("all_pass") is not True:
        raise RuntimeError("G6 preflight did not pass")
    paths = formal_job_paths(repository_root, job, output_root=output_root)
    ledger = AppendOnlyLedger(paths.ledger)
    input_hash = _stable_hash(dict(job))
    ledger_job = {
        "identity": identity, "input_hash": input_hash, "config_hash": str(job["config_hash"]),
        "protocol_hash": str(job["protocol_hash"]), "source_commit": str(job["git_commit"]),
        "scenario_panel_hash": str(job["validation_scenario_panel_hash"]),
    }
    ledger.register(ledger_job)
    current = ledger.current(identity)
    if current.state is JobState.COMPLETED:
        return _load_json(paths.summary, "completed formal summary")
    worker_id = f"g6-{os.getpid()}"
    target = int(job["environment_interactions"])
    if stop_after_interactions is not None:
        if type(stop_after_interactions) is not int or stop_after_interactions <= 0 or stop_after_interactions >= target:
            raise ValueError("stop_after_interactions must be a positive test-only prefix below the frozen target")
        target = stop_after_interactions
        evaluate_validation = False
    if output_root is None and target == int(job["environment_interactions"]) and evaluate_validation is not True:
        raise ValueError("canonical formal execution requires validation evaluation")
    checkpoint_records = _existing_checkpoint_records(paths)
    lease = ledger.acquire(identity, worker_id=worker_id)
    attempt_root = paths.attempts / f"attempt-{lease.attempt:06d}"
    attempt_root.mkdir(parents=True, exist_ok=True)
    paths.checkpoints.mkdir(parents=True, exist_ok=True)
    try:
        if resume_checkpoint is None:
            random.seed(int(job["training_seed"]))
            np.random.seed(int(job["training_seed"]))
            torch.manual_seed(int(job["training_seed"]))
            algorithm = build_algorithm(str(job["method"]), contract, device, candidate_id=str(job["candidate_id"]), scale=str(job["scale"]))
            environment = build_development_environment(repository_root, scenario_id=TRAINING_SCENARIOS[0], scale=str(job["scale"]), condition_id=str(job["condition_id"]))
            current_view = environment.reset(scenario_id=TRAINING_SCENARIOS[0])
            scenario_cursor = 0
            episode_interactions = 0
            episode_reward = 0.0
            update_count = 0
            executed_scenarios: list[int] = []
            start_interactions = 0
            fresh_since_update = 0
        else:
            checkpoint_path = Path(resume_checkpoint).resolve()
            if not checkpoint_path.is_relative_to(paths.checkpoints.resolve()) or checkpoint_path.parent != paths.checkpoints.resolve():
                raise ValueError("formal resume checkpoint is outside the job checkpoint directory")
            if not checkpoint_path.is_file():
                raise ValueError("formal resume checkpoint is missing")
            latest = _latest_checkpoint(paths)
            if latest is None or checkpoint_path != latest:
                raise ValueError("formal resume checkpoint is not the latest checkpoint")
            payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            formal_state = payload.get("state", {}).get("formal_state") if isinstance(payload, Mapping) else None
            if not isinstance(formal_state, Mapping):
                raise ValueError("formal checkpoint continuation state is missing")
            saved_environment = formal_state.get("environment")
            if not isinstance(saved_environment, Mapping):
                raise ValueError("formal checkpoint environment state is missing")
            saved_scenario_id = int(saved_environment.get("scenario_id", TRAINING_SCENARIOS[0]))
            if saved_scenario_id not in TRAINING_SCENARIOS:
                raise ValueError("formal checkpoint scenario is outside the training panel")
            environment = build_development_environment(repository_root, scenario_id=saved_scenario_id, scale=str(job["scale"]), condition_id=str(job["condition_id"]))
            algorithm, formal_state, _ = _restore_checkpoint(checkpoint_path, job, contract, device, environment)
            current_view = environment._current_view
            if current_view is None:
                current_view = environment._make_view()
            scenario_cursor = int(formal_state["scenario_cursor"])
            episode_interactions = int(formal_state["episode_interactions"])
            episode_reward = float(formal_state["episode_reward"])
            update_count = int(formal_state["update_count"])
            executed_scenarios = [int(value) for value in formal_state["executed_scenarios"]]
            fresh_since_update = int(formal_state.get("fresh_since_update", 0))
            start_interactions = int(formal_state["interaction_count"])
        _, update_interval = _update_interval(algorithm)
        for offset in range(target - start_interactions):
            interaction_index = start_interactions + offset
            scenario_id = int(current_view["scenario_id"])
            if not executed_scenarios or executed_scenarios[-1] != scenario_id:
                executed_scenarios.append(scenario_id)
            started = time.perf_counter()
            details = algorithm.act(current_view["observations"], current_view["masks"], deterministic=False, return_details=True)
            next_view = environment.step(_as_action_result(details), decision_runtime_s=time.perf_counter() - started)
            reward = float(next_view["team_reward"])
            envelope = build_physical_envelope(algorithm, current_view, next_view, details, team_reward=reward, transition_index=interaction_index, vehicle_trainable=execution.vehicle_trainable)
            _observe_physical_algorithm(algorithm, envelope, vehicle_trainable=execution.vehicle_trainable)
            fresh_since_update += 1
            episode_interactions += 1
            episode_reward += reward
            if fresh_since_update == update_interval:
                metrics = _update_physical_algorithm(algorithm, vehicle_trainable=execution.vehicle_trainable)
                if any(not math.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float, np.number))):
                    raise RuntimeError("formal update emitted NaN or Inf")
                update_count += 1
                fresh_since_update = 0
            append_jsonl(paths.training_events, {"schema_version": "g6-training-event-v1", "identity": identity, "interaction_count": interaction_index + 1, "update_count": update_count, "scenario_id": scenario_id, "team_reward": reward, "utc_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
            current_view = next_view
            if next_view["truncated"] and interaction_index + 1 < target:
                scenario_cursor = (scenario_cursor + 1) % len(TRAINING_SCENARIOS)
                environment = build_development_environment(repository_root, scenario_id=TRAINING_SCENARIOS[scenario_cursor], scale=str(job["scale"]), condition_id=str(job["condition_id"]))
                current_view = environment.reset(scenario_id=TRAINING_SCENARIOS[scenario_cursor])
                episode_interactions = 0
                episode_reward = 0.0
            if (interaction_index + 1) % int(job["checkpoint_interval"]) == 0 or interaction_index + 1 == target:
                checkpoint, checkpoint_hash = _write_checkpoint(paths, job, contract, algorithm, environment, interaction_count=interaction_index + 1, update_count=update_count, scenario_cursor=scenario_cursor, episode_interactions=episode_interactions, episode_reward=episode_reward, fresh_since_update=fresh_since_update, executed_scenarios=executed_scenarios)
                entry = {"path": str(checkpoint.relative_to(paths.root)), "sha256": checkpoint_hash, "bytes": checkpoint.stat().st_size, "interaction_count": interaction_index + 1, "validation_rows": 0}
                if evaluate_validation and (interaction_index + 1) % int(job["checkpoint_interval"]) == 0:
                    rows = evaluate_formal_checkpoint(repository_root, job, checkpoint, device=device, output_path=paths.validation_events)
                    entry["validation_rows"] = len(rows)
                checkpoint_records.append(entry)
                checkpoint_records.sort(key=lambda item: item["interaction_count"])
        summary = {"schema_version": "g6-formal-summary-v1", "status": "completed" if target == int(job["environment_interactions"]) else "interrupted", "identity": identity, "method": job["method"], "condition_id": job["condition_id"], "scale": job["scale"], "training_seed": job["training_seed"], "interactions": target, "target_interactions": int(job["environment_interactions"]), "checkpoint_count": len(checkpoint_records), "checkpoints": checkpoint_records, "validation_accessed": bool(evaluate_validation and checkpoint_records), "sealed_accessed": False, "battery_replenishment_enabled": False, "replenished_resource": "pesticide", "ecology_id": "dynamic_pest_v1", "source_commit": job["git_commit"], "source_scope_sha256": job["source_scope_sha256"], "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        if summary["status"] == "completed" and paths.validation_events.is_file():
            validation_rows = [json.loads(line) for line in paths.validation_events.read_text(encoding="utf-8").splitlines() if line.strip()]
            selected = select_frozen_checkpoint(validation_rows, expected_scenarios=VALIDATION_SCENARIOS)
            atomic_write_bytes(paths.selected_checkpoint, _json_bytes(selected))
            summary["selected_checkpoint"] = selected
            atomic_write_bytes(paths.summary, _json_bytes(summary))
        atomic_write_bytes(paths.summary, _json_bytes(summary))
        manifest = {"schema_version": "g6-formal-manifest-v1", "status": summary["status"], "identity": identity, "job": dict(job), "artifacts": [{"path": str(path.relative_to(paths.root)), "sha256": artifact_sha256(path), "bytes": path.stat().st_size} for path in (paths.training_events, paths.validation_events, paths.summary, paths.selected_checkpoint) if path.is_file()], "checkpoints": checkpoint_records, "validation_accessed": summary["validation_accessed"], "sealed_accessed": False, "battery_replenishment_enabled": False}
        atomic_write_bytes(paths.manifest, _json_bytes(manifest))
        hashes = {item["path"]: item["sha256"] for item in manifest["artifacts"] + manifest["checkpoints"]}
        if summary["status"] == "completed":
            ledger.complete(identity, lease_id=lease.lease_id, worker_id=worker_id, artifact_hashes=hashes)
        else:
            ledger.fail(identity, lease_id=lease.lease_id, worker_id=worker_id, reason="controlled interruption", artifact_hashes=hashes)
        return summary
    except Exception as exc:
        try:
            ledger.fail(identity, lease_id=lease.lease_id, worker_id=worker_id, reason=f"{type(exc).__name__}: {exc}")
        except LedgerError:
            pass
        raise


def resume_formal_job(root: Path | str, job: Mapping[str, Any], *, device: str = "cpu", output_root: Path | str | None = None, evaluate_validation: bool = True) -> dict[str, Any]:
    """Resume the latest failed/interrupted attempt using the same identity."""

    repository_root = Path(root).resolve()
    _validate_job(repository_root, job)
    paths = formal_job_paths(repository_root, job, output_root=output_root)
    latest = _latest_checkpoint(paths)
    if latest is None:
        raise ValueError("no formal checkpoint is available for recovery")
    ledger = AppendOnlyLedger(paths.ledger)
    identity = str(job["canonical_training_identity"])
    current = ledger.current(identity)
    if current.state is JobState.COMPLETED:
        return _load_json(paths.summary, "completed formal summary")
    if current.state is JobState.RUNNING:
        if current.lease is not None and float(current.lease.expires_at) > time.time():
            raise LedgerError("formal job still has an active lease")
        ledger.mark_stale(identity, reason="expired formal worker lease")
        raise LedgerError("expired formal job is stale and requires a replacement identity")
    if current.state is not JobState.FAILED:
        raise LedgerError(f"formal job is {current.state.value}, cannot resume")
    # Resume is intentionally implemented through the same executor after the
    # identity is retried; the checkpoint's RNG and environment state remain
    # the sole source of continuation state.
    ledger.requeue(identity, input_hash=_stable_hash(dict(job)), config_hash=str(job["config_hash"]), protocol_hash=str(job["protocol_hash"]), source_commit=str(job["git_commit"]), checkpoint_hash=None, scenario_panel_hash=str(job["validation_scenario_panel_hash"]))
    return run_formal_job(
        repository_root,
        job,
        device=device,
        output_root=output_root,
        evaluate_validation=evaluate_validation,
        resume_checkpoint=latest,
    )


__all__ = [
    "DYNAMIC_G6_RELATIVE", "FormalJobPaths", "evaluate_formal_checkpoint", "formal_job_paths",
    "load_frozen_job", "resume_formal_job", "run_formal_job",
]
