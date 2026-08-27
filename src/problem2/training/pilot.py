"""Development-only G5 pilot orchestration and validation-candidate freezing."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.g5_contract import (
    BudgetDecision,
    G5Contract,
    LEARNING_METHODS,
    PROBLEM2_CONDITIONS,
)

from .budget import aggregate_runtime
from .preflight import run_preflight
from .runner import ALL_CONDITION_TYPES, METHODS, run_training_job


PILOT_SCALES = ("g20x20_d2", "g30x50_d4")
PILOT_METHODS = METHODS
PILOT_CONDITIONS = ALL_CONDITION_TYPES
PILOT_TRAINING_SEEDS = (51001, 51002, 51003)
PILOT_SCENARIO_IDS = tuple(range(10000, 10020))
VALIDATION_SCENARIO_IDS = tuple(range(20000, 20050))


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
    jobs = tuple(
        PilotJob(method, condition, scale, seed, scenario)
        for scale in scales
        for seed in training_seeds
        for method in methods
        for condition in conditions
        for scenario in (scenario_ids[0],)
    )
    identities = [job.identity for job in jobs]
    if len(identities) != len(set(identities)):
        raise ValueError("pilot matrix contains duplicate identities")
    return jobs


def _paths_for_output(output_root: Path) -> tuple[Path, Path]:
    if output_root.name == "pilots":
        base = output_root.parent
    else:
        base = output_root
    return base / "validated" / "pilot-episodes.jsonl", base / "audits" / "pilot-audit.json"


def run_pilot_matrix(
    contract: G5Contract,
    output_root: Path | str,
    *,
    jobs: Sequence[PilotJob] | None = None,
    interactions: int = 128,
    device: str = "cpu",
    runner: Callable[[Mapping[str, Any], str, int, Path], Mapping[str, Any]] = run_training_job,
) -> dict[str, Any]:
    """Run or inject the development pilot path and persist descriptive records."""

    _contract_guard(contract)
    if isinstance(interactions, bool) or not isinstance(interactions, int) or interactions <= 0:
        raise ValueError("pilot interactions must be a positive integer")
    selected_jobs = tuple(jobs) if jobs is not None else build_pilot_matrix(contract)
    identities = [job.identity for job in selected_jobs]
    if len(identities) != len(set(identities)):
        raise ValueError("pilot jobs contain duplicate identities")
    if any(job.partition != "development" for job in selected_jobs):
        raise ValueError("pilot jobs must use the development partition")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    episodes_path, audit_path = _paths_for_output(root)
    preflight = run_preflight(device, contract.source_root)
    if preflight.get("status") != "pass":
        raise ValueError(preflight.get("reason", "pilot device preflight failed"))
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
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
                if result.get(field) is not False:
                    raise ValueError(f"pilot runner did not prove {field}=false")
            if result.get("partition", "development") != "development":
                raise ValueError("pilot runner returned a non-development partition")
            for episode_index, scenario_id in enumerate(job.scenario_ids):
                record = {
                    "schema_version": "g5-pilot-episode-v1",
                    "data_status": "development_pilot_descriptive",
                    "pilot_job_identity": job.identity,
                    "episode_index": episode_index,
                    "method": job.method,
                    "algorithm_id": result.get("algorithm_id", job.method),
                    "condition_id": job.condition_id,
                    "scale": job.scale,
                    "training_seed": job.training_seed,
                    "scenario_id": scenario_id,
                    "partition": "development",
                    "interactions": int(result.get("interactions", interactions)),
                    "elapsed_seconds": elapsed,
                    "seconds_per_interaction": elapsed / max(int(result.get("interactions", interactions)), 1),
                    "finite_metrics": bool(result.get("finite_metrics", True)),
                    "evaluation_frozen": bool(result.get("evaluation_frozen", True)),
                    "training_result": result,
                    "validation_accessed": False,
                    "sealed_accessed": False,
                    "battery_replenishment_enabled": False,
                }
                records.append(record)
            runtime_rows.append({
                "method_id": job.method,
                "scale_id": job.scale,
                "interactions": record["interactions"],
                "elapsed_seconds": record["elapsed_seconds"],
            })
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
    audit: dict[str, Any] = {
        "schema_version": "g5-pilot-audit-v1",
        "status": "pass" if not failures and len(runtime_rows) == len(selected_jobs) and len(records) == len(selected_jobs) * len(PILOT_SCENARIO_IDS) else "fail",
        "maturity": "M2",
        "data_status": "development_pilot_descriptive",
        "job_count": len(selected_jobs),
        "episode_count": len(records),
        "training_job_count": len(selected_jobs),
        "coverage": coverage,
        "runtime_aggregates": aggregate_runtime(runtime_rows) if runtime_rows else {},
        "failures": failures,
        "validation_accessed": False,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
        "formal_training_performed": False,
        "episodes_path": str(episodes_path),
    }
    atomic_write_bytes(audit_path, (json.dumps(audit, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    return {**audit, "episodes_path": str(episodes_path), "audit_path": str(audit_path)}


def _candidate_payload(contract: G5Contract, decision: BudgetDecision) -> dict[str, Any]:
    if decision.selected_budget <= 0 or decision.checkpoint_interval <= 0 or decision.checkpoint_count < 20:
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
) -> dict[str, Any]:
    """Freeze four hashed candidates per method before any validation access."""

    _contract_guard(contract)
    path = Path(output_path).resolve()
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
        stable_keys = ("manifest_id", "candidates", "equal_environment_interactions", "checkpoint_interval", "scenario_panel", "selection_rule")
        if any(existing.get(key) != payload.get(key) for key in stable_keys):
            raise ValueError("candidate manifest drift before validation")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    return payload


__all__ = [
    "PILOT_CONDITIONS",
    "PILOT_METHODS",
    "PILOT_SCALES",
    "PilotJob",
    "build_pilot_matrix",
    "freeze_validation_candidates",
    "run_pilot_matrix",
]
