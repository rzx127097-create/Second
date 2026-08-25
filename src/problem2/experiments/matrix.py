from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping

from .families import (
    FAMILY_DEFINITIONS, FORMAL_SEEDS, HEURISTIC_CONDITIONS, LEARNING_METHODS,
    REQUIRED_CONDITIONS, SCALES,
)
from .identity import canonical_training_identity, experiment_identity
from .sensitivity import SENSITIVITY_AXES


@dataclass(frozen=True)
class TrainingJob:
    method: str
    scale: str
    training_seed: int
    config_hash: str
    git_commit: str
    family: str
    condition_id: str
    protocol_hash: str
    canonical_training_identity: str
    identity: str
    ablation_group: str | None = None
    sensitivity_axis: str | None = None
    sensitivity_value: float | None = None


@dataclass(frozen=True)
class ExperimentReference:
    family: str
    condition_id: str
    experiment_identity: str
    canonical_training_identity: str
    job: TrainingJob


@dataclass(frozen=True)
class TrainingGraph:
    unique_jobs: tuple[TrainingJob, ...]
    references: tuple[ExperimentReference, ...]
    source_commit: str
    protocol_hash: str
    registry_hashes: Mapping[str, str]

    @property
    def jobs(self) -> tuple[TrainingJob, ...]:
        return self.unique_jobs

    @property
    def family_counts(self) -> dict[str, int]:
        return {
            family: sum(job.family == family for job in self.unique_jobs)
            for family in FAMILY_DEFINITIONS
        }

    def assert_safe_deduplication(self, left: TrainingJob, right: TrainingJob) -> None:
        for job in (left, right):
            expected = canonical_training_identity(job.method, job.scale, job.training_seed, job.config_hash, job.git_commit)
            if expected != job.canonical_training_identity:
                raise ValueError("deduplication rejects tampered canonical identity")
        fields = ("method", "scale", "training_seed", "config_hash", "git_commit")
        if any(getattr(left, field) != getattr(right, field) for field in fields):
            raise ValueError("deduplication requires exact canonical identity")
        if left.protocol_hash != right.protocol_hash:
            raise ValueError("deduplication requires exact checkpoint-selection protocol")


def _stable_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_commit(root: Path) -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root,
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        dirty = [
            line for line in status.stdout.splitlines()
            if "outputs/problem2_sr_mappo_v1/g5/manifests/" not in line
        ]
        if dirty:
            raise RuntimeError("source tree is dirty; frozen provenance cannot be generated")
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Git is unavailable; frozen provenance cannot be generated") from exc
    commit = result.stdout.strip()
    if not commit or any(char not in "0123456789abcdef" for char in commit.lower()):
        raise RuntimeError("Git returned an invalid source commit")
    return commit


def _config_hash(method: str, condition: str, registry_hashes: Mapping[str, str], *, extra: Mapping[str, object] | None = None) -> str:
    return _stable_hash({"method": method, "condition_id": condition, "extra": dict(extra or {}), "registry_hashes": dict(sorted(registry_hashes.items()))})


def _new_job(
    *, root: Path, protocol_hash: str, registry_hashes: Mapping[str, str], git_commit: str, family: str,
    condition_id: str, method: str, scale: str, seed: int,
    extra: Mapping[str, object] | None = None,
) -> TrainingJob:
    config_hash = _config_hash(method, condition_id, registry_hashes, extra=extra)
    canonical = canonical_training_identity(method, scale, seed, config_hash, git_commit)
    return TrainingJob(
        method=method, scale=scale, training_seed=seed, config_hash=config_hash,
        git_commit=git_commit, family=family, condition_id=condition_id,
        protocol_hash=protocol_hash, canonical_training_identity=canonical,
        identity=experiment_identity(family, condition_id, protocol_hash, canonical),
        ablation_group=extra.get("ablation_group") if extra else None,
        sensitivity_axis=extra.get("sensitivity_axis") if extra else None,
        sensitivity_value=extra.get("sensitivity_value") if extra else None,
    )


