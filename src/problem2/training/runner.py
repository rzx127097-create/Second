"""Bounded, deterministic G5 development smoke runner.

This adapter exercises the shared algorithm collection/update/checkpoint path only
on development identities. It is deliberately not a pilot or evaluation runner.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import random
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_checkpoint, save_checkpoint
from problem2.algorithms.protocol import ActionResult, OffPolicyEnvelope, OnPolicyEnvelope, RoleBatch
from problem2.experiments.artifacts import artifact_sha256, atomic_write_bytes, append_jsonl
from problem2.experiments.g5_contract import load_g5_contract

from .preflight import run_preflight


METHODS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile")
ABLATION_CONDITIONS = ("no_observation_normalization", "no_return_normalization", "no_network_stabilization", "no_robust_value_update", "no_learning_rate_decay")
SENSITIVITY_CONDITIONS = ("learning_rate", "clip_range", "entropy_coef", "gamma", "gae_lambda")
ON_POLICY = {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile"}
ROLE_SHAPES = {"uav": (2, 179), "vehicle": (1, 28)}
MASK_SHAPES = {"uav": (2, 6), "vehicle": (1, 5)}
ALL_CONDITION_TYPES = ("sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage", "sr_mappo_nearest", "sr_mappo_urgency", *ABLATION_CONDITIONS, *SENSITIVITY_CONDITIONS)


def _hash_text(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _provenance(contract, condition: str) -> dict[str, str]:
    root = contract.source_root
    try:
        import subprocess
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception as error:
        raise RuntimeError("cannot resolve source commit for smoke provenance") from error
    source_payload = json.dumps(dict(sorted(contract.file_hashes.items())), sort_keys=True, separators=(",", ":"))
    source = hashlib.sha256(source_payload.encode("ascii")).hexdigest()
    config = contract.file_hashes["configs/problem2/g5/methods.yaml"]
    protocol = contract.file_hashes["docs/evidence/g5/heterogeneous_interface.yaml"]
    ancestry = _hash_text(condition, 64)
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.lower()):
        raise RuntimeError("Git returned an invalid source commit for smoke provenance")
    return {"source_commit": commit, "source_bundle_sha256": source, "config_hash": config, "protocol_hash": protocol, "ancestry_hash": ancestry}


def _observations(index: int) -> dict[str, np.ndarray]:
    base = np.float32(index * 0.001)
    return {"uav": np.full(ROLE_SHAPES["uav"], base, dtype=np.float32), "vehicle": np.full(ROLE_SHAPES["vehicle"], base + 0.1, dtype=np.float32)}


def _masks() -> dict[str, np.ndarray]:
    return {"uav": np.ones(MASK_SHAPES["uav"], dtype=bool), "vehicle": np.asarray([[True, True, False, False, False]], dtype=bool)}


def _envelope(
    algorithm,
    current: dict[str, np.ndarray],
    nxt: dict[str, np.ndarray],
    index: int,
    details: Mapping[str, Any],
    *,
    scenario_id: int = 10000,
):
    action_result = ActionResult(actions=details["actions"], masks=details["masks"])
    role_batch = RoleBatch.from_action_result(
        action_result,
        observations=current,
        rewards={role: np.full(current[role].shape[0], 0.1, dtype=np.float32) for role in current},
        next_observations=nxt,
        next_masks=_masks(),
        terminated=False,
        truncated=False,
        scenario_id=f"development-{scenario_id}",
        transition_id=f"development-{scenario_id}:{index}",
    )
    common = {
        "role_batch": role_batch,
        "policy_observations": details.get("policy_observations", current),
        "old_log_probs": details.get("log_probs", {"uav": [0.0, 0.0], "vehicle": [0.0]}),
        "valid_actor_sample": {"uav": np.ones(2, dtype=bool), "vehicle": np.ones(1, dtype=bool)},
        "agent_ids": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
        "candidate_mapping": {"vehicle": ["request-0", None, None, None]},
        "normalization_versions": details.get("normalization_versions", {}),
        "team_reward": 0.1,
        "valid_sample": True,
    }
    if algorithm.method_id == "ippo_mobile":
        values = details["values"]
        next_values = {role: algorithm.local_value(role, nxt[role]).detach().cpu().numpy() for role in algorithm.roles}
        return OnPolicyEnvelope(value_conditioning="local", values=values, next_values=next_values, **common)
    state = np.full(185, np.float32(index * 0.01), dtype=np.float32)
    next_state = np.full(185, np.float32((index + 1) * 0.01), dtype=np.float32)
    if algorithm.method_id in ON_POLICY:
        values = float(algorithm.value(state).detach().cpu().reshape(-1)[0])
        next_values = float(algorithm.value(next_state).detach().cpu().reshape(-1)[0])
        return OnPolicyEnvelope(value_conditioning="centralized", values=values, next_values=next_values, critic_state=state, next_critic_state=next_state, **common)
    return OffPolicyEnvelope(critic_state=state, next_critic_state=next_state, **{key: common[key] for key in ("role_batch", "team_reward", "valid_sample", "valid_actor_sample", "agent_ids", "candidate_mapping")})


def _algorithm_for_condition(condition: str) -> str:
    return condition if condition in METHODS else ("mappo_mobile" if condition == "mappo_mobile" else "sr_mappo_mobile")


def _write_manifest(root: Path, files: list[Path], result: Mapping[str, Any]) -> Path:
    manifest = {"schema_version": "g5-smoke-artifact-v1", "status": "pass", "maturity": "M2", "method": result["method"], "algorithm_id": result["algorithm_id"], "condition_id": result["condition_id"], "partition": result["partition"], "scenario_id": result["scenario_id"], "training_seed": result["training_seed"], "provenance": result["provenance"], "validation_accessed": False, "sealed_accessed": False, "battery_replenishment_enabled": False, "artifacts": [{"path": str(path.relative_to(root)), "sha256": artifact_sha256(path), "bytes": path.stat().st_size} for path in files]}
    path = root / "manifest.json"
    atomic_write_bytes(path, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    loaded = json.loads(path.read_text(encoding="utf-8"))
    for item in loaded["artifacts"]:
        artifact = root / item["path"]
        if artifact.resolve().parent != root.resolve() or artifact_sha256(artifact) != item["sha256"] or artifact.stat().st_size != item["bytes"]:
            raise RuntimeError("smoke artifact manifest verification failed")
    if loaded["method"] != result["method"] or loaded["algorithm_id"] != result["algorithm_id"] or loaded["condition_id"] != result["condition_id"]:
        raise RuntimeError("smoke artifact identity drift")
    return path


def _evaluation_snapshot(algorithm: Any) -> bytes:
    """Stable snapshot of policy/evaluation state, excluding replay bookkeeping."""
    payload: list[tuple[str, str, bytes]] = []
    for name, value in sorted(vars(algorithm).items()):
        if isinstance(value, torch.nn.Module):
            for key, tensor in sorted(value.state_dict().items()):
                payload.append((name, key, tensor.detach().cpu().numpy().tobytes()))
    payload.append(("training", "flag", str(bool(getattr(algorithm, "training", True))).encode()))
    if hasattr(algorithm, "exploration"):
        payload.append(("exploration", "value", repr(getattr(algorithm, "exploration")).encode()))
    return pickle.dumps(payload, protocol=5)


def _state_digest(algorithm: Any) -> str:
    return hashlib.sha256(_evaluation_snapshot(algorithm)).hexdigest()


def _value_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_training_job(job: Mapping[str, Any], device: str, max_interactions: int, output_root: Path | str) -> dict[str, Any]:
    if not isinstance(job, Mapping):
        raise TypeError("job must be a mapping")
    root = Path(job.get("source_root", Path(__file__).resolve().parents[3])).resolve()
    contract = load_g5_contract(root)
    method = str(job.get("method", ""))
    condition = str(job.get("condition_id", method))
    if method not in METHODS:
        raise ValueError(f"unknown learning method {method!r}")
    if condition not in (*ALL_CONDITION_TYPES, *METHODS):
        raise ValueError(f"unknown condition {condition!r}")
    seed = job.get("training_seed", 51001)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed not in contract.partitions["development_training"]:
        raise ValueError("smoke runner requires a development training seed")
    if job.get("partition") != "development" or int(job.get("scenario_id", -1)) not in contract.partitions["development_scenarios"]:
        raise ValueError("smoke runner requires development partition and scenario")
    scale = str(job.get("scale", "g5_smoke"))
    if isinstance(max_interactions, bool) or int(max_interactions) <= 0:
        raise ValueError("max_interactions must be positive")
    preflight = run_preflight(device, root)
    if preflight.get("status") != "pass":
        raise RuntimeError(preflight.get("reason", "device preflight failed"))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if str(device).lower() == "cuda":
        torch.cuda.reset_peak_memory_stats()
    output = Path(output_root).resolve() / f"{method}__{condition}__{seed}"
    output.mkdir(parents=True, exist_ok=True)
    # The learning family is owned by the job method; condition is an
    # independent support/controller boundary and must never swap algorithms.
    actual_method = method
    algorithm = build_algorithm(actual_method, contract, device)
    provenance = _provenance(contract, condition)
    start = 0
    resume_from = job.get("resume_from")
    if resume_from:
        algorithm, metadata = load_checkpoint(Path(resume_from), lambda: build_algorithm(actual_method, contract, device), expected_provenance=provenance)
        start = int(metadata["provenance"].get("interactions", 0))
    target = int(max_interactions)
    stop_at = min(target, int(job.get("stop_after_interactions", target)))
    records: list[dict[str, Any]] = []
    for index in range(start, stop_at):
        current, nxt = _observations(0), _observations(1)
        details = algorithm.act(current, _masks(), deterministic=False, return_details=True)
        algorithm.observe(_envelope(algorithm, current, nxt, index, details, scenario_id=int(job["scenario_id"])))
        records.append({"interaction": index + 1, "method": method, "condition_id": condition, "scale": scale, "scenario_id": int(job["scenario_id"]), "role_shapes": {key: list(value.shape) for key, value in current.items()}, "mask_shapes": {key: list(value.shape) for key, value in _masks().items()}, "validation_accessed": False, "sealed_accessed": False, "replenished_resource": "pesticide", "battery_replenishment_enabled": False})
    interrupted = stop_at < target
    checkpoint = output / "checkpoint.pt"
    # G3 checkpoint provenance is deliberately extended only in the outer report;
    # checkpoint loader compares the frozen contract fields.
    save_checkpoint(checkpoint, algorithm, step=stop_at, provenance=provenance | {"interactions": stop_at})
    if interrupted:
        return {"method": method, "algorithm_id": actual_method, "condition_id": condition, "scale": scale, "scenario_id": int(job["scenario_id"]), "interactions": stop_at, "updates": 0, "interrupted": True, "checkpoint": str(checkpoint), "training_log": str(output / "training.jsonl"), "validation_accessed": False, "sealed_accessed": False, "resume_equivalent": False, "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()) if str(device).lower() == "cuda" else 0, "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()) if str(device).lower() == "cuda" else 0}
    metrics = algorithm.update()
    finite = all(np.isfinite(float(value)) for value in metrics.values() if isinstance(value, (int, float, np.integer, np.floating)))
    algorithm.set_evaluation(True)
    eval_before = algorithm.normalizer_state_bytes() if hasattr(algorithm, "normalizer_state_bytes") else _evaluation_snapshot(algorithm)
    first = algorithm.act(_observations(0), _masks(), deterministic=True)
    second = algorithm.act(_observations(0), _masks(), deterministic=True)
    eval_after = algorithm.normalizer_state_bytes() if hasattr(algorithm, "normalizer_state_bytes") else _evaluation_snapshot(algorithm)
    evaluation_actions = {role: first.actions[role].tolist() for role in first.actions}
    evaluation_frozen = evaluation_actions == {role: second.actions[role].tolist() for role in second.actions} and eval_before == eval_after
    log_path = output / "training.jsonl"
    if start == 0:
        log_path.unlink(missing_ok=True)
    for record in records:
        append_jsonl(log_path, record)
    diagnostics = algorithm.diagnostics.snapshot()
    state_digest = _state_digest(algorithm)
    metrics_digest = _value_digest(metrics)
    diagnostics_digest = _value_digest(diagnostics)
    resume_comparison = {"algorithm_state_equal": False, "metrics_equal": False, "diagnostics_equal": False}
    if resume_from:
        reference = job.get("resume_reference")
        if not isinstance(reference, Mapping):
            raise ValueError("resume equivalence requires an uninterrupted reference")
        resume_comparison = {
            "algorithm_state_equal": reference.get("algorithm_state_digest") == state_digest,
            "metrics_equal": reference.get("metrics_digest") == metrics_digest,
            "diagnostics_equal": reference.get("diagnostics_digest") == diagnostics_digest,
        }
        if not all(resume_comparison.values()):
            raise ValueError(f"resume equivalence comparison failed: {resume_comparison}")
    resume_equivalent = bool(resume_from) and all(resume_comparison.values())
    summary = {"method": method, "algorithm_id": actual_method, "condition_id": condition, "scale": scale, "partition": "development", "scenario_id": int(job["scenario_id"]), "training_seed": seed, "interactions": target, "updates": int(diagnostics.get("updates", 1)), "finite_metrics": bool(finite), "evaluation_frozen": bool(evaluation_frozen), "evaluation_actions": evaluation_actions, "validation_accessed": False, "sealed_accessed": False, "replenished_resource": "pesticide", "battery_replenishment_enabled": False, "interrupted": False, "resume_equivalent": resume_equivalent, "resume_comparison": resume_comparison, "checkpoint": str(checkpoint), "training_log": str(log_path), "provenance": provenance, "algorithm_state_digest": state_digest, "metrics_digest": metrics_digest, "diagnostics_digest": diagnostics_digest, "metrics": dict(metrics), "role_shapes": {"uav": [2, 179], "vehicle": [1, 28]}, "mask_shapes": {"uav": [2, 6], "vehicle": [1, 5]}, "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()) if str(device).lower() == "cuda" else 0, "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()) if str(device).lower() == "cuda" else 0}
    summary["mask_shapes"]["vehicle"] = [1, 5]
    summary_path = output / "summary.json"
    atomic_write_bytes(summary_path, (json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    manifest = _write_manifest(output, [checkpoint, log_path, summary_path], summary)
    summary["manifest"] = str(manifest)
    return summary


__all__ = ["run_training_job"]
