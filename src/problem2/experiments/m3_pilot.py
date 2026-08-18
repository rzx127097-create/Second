"""Frozen canonical selection for the controlled-simulation M3 pilot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .orchestrator import Chapter45Orchestrator, select_jobs


@dataclass(frozen=True)
class M3PilotProfile:
    version: int = 1
    family: str = "main_comparison"
    execution_profile: str = "simulation"
    scales: tuple[str, ...] = ("s1", "s6")
    methods: tuple[str, ...] = (
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    )
    training_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    split: str = "validation"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text.lower())


def _semantic_payload(manifest: Mapping[str, object]) -> dict[str, object]:
    return {
        str(key): value
        for key, value in manifest.items()
        if key not in {"created_at", "semantic_sha256"}
    }


def _semantic_sha256(manifest: Mapping[str, object]) -> str:
    payload = json.dumps(
        _semantic_payload(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_resource_report(
    path: Path,
    orchestrator: Chapter45Orchestrator,
) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"resource activation report does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"resource activation report is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("resource activation report must be a JSON object")
    if payload.get("activated") is not True:
        raise ValueError("resource activation report must have activated=true")
    if payload.get("diagnosis") != "resource_service_chain_activated":
        raise ValueError("resource activation diagnosis must be resource_service_chain_activated")
    if payload.get("config_hash") != orchestrator.config_hash:
        raise ValueError("resource activation config hash does not match the M3 configuration")
    if payload.get("git_commit") != orchestrator.git_provenance.commit:
        raise ValueError("resource activation Git commit does not match the M3 source")
    if payload.get("source_tree_hash") != orchestrator.git_provenance.source_tree_hash:
        raise ValueError("resource activation source-tree hash does not match the M3 source")
    if not _is_sha256(payload.get("simulation_profile_sha256")):
        raise ValueError("resource activation simulation profile must have a SHA-256 identity")
    record_count = payload.get("record_count")
    if type(record_count) is not int or int(record_count) < 1:
        raise ValueError("resource activation record_count must be a positive integer")
    return payload


def _validation_scenarios(
    orchestrator: Chapter45Orchestrator,
    profile: M3PilotProfile,
) -> dict[str, tuple[str, ...]]:
    declared = tuple(
        str(value) for value in orchestrator.config.experiments["validation_scenarios"]
    )
    result: dict[str, tuple[str, ...]] = {}
    for scale in profile.scales:
        scenarios = tuple(
            scenario_id
            for scenario_id in declared
            if str(orchestrator.config.scenarios[scenario_id]["scale"]) == scale
            and str(orchestrator.config.scenarios[scenario_id]["split"]) == profile.split
        )
        if len(scenarios) != 2:
            raise ValueError(
                f"M3 requires exactly two validation scenarios for {scale}; found {len(scenarios)}"
            )
        result[scale] = scenarios
    return result


def build_m3_manifest(
    orchestrator: Chapter45Orchestrator,
    *,
    resource_report_path: str | Path,
    created_at: str | None = None,
) -> dict[str, object]:
    """Build, but do not persist, the immutable M3 pilot selection."""

    profile = M3PilotProfile()
    provenance = orchestrator.git_provenance
    if provenance.dirty:
        raise ValueError("M3 manifest preparation requires a clean Git worktree")
    if tuple(orchestrator.spec.main_methods) != profile.methods:
        raise ValueError("M3 methods do not match the registered Chapter 4.5 protocol")
    if tuple(orchestrator.spec.training_seeds) != profile.training_seeds:
        raise ValueError("M3 training seeds do not match the registered Chapter 4.5 protocol")
    if not set(profile.scales) <= set(orchestrator.spec.scales):
        raise ValueError("M3 scales are not registered in the Chapter 4.5 protocol")

    resource_path = Path(resource_report_path).resolve()
    resource = _load_resource_report(resource_path, orchestrator)
    scenarios_by_scale = _validation_scenarios(orchestrator, profile)
    family_jobs = orchestrator.plan(
        profile.family,
        execution_profile=profile.execution_profile,
    )
    selected = select_jobs(
        family_jobs,
        scales=profile.scales,
        methods=profile.methods,
        seeds=profile.training_seeds,
    )
    if len(selected) != 50:
        raise ValueError(f"M3 canonical selection must contain 50 jobs; found {len(selected)}")
    target_updates = int(orchestrator.config.algorithm["total_updates"])
    if any(
        job.identity.execution_profile != profile.execution_profile
        or job.identity.target_updates != target_updates
        or job.identity.condition_id == "direct"
        for job in selected
    ):
        raise ValueError("M3 selected jobs do not have canonical full-budget identities")

    jobs: list[dict[str, object]] = []
    evaluations: list[dict[str, object]] = []
    for planned in selected:
        identity = planned.identity
        jobs.append({
            **identity.to_dict(),
            "job_id": identity.job_id,
            "intervention_hash": planned.intervention.identity_hash,
            "job_record_path": f"jobs/{identity.job_id}.json",
            "checkpoint_path": f"checkpoints/{identity.job_id}.pt",
        })
        for scenario_id in scenarios_by_scale[identity.scale]:
            evaluations.append({
                "job_id": identity.job_id,
                "method": identity.method,
                "scale": identity.scale,
                "training_seed": identity.training_seed,
                "family": identity.family,
                "condition_id": identity.condition_id,
                "scenario_id": scenario_id,
                "split": profile.split,
                "run_id": f"{identity.job_id}:0:{scenario_id}",
                "raw_path": f"raw/evaluation-{identity.job_id}-{scenario_id}.jsonl",
            })
    if len(evaluations) != 100:
        raise ValueError(
            f"M3 canonical selection must contain 100 evaluations; found {len(evaluations)}"
        )

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    manifest: dict[str, object] = {
        "schema_version": 1,
        "created_at": str(timestamp),
        "profile": {
            "version": profile.version,
            "family": profile.family,
            "execution_profile": profile.execution_profile,
            "scales": list(profile.scales),
            "methods": list(profile.methods),
            "training_seeds": list(profile.training_seeds),
            "split": profile.split,
            "target_updates": target_updates,
            "checkpoint_selection_rule": str(
                orchestrator.spec.execution["checkpoint_selection_rule"]
            ),
            "scenarios_by_scale": {
                scale: list(scenarios) for scale, scenarios in scenarios_by_scale.items()
            },
        },
        "identity": {
            "config_dir": str(orchestrator.config_dir.resolve()),
            "config_hash": orchestrator.config_hash,
            "protocol_path": str(orchestrator.protocol_path.resolve()),
            "protocol_hash": orchestrator.protocol_hash,
            "git_commit": provenance.commit,
            "source_tree_hash": provenance.source_tree_hash,
            "git_dirty": False,
            "output_root": str(orchestrator.output_root.resolve()),
        },
        "resource_activation": {
            "path": str(resource_path),
            "sha256": _sha256(resource_path),
            "activated": True,
            "diagnosis": str(resource["diagnosis"]),
            "record_count": int(resource["record_count"]),
            "config_hash": str(resource["config_hash"]),
            "git_commit": str(resource["git_commit"]),
            "source_tree_hash": str(resource["source_tree_hash"]),
            "simulation_profile_sha256": str(resource["simulation_profile_sha256"]),
            "provisional": bool(resource.get("provisional", True)),
        },
        "counts": {"jobs": len(jobs), "evaluations": len(evaluations)},
        "jobs": jobs,
        "evaluations": evaluations,
    }
    manifest["semantic_sha256"] = _semantic_sha256(manifest)
    return manifest


def load_m3_manifest(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"M3 manifest does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"M3 manifest is invalid JSON: {source}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported M3 manifest schema")
    observed = payload.get("semantic_sha256")
    expected = _semantic_sha256(payload)
    if observed != expected:
        raise ValueError("M3 manifest semantic SHA-256 mismatch")
    return payload


def write_m3_manifest(
    path: str | Path,
    manifest: Mapping[str, object],
) -> tuple[Path, bool]:
    target = Path(path)
    if manifest.get("schema_version") != 1 or manifest.get("semantic_sha256") != _semantic_sha256(manifest):
        raise ValueError("cannot write an invalid M3 manifest")
    if target.is_file():
        existing = load_m3_manifest(target)
        if existing["semantic_sha256"] == manifest["semantic_sha256"]:
            return target, True
        raise ValueError(f"conflicting M3 manifest already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            dict(manifest),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return target, False


__all__ = [
    "M3PilotProfile",
    "build_m3_manifest",
    "load_m3_manifest",
    "write_m3_manifest",
]
