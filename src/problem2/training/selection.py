"""Mechanical candidate selection and G6/G7 identity-plan construction."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence


DYNAMIC_ECOLOGY_ID = "dynamic_pest_v1"
DYNAMIC_OUTPUT_ROOT = "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6"
_DEFAULT_STORAGE_BYTES_PER_JOB = 8 * 1024 * 1024
_ATOMIC_STORAGE_HEADROOM_BYTES = 64 * 1024 * 1024
_GPU_HOURS_PER_JOB = 0.25
_EVALUATOR_HASH = hashlib.sha256(b"problem2-deterministic-evaluator-v2").hexdigest()


def _sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"{label} must be a SHA-256 hash")
    return value.lower()


def _require_commit(value: object) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError("source commit must be a 40-character Git commit")
    return value.lower()


def select_candidates(
    rows: Iterable[Mapping[str, Any]],
    *,
    require_complete: bool = False,
    expected_cell_count: int = 3000,
    candidate_manifest_sha256: str | None = None,
    budget_manifest_sha256: str | None = None,
    physical_scenario_contract_sha256: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Select one row per method using the pre-registered total ordering."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, source in enumerate(rows):
        if not isinstance(source, Mapping):
            raise ValueError(f"candidate result {index} must be a mapping")
        row = dict(source)
        method = row.get("method")
        candidate_id = row.get("candidate_id")
        if not isinstance(method, str) or not method or not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate result identity is incomplete")
        _require_sha256(row.get("config_hash"), "configuration hash")
        for field in ("mean_validation_reduction_rate", "success_probability"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"{field} must be finite")
        interactions = row.get("interaction_count")
        if isinstance(interactions, bool) or not isinstance(interactions, int) or interactions <= 0:
            raise ValueError("interaction_count must be a positive integer")
        grouped[method].append(row)
    if not grouped:
        raise ValueError("candidate results are empty")
    if require_complete:
        if expected_cell_count != 3000:
            raise ValueError("canonical validation selection requires exactly 3000 cells")
        if set(grouped) != {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile"}:
            raise ValueError("canonical selection requires every frozen method")
        if sum(int(row.get("episode_count", -1)) for rows_for_method in grouped.values() for row in rows_for_method) != expected_cell_count:
            raise ValueError("selection requires complete 3000 validated cells")
        if any(len(rows_for_method) != 4 for rows_for_method in grouped.values()):
            raise ValueError("canonical selection requires exactly four candidates per method")
        if any(
            {str(row["candidate_id"]) for row in rows_for_method} != {"c01", "c02", "c03", "c04"}
            for rows_for_method in grouped.values()
        ):
            raise ValueError("canonical selection requires candidate IDs c01-c04")
        if any(
            row.get("episode_count") != 150
            for rows_for_method in grouped.values()
            for row in rows_for_method
        ):
            raise ValueError("canonical selection requires exactly 150 cells per candidate")
        provenance = {
            "candidate_manifest_sha256": _require_sha256(candidate_manifest_sha256, "candidate manifest hash"),
            "budget_manifest_sha256": _require_sha256(budget_manifest_sha256, "budget manifest hash"),
            "physical_scenario_contract_sha256": _require_sha256(physical_scenario_contract_sha256, "physical scenario contract hash"),
        }
    else:
        provenance = {}
    selected: dict[str, dict[str, Any]] = {}
    for method, candidates in grouped.items():
        identities = [str(item["candidate_id"]) for item in candidates]
        if len(identities) != len(set(identities)):
            raise ValueError(f"duplicate candidate result for {method}")
        selected[method] = min(
            candidates,
            key=lambda item: (
                -float(item["mean_validation_reduction_rate"]),
                -float(item["success_probability"]),
                int(item["interaction_count"]),
                str(item["config_hash"]),
            ),
        ) | provenance
    return selected


def build_formal_freeze_payloads(
    training_jobs: Sequence[Mapping[str, Any]],
    *,
    validation_scenario_ids: Iterable[int],
    validation_panel_hash: str,
    sealed_scenario_ids: Iterable[int],
    sealed_panel_hash: str,
    source_commit: str,
    protocol_hash: str,
    source_scope_sha256: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Build content-free formal identity plans and enforce the frozen counts."""

    validation_hash = _require_sha256(validation_panel_hash, "validation panel hash")
    sealed_hash = _require_sha256(sealed_panel_hash, "sealed panel hash")
    commit = _require_commit(source_commit)
    protocol = _require_sha256(protocol_hash, "protocol hash")
    validation_ids = tuple(validation_scenario_ids)
    sealed_ids = tuple(sealed_scenario_ids)
    if validation_ids != tuple(range(20000, 20050)):
        raise ValueError("validation identities must be 20000-20049")
    if sealed_ids != tuple(range(30000, 30100)):
        raise ValueError("sealed identities must be 30000-30099")
    jobs = [dict(job) for job in training_jobs]
    if len(jobs) != 375:
        raise ValueError(f"G6 must contain exactly 375 unique training jobs, got {len(jobs)}")
    canonical = [job.get("canonical_training_identity") for job in jobs]
    if len(set(canonical)) != 375 or any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in canonical
    ):
        raise ValueError("G6 training identities must be 375 unique SHA-256 values")
    base_count = sum(job.get("family") == "algorithm_scale" for job in jobs)
    if base_count != 150:
        raise ValueError(f"G6 must contain exactly 150 base jobs, got {base_count}")
    for job in jobs:
        _require_sha256(job.get("config_hash"), "training configuration hash")

    scopes = {
        str(job["source_scope_sha256"])
        for job in jobs
        if isinstance(job.get("source_scope_sha256"), str)
    }
    if source_scope_sha256 is not None:
        source_scope = _require_sha256(source_scope_sha256, "source scope hash")
    elif len(scopes) == 1:
        source_scope = _require_sha256(next(iter(scopes)), "source scope hash")
    elif len(scopes) > 1:
        raise ValueError("training jobs must share one frozen source scope")
    else:
        source_scope = _sha256(sorted(str(value) for value in canonical))
    for job in jobs:
        declared_scope = job.get("source_scope_sha256")
        if declared_scope is not None and declared_scope != source_scope:
            raise ValueError("training job source scope differs from the frozen scope")
        declared_commit = job.get("git_commit")
        if declared_commit is not None and declared_commit != commit:
            raise ValueError("training job source commit differs from the frozen commit")
        job["source_scope_sha256"] = source_scope
        job["git_commit"] = commit
        job.setdefault("ecology_id", DYNAMIC_ECOLOGY_ID)
        job.setdefault("output_root", DYNAMIC_OUTPUT_ROOT)

    mechanism_refs = tuple(
        _sha256({"kind": "mechanism_sensitivity", "axis": axis, "level": level, "seed_index": seed_index})
        for axis in range(5)
        for level in ("low", "high")
        for seed_index in range(5)
    )
    evaluation_sources = tuple(str(value) for value in canonical) + mechanism_refs
    expected_sealed = len(evaluation_sources) * len(sealed_ids)
    if expected_sealed != 42500:
        raise ValueError(f"G7 must contain exactly 42,500 evaluation identities, got {expected_sealed}")
    sealed_identity_hash = _sha256(
        [_sha256({"source": source, "scenario_id": scenario}) for source in evaluation_sources for scenario in sealed_ids]
    )
    provenance = {"source_commit": commit, "protocol_hash": protocol}
    scheduler_order = sorted(str(value) for value in canonical)
    expected_storage_bytes = len(jobs) * _DEFAULT_STORAGE_BYTES_PER_JOB
    expected_gpu_hours = len(jobs) * _GPU_HOURS_PER_JOB
    return {
        "g6_training": {
            "schema_version": "g5.v1",
            "status": "frozen_unexecuted",
            "partition": "formal_training",
            "base_job_count": base_count,
            "job_count": len(jobs),
            "jobs": jobs,
            "provenance": provenance,
            "source_scope_sha256": source_scope,
            "ecology_id": DYNAMIC_ECOLOGY_ID,
            "output_root": DYNAMIC_OUTPUT_ROOT,
            "scheduler_order": scheduler_order,
            "expected_storage_bytes": expected_storage_bytes,
            "expected_gpu_hours": expected_gpu_hours,
            "atomic_storage_headroom_bytes": _ATOMIC_STORAGE_HEADROOM_BYTES,
            "sealed_accessed": False,
        },
        "g6_validation": {
            "schema_version": "g5.v1",
            "status": "frozen_unexecuted",
            "partition": "validation",
            "scenario_ids": list(validation_ids),
            "scenario_panel_hash": validation_hash,
            "scenario_content": None,
            "evaluation_results": [],
            "expected_evaluation_count": len(jobs) * 20 * len(validation_ids),
            "checkpoint_selection": "frozen_g5_checkpoint_selection_rule",
            "deterministic_policy": True,
            "ecology_id": DYNAMIC_ECOLOGY_ID,
            "output_root": DYNAMIC_OUTPUT_ROOT,
            "evaluator_hash": _EVALUATOR_HASH,
            "source_scope_sha256": source_scope,
            "provenance": provenance,
            "sealed_accessed": False,
        },
        "g7_sealed": {
            "schema_version": "g5.v1",
            "status": "locked_unexecuted",
            "partition": "sealed_test",
            "scenario_ids": list(sealed_ids),
            "scenario_panel_hash": sealed_hash,
            "scenario_content": None,
            "evaluation_results": [],
            "evaluation_source_count": len(evaluation_sources),
            "expected_evaluation_count": expected_sealed,
            "evaluation_identity_set_hash": sealed_identity_hash,
            "evaluation_identity_template": {
                "source_identity": "selected_g6_training_identity_or_mechanism_sensitivity_identity",
                "scenario_id": "sealed_test_30000_30099",
                "checkpoint_hash": "bound_only_after_g6_selected_checkpoint",
                "evaluator_hash": "bound_only_at_g7_execution",
                "scenario_panel_hash": sealed_hash,
            },
            "provenance": provenance,
            "sealed_accessed": False,
            "actual_unlock_count": 0,
        },
    }


__all__ = ["build_formal_freeze_payloads", "select_candidates"]