def build_training_graph(contract) -> TrainingGraph:
    """Expand the frozen family registry and deduplicate only exact base jobs."""
    root = Path(contract.source_root)
    protocol_hash = contract.file_hashes["configs/problem2/g5/protocol.yaml"]
    git_commit = _git_commit(root)
    registry_hashes = {
        path: contract.file_hashes[path]
        for path in (
            "configs/problem2/g5/families.yaml",
            "configs/problem2/g5/ablations.yaml",
            "configs/problem2/g5/sensitivity.yaml",
        )
    }
    jobs: list[TrainingJob] = []
    by_base: dict[str, TrainingJob] = {}
    references: list[ExperimentReference] = []

    def add_job(family: str, condition: str, method: str, scale: str, seed: int, extra=None) -> TrainingJob:
        candidate = _new_job(
            root=root, protocol_hash=protocol_hash, registry_hashes=registry_hashes, git_commit=git_commit,
            family=family, condition_id=condition, method=method, scale=scale,
            seed=seed, extra=extra,
        )
        existing = by_base.get(candidate.canonical_training_identity)
        if existing is None:
            by_base[candidate.canonical_training_identity] = candidate
            jobs.append(candidate)
            return candidate
        return existing

    def ref(family: str, condition: str, job: TrainingJob) -> None:
        references.append(ExperimentReference(
            family=family, condition_id=condition,
            experiment_identity=experiment_identity(family, condition, protocol_hash, job.canonical_training_identity),
            canonical_training_identity=job.canonical_training_identity, job=job,
        ))

    base: dict[tuple[str, str, int], TrainingJob] = {}
    for method in LEARNING_METHODS:
        for scale in SCALES:
            for seed in FORMAL_SEEDS:
                base[(method, scale, seed)] = add_job("algorithm_scale", method, method, scale, seed)
    # Convergence references the same base jobs.
    for method in LEARNING_METHODS:
        for scale in SCALES:
            for seed in FORMAL_SEEDS:
                ref("algorithm_convergence", method, base[(method, scale, seed)])
                ref("algorithm_scale", method, base[(method, scale, seed)])

    required: dict[tuple[str, str, int], TrainingJob] = {}
    for condition in REQUIRED_CONDITIONS:
        for scale in SCALES:
            for seed in FORMAL_SEEDS:
                if condition in ("sr_mappo_mobile", "mappo_mobile"):
                    job = base[(condition, scale, seed)]
                elif condition in ("sr_mappo_fixed", "sr_mappo_astar", "sr_mappo_two_stage"):
                    job = add_job("problem2_required", condition, "sr_mappo_mobile", scale, seed)
                else:
                    raise AssertionError(condition)
                required[(condition, scale, seed)] = job
                ref("problem2_required", condition, job)

    for condition in HEURISTIC_CONDITIONS:
        for scale in SCALES:
            for seed in FORMAL_SEEDS:
                job = add_job("vehicle_heuristics", condition, "sr_mappo_mobile", scale, seed)
                ref("vehicle_heuristics", condition, job)
    for scale in SCALES:
        for seed in FORMAL_SEEDS:
            ref("vehicle_heuristics", "sr_mappo_mobile", base[("sr_mappo_mobile", scale, seed)])

    ablation_ids = (
        "no_observation_normalization", "no_return_normalization",
        "no_network_stabilization", "no_robust_value_update", "no_learning_rate_decay",
    )
    for condition in ablation_ids:
        for seed in FORMAL_SEEDS:
            job = add_job(
                "sr_mappo_ablation", condition, "sr_mappo_mobile", "g30x30_d3", seed,
                {"ablation_group": condition},
            )
            ref("sr_mappo_ablation", condition, job)
    for seed in FORMAL_SEEDS:
        ref("sr_mappo_ablation", "sr_mappo_mobile", base[("sr_mappo_mobile", "g30x30_d3", seed)])

    for axis, levels in SENSITIVITY_AXES.items():
        center = levels[1]
        for value in (levels[0], levels[2]):
            condition = f"sr_mappo_mobile__{axis}__{value:g}"
            for seed in FORMAL_SEEDS:
                job = add_job(
                    "sr_mappo_sensitivity", condition, "sr_mappo_mobile", "g30x30_d3", seed,
                    {"sensitivity_axis": axis, "sensitivity_value": value},
                )
                ref("sr_mappo_sensitivity", condition, job)
        for seed in FORMAL_SEEDS:
            ref("sr_mappo_sensitivity", "sr_mappo_mobile", base[("sr_mappo_mobile", "g30x30_d3", seed)])

    graph = TrainingGraph(
        unique_jobs=tuple(jobs), references=tuple(references), source_commit=git_commit,
        protocol_hash=protocol_hash, registry_hashes=registry_hashes,
    )
    if len(graph.unique_jobs) != 375:
        raise ValueError(f"frozen training graph must contain 375 jobs, got {len(graph.unique_jobs)}")
    return graph


__all__ = ["TrainingJob", "ExperimentReference", "TrainingGraph", "build_training_graph"]
