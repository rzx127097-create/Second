"""Bounded physical candidate training for G5 Task 12."""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import (
    load_training_checkpoint,
    save_training_checkpoint,
)
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import (
    ActionResult,
    OffPolicyEnvelope,
    OnPolicyEnvelope,
    RoleBatch,
)
from problem2.experiments.artifacts import artifact_sha256, atomic_write_bytes
from problem2.experiments.ecology_policy import DYNAMIC_OUTPUT_ROOT, resolve_frozen_g5_manifest
from problem2.experiments.g5_contract import G5Contract, load_g5_contract

from .preflight import run_preflight
from .conditions import resolve_condition_execution
from .runner import _provenance, _validate_preflight, evaluation_state_digest
from .tuning import CanonicalValidationStore, DEVELOPMENT_SCENARIO_IDS, build_development_environment


PHYSICAL_TRAINING_SCHEMA_VERSION = "g5-physical-candidate-training-v1"
PHYSICAL_MANIFEST_SCHEMA_VERSION = "g5-physical-candidate-artifact-v1"
EXPECTED_CANDIDATE_SHA256 = "67e6784b3d00d0385310d467c351f5b3374f02c7a7d7c22c571d4de29190419a"
EXPECTED_BUDGET_SHA256 = "048138954f336c95e3d339aed594c71e23167ef30cc1f4a373d5c2b10bb049cb"
ON_POLICY_METHODS = {"sr_mappo_mobile", "mappo_mobile", "ippo_mobile"}
OFF_POLICY_METHODS = {"maddpg_mobile", "iql_mobile"}
CANONICAL_INTERACTIONS = 200000
PHYSICAL_SOURCE_FILES = (
    "src/problem2/training/physical_training.py",
    "src/problem2/training/tuning.py",
    "src/problem2/training/runner.py",
)
PHYSICAL_SCENARIO_CONTRACT = "docs/evidence/g5/physical_scenario_contract.yaml"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _physical_source_hashes(root: Path) -> dict[str, str]:
    return {relative: _file_sha256(root / relative) for relative in PHYSICAL_SOURCE_FILES}


def _require_clean_tracked_physical_sources(root: Path) -> None:
    for relative in (*PHYSICAL_SOURCE_FILES, PHYSICAL_SCENARIO_CONTRACT):
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
            capture_output=True,
            text=True,
            check=False,
        )
        if tracked.returncode != 0:
            raise RuntimeError(f"canonical physical training source is not tracked: {relative}")
    clean = subprocess.run(
        [
            "git", "-C", str(root), "diff", "--quiet", "HEAD", "--",
            "src/problem2", "scripts/run_g5_validation_tuning.py", PHYSICAL_SCENARIO_CONTRACT,
        ],
        check=False,
    )
    if clean.returncode != 0:
        raise RuntimeError("canonical physical training rejects dirty tracked source")


def physical_checkpoint_provenance(
    contract: G5Contract,
    condition: str,
    candidate_id: str,
    *,
    canonical: bool,
    method: str | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    root = contract.source_root
    if canonical:
        _require_clean_tracked_physical_sources(root)
    source_hashes = _physical_source_hashes(root)
    provenance = _provenance(contract, method or condition, candidate_id)
    bundle_payload = {
        "contract_files": dict(sorted(contract.file_hashes.items())),
        "physical_training_sources": source_hashes,
    }
    provenance["source_bundle_sha256"] = hashlib.sha256(
        json.dumps(bundle_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return provenance, source_hashes


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(payload), sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _evaluation_state_is_finite(algorithm: Any) -> bool:
    for name, value in vars(algorithm).items():
        if isinstance(value, torch.nn.Module):
            if any(not torch.isfinite(tensor).all().item() for tensor in value.state_dict().values()):
                return False
        elif name.endswith("normalizer") and hasattr(value, "state_dict"):
            for nested in value.state_dict().values():
                if isinstance(nested, np.ndarray) and not np.isfinite(nested).all():
                    return False
                if isinstance(nested, (float, np.floating)) and not math.isfinite(float(nested)):
                    return False
    return True


def _as_action_result(details: Mapping[str, Any]) -> ActionResult:
    if not isinstance(details, Mapping) or "actions" not in details or "masks" not in details:
        raise ValueError("algorithm action details are incomplete")
    return ActionResult(actions=details["actions"], masks=details["masks"])


def build_physical_envelope(
    algorithm: Any,
    current_view: Mapping[str, Any],
    next_view: Mapping[str, Any],
    action_details: Mapping[str, Any],
    *,
    team_reward: float,
    transition_index: int,
    vehicle_trainable: bool = True,
) -> OnPolicyEnvelope | OffPolicyEnvelope:
    """Bind one exact physical transition to the strict algorithm protocol."""

    if not math.isfinite(float(team_reward)):
        raise ValueError("physical team reward must be finite")
    action_result = _as_action_result(action_details)
    executed_actions = {
        role: np.asarray(values, dtype=np.int64).copy()
        for role, values in action_result.actions.items()
    }
    executed_view_actions = next_view.get("sampled_actions")
    if (
        not vehicle_trainable
        and isinstance(executed_view_actions, Mapping)
        and "vehicle" in executed_view_actions
    ):
        executed_actions["vehicle"] = np.asarray(
            executed_view_actions["vehicle"], dtype=np.int64
        ).reshape(-1)
    action_result = ActionResult(actions=executed_actions, masks=action_result.masks)
    rewards = {
        role: np.full(
            np.asarray(current_view["observations"][role]).shape[0],
            float(team_reward),
            dtype=np.float32,
        )
        for role in algorithm.roles
    }
    scenario_id = int(current_view["scenario_id"])
    role_batch = RoleBatch.from_action_result(
        action_result,
        observations=current_view["observations"],
        rewards=rewards,
        next_observations=next_view["observations"],
        next_masks=next_view["masks"],
        terminated=bool(next_view.get("terminated", False)),
        truncated=bool(next_view.get("truncated", False)),
        scenario_id=f"development-{scenario_id}",
        transition_id=f"physical-development-{scenario_id}:{transition_index}",
    )
    common = {
        "role_batch": role_batch,
        "team_reward": float(team_reward),
        "valid_sample": True,
        "valid_actor_sample": {
            role: (np.count_nonzero(np.asarray(action_details["masks"][role], dtype=bool), axis=-1) > 1)
            if role != "vehicle" or vehicle_trainable else np.zeros(np.asarray(action_details["masks"][role]).shape[0], dtype=bool)
            for role in algorithm.roles
        },
        "agent_ids": current_view["agent_ids"],
        "candidate_mapping": current_view["candidate_mapping"],
    }
    if algorithm.method_id not in ON_POLICY_METHODS:
        return OffPolicyEnvelope(
            critic_state=current_view["critic_state"],
            next_critic_state=next_view["critic_state"],
            **common,
        )

    old_log_probs = action_details["log_probs"]
    if not vehicle_trainable:
        old_log_probs = {
            role: values for role, values in action_details["log_probs"].items()
        }
        replayed = algorithm.replay_log_probs(
            action_details["policy_observations"],
            action_result.masks,
            action_result.actions,
        )
        old_log_probs["vehicle"] = replayed["vehicle"]
    policy_common = {
        **common,
        "policy_observations": action_details["policy_observations"],
        "old_log_probs": old_log_probs,
        "normalization_versions": action_details["normalization_versions"],
    }
    if algorithm.method_id == "ippo_mobile":
        next_values = {
            role: algorithm.local_value(role, next_view["observations"][role]).detach().cpu().numpy()
            for role in algorithm.roles
        }
        return OnPolicyEnvelope(
            values=action_details["values"],
            next_values=next_values,
            value_conditioning="local",
            **policy_common,
        )
    next_value = float(
        algorithm.value(next_view["critic_state"]).detach().cpu().reshape(-1)[0]
    )
    current_value = float(
        algorithm.value(current_view["critic_state"]).detach().cpu().reshape(-1)[0]
    )
    return OnPolicyEnvelope(
        values=current_value,
        next_values=next_value,
        value_conditioning="centralized",
        critic_state=current_view["critic_state"],
        next_critic_state=next_view["critic_state"],
        **policy_common,
    )


def _clear_off_policy_replay(algorithm: Any) -> None:
    if algorithm.method_id == "maddpg_mobile":
        algorithm.replay = JointReplayBuffer(algorithm.replay.capacity, seed=0)
        if hasattr(algorithm, "_physical_replay_before_observe"):
            delattr(algorithm, "_physical_replay_before_observe")
    elif algorithm.method_id == "iql_mobile":
        algorithm.uav_replay = JointReplayBuffer(algorithm.uav_replay.capacity, seed=0)
        algorithm.vehicle_replay = JointReplayBuffer(algorithm.vehicle_replay.capacity, seed=1)


def _terminal_buffer_counts(algorithm: Any) -> tuple[int, int]:
    pending = len(getattr(algorithm, "_pending_envelopes", ()))
    if algorithm.method_id == "maddpg_mobile":
        replay_rows = len(algorithm.replay)
    elif algorithm.method_id == "iql_mobile":
        replay_rows = len(algorithm.uav_replay) + len(algorithm.vehicle_replay)
    else:
        replay_rows = 0
    return pending, replay_rows


def _observe_physical_algorithm(
    algorithm: Any,
    envelope: OnPolicyEnvelope | OffPolicyEnvelope,
    *,
    vehicle_trainable: bool,
) -> None:
    """Collect a physical transition without creating a vehicle-only replay row."""

    if vehicle_trainable or algorithm.method_id not in OFF_POLICY_METHODS:
        algorithm.observe(envelope)
        return
    if algorithm.method_id == "iql_mobile":
        algorithm.uav_replay.append(envelope)
        algorithm.diagnostics.increment("observed_transitions")
        return
    # MADDPG has one joint replay. Keep the transition available for its UAV
    # update, then restore the pre-transition replay after the update boundary.
    if not hasattr(algorithm, "_physical_replay_before_observe"):
        algorithm._physical_replay_before_observe = deepcopy(algorithm.replay.state_dict())
    algorithm.replay.append(envelope)
    algorithm.diagnostics.increment("observed_transitions")


def _vehicle_training_snapshot(algorithm: Any) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"modules": {}, "normalizers": {}, "trainer": {}}
    for name, value in vars(algorithm).items():
        if name.startswith("vehicle_") and isinstance(value, torch.nn.Module):
            snapshot["modules"][name] = deepcopy(value.state_dict())
        elif name.startswith("vehicle_") and hasattr(value, "state_dict"):
            snapshot["normalizers"][name] = deepcopy(value.state_dict())
    trainer = getattr(algorithm, "_trainer", None)
    if trainer is not None:
        for name in ("optimizers", "actor_optimizers", "critic_optimizers", "schedulers"):
            mapping = getattr(trainer, name, None)
            if isinstance(mapping, Mapping) and "vehicle" in mapping:
                snapshot["trainer"][name] = deepcopy(mapping["vehicle"].state_dict())
        for name in ("role_update_count", "target_update_count"):
            mapping = getattr(trainer, name, None)
            if isinstance(mapping, Mapping) and "vehicle" in mapping:
                snapshot["trainer"][name] = deepcopy(mapping["vehicle"])
    if algorithm.method_id == "iql_mobile" and hasattr(algorithm, "vehicle_replay"):
        snapshot["vehicle_replay"] = deepcopy(algorithm.vehicle_replay.state_dict())
    if algorithm.method_id == "maddpg_mobile" and hasattr(algorithm, "_physical_replay_before_observe"):
        snapshot["shared_replay"] = deepcopy(algorithm._physical_replay_before_observe)
    return snapshot


def _restore_vehicle_training_snapshot(algorithm: Any, snapshot: Mapping[str, Any]) -> None:
    for name, state in snapshot.get("modules", {}).items():
        getattr(algorithm, name).load_state_dict(state)
    for name, state in snapshot.get("normalizers", {}).items():
        getattr(algorithm, name).load_state_dict(state)
    trainer = getattr(algorithm, "_trainer", None)
    if trainer is not None:
        for name, state in snapshot.get("trainer", {}).items():
            target = getattr(trainer, name)
            if isinstance(target, Mapping) and "vehicle" in target:
                if name in {"role_update_count", "target_update_count"}:
                    target["vehicle"] = deepcopy(state)
                else:
                    target["vehicle"].load_state_dict(state)
    if "vehicle_replay" in snapshot:
        algorithm.vehicle_replay.load_state_dict(snapshot["vehicle_replay"])
    if "shared_replay" in snapshot:
        algorithm.replay.load_state_dict(snapshot["shared_replay"])
        if hasattr(algorithm, "_physical_replay_before_observe"):
            delattr(algorithm, "_physical_replay_before_observe")


def _update_interval(algorithm: Any) -> tuple[str, int]:
    if algorithm.method_id in ON_POLICY_METHODS:
        return "rollout_horizon", int(algorithm.training_config["rollout_horizon"])
    return "batch_size", int(algorithm.trainer.batch_size)


def _update_physical_algorithm(algorithm: Any, *, vehicle_trainable: bool = True) -> Mapping[str, Any]:
    vehicle_snapshot = _vehicle_training_snapshot(algorithm) if not vehicle_trainable else None
    try:
        if algorithm.method_id == "iql_mobile" and not vehicle_trainable and not len(algorithm.vehicle_replay):
            rows = algorithm.uav_replay.sample(
                min(algorithm.trainer.batch_size, len(algorithm.uav_replay))
            )
            result = algorithm.trainer.update_role("uav", rows)
            algorithm._diagnostics.increment("updates")
            return {
                "uav_loss": float(result["loss"]),
                "vehicle_loss": 0.0,
                "updates": float(algorithm.trainer.update_count),
            }
        if algorithm.method_id != "ippo_mobile":
            return algorithm.update()
        empty_roles = [
            role
            for role in algorithm.roles
            if not any(
                bool(envelope.valid_sample)
                and np.asarray(envelope.valid_actor_sample[role], dtype=bool).any()
                for envelope in algorithm._pending_envelopes
            )
        ]
        if not empty_roles:
            return algorithm.update()

        batch = algorithm._rollout_from_envelopes()
        actor_snapshots: dict[str, dict[str, torch.Tensor]] = {}
        gradient_flags: dict[str, list[bool]] = {}
        for role in empty_roles:
            actor = algorithm.uav_actor if role == "uav" else algorithm.vehicle_actor
            actor_snapshots[role] = {
                key: value.detach().cpu().clone()
                for key, value in actor.state_dict().items()
            }
            parameters = list(actor.parameters())
            gradient_flags[role] = [parameter.requires_grad for parameter in parameters]
            for parameter in parameters:
                parameter.requires_grad_(False)
            for record in batch.transitions:
                record["valid_actor_sample"][role] = np.ones_like(
                    record["valid_actor_sample"][role], dtype=bool
                )
        try:
            metrics = dict(
                algorithm.trainer.update(
                    batch,
                    epochs=int(algorithm.training_config.get("ppo_epochs", 1)),
                )
            )
        finally:
            for role in empty_roles:
                actor = algorithm.uav_actor if role == "uav" else algorithm.vehicle_actor
                for parameter, enabled in zip(actor.parameters(), gradient_flags[role]):
                    parameter.requires_grad_(enabled)
        for role in empty_roles:
            actor = algorithm.uav_actor if role == "uav" else algorithm.vehicle_actor
            if any(
                not torch.equal(value.detach().cpu(), actor_snapshots[role][key])
                for key, value in actor.state_dict().items()
            ):
                raise RuntimeError(
                    f"forced {role} actor changed during the physical IPPO value update"
                )
            metrics[f"{role}_actor_updates"] = 0
            metrics[f"{role}_valid_samples"] = 0
        algorithm._pending_envelopes = []
        algorithm._update_count += 1
        algorithm._diagnostics.increment("updates")
        return metrics
    finally:
        if vehicle_snapshot is not None:
            _restore_vehicle_training_snapshot(algorithm, vehicle_snapshot)


def _validate_job(
    job: Mapping[str, Any],
    contract: G5Contract,
    max_interactions: int,
) -> tuple[str, str, str, int, str, tuple[int, ...]]:
    if not isinstance(job, Mapping):
        raise TypeError("physical training job must be a mapping")
    method = str(job.get("method", ""))
    condition = str(job.get("condition_id", method))
    if method not in ON_POLICY_METHODS | OFF_POLICY_METHODS:
        raise ValueError("physical candidate training requires one exact frozen learning method identity")
    if condition != method:
        try:
            execution = resolve_condition_execution(condition)
        except ValueError as exc:
            raise ValueError("physical refit condition is not executable") from exc
        if (
            job.get("vehicle_controller") != execution.vehicle_controller
            or job.get("vehicle_trainable") is not execution.vehicle_trainable
            or job.get("training_mode") != execution.training_mode
        ):
            raise ValueError("physical refit condition semantics are incomplete")
    candidate_id = job.get("candidate_id")
    candidates = contract.tuning_candidates.get(method, ())
    if not isinstance(candidate_id, str) or candidate_id not in {item.candidate_id for item in candidates}:
        raise ValueError("physical candidate training requires a frozen candidate ID")
    seed = job.get("training_seed")
    if type(seed) is not int or seed not in contract.partitions["development_training"]:
        raise ValueError("physical candidate training requires a frozen development training seed")
    if job.get("partition") != "development" or job.get("scenario_id") != DEVELOPMENT_SCENARIO_IDS.start:
        raise ValueError("physical candidate training must start at development scenario 10000")
    scenario_ids = tuple(job.get("scenario_ids", ()))
    if scenario_ids != tuple(DEVELOPMENT_SCENARIO_IDS):
        raise ValueError("physical candidate training must cycle exact scenarios 10000-10019")
    scale = str(job.get("scale", ""))
    if not scale:
        raise ValueError("physical candidate training requires a frozen scale")
    if type(max_interactions) is not int or max_interactions <= 0:
        raise ValueError("physical interaction count must be a positive integer")
    if job.get("resume_from") is not None:
        raise ValueError("terminal physical candidate checkpoints are not resumable")
    return method, condition, candidate_id, seed, scale, scenario_ids


def validate_physical_training_completion(
    manifest_path: Path | str,
    *,
    contract: G5Contract,
    method: str,
    condition_id: str | None = None,
    candidate_id: str,
    config_hash: str,
    seed: int,
    interactions: int,
    scale: str,
    device: str,
    canonical: bool,
) -> dict[str, Any]:
    """Validate a manifest-complete physical identity and strictly reload its policy."""

    condition = str(condition_id or method)
    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.is_file():
        raise RuntimeError(f"physical training completion manifest is missing: {manifest_file}")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"physical training completion manifest is unreadable: {manifest_file}") from exc
    expected_manifest_keys = {
        "schema_version", "status", "identity", "artifacts", "canonical",
        "evidence_status", "checkpoint_evaluation_state_digest", "source_provenance",
        "validation_accessed", "sealed_accessed",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_manifest_keys:
        raise RuntimeError("physical training completion manifest schema drifted")
    evidence_status = "canonical_candidate_evidence" if canonical else "noncanonical_test_only"
    expected_identity = {
        "method": method,
        "algorithm_id": method,
        "condition_id": condition,
        "partition": "development",
        "scenario_id": DEVELOPMENT_SCENARIO_IDS.start,
        "scenario_ids": list(DEVELOPMENT_SCENARIO_IDS),
        "candidate_id": candidate_id,
        "candidate_config_hash": config_hash,
        "training_seed": seed,
        "interaction_count": interactions,
        "scale": scale,
    }
    if (
        manifest["schema_version"] != PHYSICAL_MANIFEST_SCHEMA_VERSION
        or manifest["status"] != "pass"
        or manifest["identity"] != expected_identity
        or manifest["canonical"] is not canonical
        or manifest["evidence_status"] != evidence_status
        or manifest["validation_accessed"] is not False
        or manifest["sealed_accessed"] is not False
    ):
        raise RuntimeError("physical training completion manifest identity drifted")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        raise RuntimeError("physical training completion manifest artifact set drifted")
    expected_names = {"checkpoint.pt", "physical-episodes.jsonl", "summary.json"}
    observed_names = {item.get("path") for item in artifacts if isinstance(item, dict)}
    if observed_names != expected_names or len(observed_names) != len(artifacts):
        raise RuntimeError("physical training completion manifest artifact set drifted")
    directory_files = {item.name for item in manifest_file.parent.iterdir() if item.is_file()}
    if directory_files != expected_names | {"manifest.json"}:
        raise RuntimeError("physical training completion directory has an extra or missing artifact")
    for item in artifacts:
        if set(item) != {"path", "sha256", "bytes"}:
            raise RuntimeError("physical training completion artifact entry drifted")
        artifact = (manifest_file.parent / item["path"]).resolve()
        if artifact.parent != manifest_file.parent or not artifact.is_file():
            raise RuntimeError("physical training completion artifact path escaped")
        if artifact_sha256(artifact) != item["sha256"] or artifact.stat().st_size != item["bytes"]:
            raise RuntimeError("physical training completion artifact hash or byte count drifted")

    summary_file = manifest_file.parent / "summary.json"
    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("physical training summary is unreadable") from exc
    expected_summary = {
        "schema_version": PHYSICAL_TRAINING_SCHEMA_VERSION,
        "status": "completed",
        "training_mode": "physical_development",
        "scenario_execution": True,
        "method": method,
        "algorithm_id": method,
        "condition_id": condition,
        "partition": "development",
        "scenario_id": DEVELOPMENT_SCENARIO_IDS.start,
        "scenario_ids": list(DEVELOPMENT_SCENARIO_IDS),
        "training_seed": seed,
        "scale": scale,
        "interaction_count": interactions,
        "interactions": interactions,
        "candidate_id": candidate_id,
        "candidate_config_hash": config_hash,
        "interrupted": False,
        "finite_metrics": True,
        "evaluation_frozen": True,
        "terminal_checkpoint_kind": "inference_evaluation_complete",
        "pending_on_policy_envelopes": 0,
        "off_policy_replay_rows": 0,
        "resumable_mid_training": False,
        "canonical": canonical,
        "evidence_status": evidence_status,
        "vehicle_controller": (
            resolve_condition_execution(condition).vehicle_controller
            if condition != method
            else "learned"
        ),
        "vehicle_trainable": (
            resolve_condition_execution(condition).vehicle_trainable
            if condition != method
            else True
        ),
        "condition_training_mode": (
            resolve_condition_execution(condition).training_mode
            if condition != method
            else "joint"
        ),
    }
    if not isinstance(summary, dict) or any(summary.get(key) != value for key, value in expected_summary.items()):
        raise RuntimeError("physical training summary identity or finite-state declaration drifted")
    if summary.get("checkpoint_after_update_count") != summary.get("optimizer_update_count"):
        raise RuntimeError("physical training checkpoint precedes the final update")
    for field, name in (("checkpoint", "checkpoint.pt"), ("training_log", "physical-episodes.jsonl"), ("summary", "summary.json"), ("manifest", "manifest.json")):
        if Path(str(summary.get(field, ""))).resolve() != (manifest_file.parent / name).resolve():
            raise RuntimeError(f"physical training summary {field} path drifted")

    expected_provenance, source_hashes = physical_checkpoint_provenance(
        contract, condition, candidate_id, canonical=canonical, method=method
    )
    expected_environment = build_development_environment(
        contract.source_root,
        scenario_id=DEVELOPMENT_SCENARIO_IDS.start,
        scale=scale,
    )
    expected_source = {
        **expected_environment.source_provenance,
        "source_commit": expected_provenance["source_commit"],
        "source_bundle_sha256": expected_provenance["source_bundle_sha256"],
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_SHA256,
        "budget_manifest_sha256": EXPECTED_BUDGET_SHA256,
        "physical_training_source_sha256": source_hashes,
        "canonical": canonical,
        "evidence_status": evidence_status,
    }
    if summary.get("checkpoint_provenance") != expected_provenance:
        raise RuntimeError("physical training checkpoint provenance drifted from current source")
    if summary.get("source_provenance") != expected_source or manifest["source_provenance"] != expected_source:
        raise RuntimeError("physical training source provenance drifted from current source")
    checkpoint = manifest_file.parent / "checkpoint.pt"
    try:
        restored, _ = load_training_checkpoint(
            checkpoint,
            lambda: build_algorithm(method, contract, device, candidate_id=candidate_id, scale=scale),
            expected_provenance,
        )
    except Exception as exc:
        raise RuntimeError("physical training checkpoint strict reload failed") from exc
    digest = evaluation_state_digest(restored)
    if not _evaluation_state_is_finite(restored):
        raise RuntimeError("physical training evaluation state is not finite")
    if (
        summary.get("trained_evaluation_state_digest") != digest
        or summary.get("checkpoint_evaluation_state_digest") != digest
        or summary.get("algorithm_state_digest") != digest
        or manifest["checkpoint_evaluation_state_digest"] != digest
    ):
        raise RuntimeError("physical training evaluation-state digest drifted")
    return {**summary, "completion_validated": True}


def _run_physical_candidate_training(
    job: Mapping[str, Any],
    device: str,
    max_interactions: int,
    output_root: Path | str,
    *,
    canonical: bool,
    allow_g5_output: bool = False,
) -> dict[str, Any]:
    """Train one frozen candidate on exact G2-backed development transitions."""

    root = Path(job.get("source_root", Path(__file__).resolve().parents[3])).resolve()
    supplied_contract = job.get("_contract")
    contract = supplied_contract if isinstance(supplied_contract, G5Contract) else load_g5_contract(root)
    if contract.validation_accessed is not False or contract.sealed_accessed is not False:
        raise RuntimeError("physical candidate training requires untouched validation and sealed partitions")
    method, condition, candidate_id, seed, scale, scenario_ids = _validate_job(
        job, contract, max_interactions
    )
    base_output = Path(output_root).resolve()
    canonical_g5_root = (root / DYNAMIC_OUTPUT_ROOT / "g5").resolve()
    if canonical and not base_output.is_relative_to(canonical_g5_root):
        raise ValueError("canonical physical training output must be confined below the canonical G5 output root")
    if not canonical and base_output.is_relative_to(canonical_g5_root) and not allow_g5_output:
        raise ValueError("noncanonical test training cannot write below the canonical G5 output root")
    if canonical:
        CanonicalValidationStore.assert_candidate_generation_allowed(root)
    candidates_path = resolve_frozen_g5_manifest(root, "validation-candidates.json")
    budget_path = resolve_frozen_g5_manifest(root, "pilot-budget.json")
    if _file_sha256(candidates_path) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("frozen validation candidate bytes drifted")
    if _file_sha256(budget_path) != EXPECTED_BUDGET_SHA256:
        raise RuntimeError("frozen pilot budget bytes drifted")
    supplied_preflight = job.get("_preflight")
    preflight = supplied_preflight if isinstance(supplied_preflight, Mapping) else run_preflight(device, root)
    _validate_preflight(preflight, str(device).lower())

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if str(device).lower() == "cuda":
        torch.cuda.reset_peak_memory_stats()
    candidate = next(item for item in contract.tuning_candidates[method] if item.candidate_id == candidate_id)
    algorithm = build_algorithm(method, contract, device, candidate_id=candidate_id, scale=scale)
    checkpoint_provenance, physical_source_hashes = physical_checkpoint_provenance(
        contract, condition, candidate_id, canonical=canonical, method=method
    )
    schedule_name, update_interval = _update_interval(algorithm)
    target = int(max_interactions)

    job_output = (base_output / f"{method}__{condition}__{seed}").resolve()
    if not job_output.is_relative_to(base_output):
        raise ValueError("physical training output escaped the supplied root")
    job_output.mkdir(parents=True, exist_ok=True)

    scenario_cursor = 0
    condition_for_factory = condition if condition in {"sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "sr_mappo_nearest", "sr_mappo_urgency", "sr_mappo_two_stage"} else None
    condition_vehicle_trainable = condition_for_factory is None or resolve_condition_execution(condition_for_factory).vehicle_trainable
    environment = build_development_environment(
        root, scenario_id=scenario_ids[scenario_cursor], scale=scale, condition_id=condition_for_factory
    )
    if getattr(environment, "primary_eligible", False) is not True or getattr(environment, "ecology_mode", None) != "dynamic":
        raise RuntimeError("physical candidate training requires the dynamic primary environment")
    current = environment.reset(scenario_id=scenario_ids[scenario_cursor])
    source_provenance = {
        **environment.source_provenance,
        "source_commit": checkpoint_provenance["source_commit"],
        "source_bundle_sha256": checkpoint_provenance["source_bundle_sha256"],
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_SHA256,
        "budget_manifest_sha256": EXPECTED_BUDGET_SHA256,
        "physical_training_source_sha256": physical_source_hashes,
        "canonical": canonical,
        "evidence_status": "canonical_candidate_evidence" if canonical else "noncanonical_test_only",
    }
    update_count = 0
    fresh_since_update = 0
    episode_interactions = 0
    episode_reward = 0.0
    episode_rows: list[dict[str, Any]] = []
    executed_scenarios: list[int] = []
    last_metrics: Mapping[str, Any] = {}

    def finish_episode() -> None:
        episode_rows.append({
            "partition": "development",
            "scenario_id": int(environment.physical.scenario_id),
            "interaction_count": episode_interactions,
            "team_reward_sum": episode_reward,
            "initial_total_pest": float(environment.initial_prey.sum()),
            "final_total_pest": float(environment.prey.sum()),
            "spray_action_count": int(environment.spray_action_count),
            "sprayed_pesticide_l": float(environment.sprayed_pesticide_l),
            "metric_source": "dynamic_ecology_environment",
            "ecology_version": environment.ecology.config.version,
            "ecology_config_sha256": environment.ecology.config.contract_sha256,
            "ecology_scenario_sha256": environment.ecology.scenario.scenario_sha256,
            "initial_total_predator": float(environment.initial_predator.sum()),
            "final_total_predator": float(environment.predator.sum()),
            "cumulative_deposited_effect": environment.ecology.deposited_effect,
            "terminal_mean_concentration": float(environment.ecology.concentration.mean()),
            "terminal_max_concentration": float(environment.ecology.concentration.max()),
            "terminal_wind_direction": float(environment.ecology.wind_state.direction),
            "terminal_wind_strength": float(environment.ecology.wind_state.strength),
            "dynamic_step_count": environment.ecology.step_count,
        })

    for transition_index in range(target):
        scenario_id = int(current["scenario_id"])
        if not executed_scenarios or executed_scenarios[-1] != scenario_id:
            executed_scenarios.append(scenario_id)
        details = algorithm.act(
            current["observations"],
            current["masks"],
            deterministic=False,
            return_details=True,
        )
        action_result = _as_action_result(details)
        next_view = environment.step(action_result)
        team_reward = float(next_view["team_reward"])
        envelope = build_physical_envelope(
            algorithm,
            current,
            next_view,
            details,
            team_reward=team_reward,
            transition_index=transition_index,
            vehicle_trainable=condition_vehicle_trainable,
        )
        algorithm.observe(envelope)
        fresh_since_update += 1
        episode_interactions += 1
        episode_reward += team_reward

        if fresh_since_update == update_interval:
            last_metrics = _update_physical_algorithm(algorithm, vehicle_trainable=condition_vehicle_trainable)
            update_count += 1
            fresh_since_update = 0
            if method in OFF_POLICY_METHODS:
                _clear_off_policy_replay(algorithm)

        final_interaction = transition_index + 1 == target
        if next_view["truncated"] or final_interaction:
            finish_episode()
        if next_view["truncated"] and not final_interaction:
            scenario_cursor = (scenario_cursor + 1) % len(scenario_ids)
            environment = build_development_environment(
                root, scenario_id=scenario_ids[scenario_cursor], scale=scale, condition_id=condition_for_factory
            )
            if getattr(environment, "primary_eligible", False) is not True or getattr(environment, "ecology_mode", None) != "dynamic":
                raise RuntimeError("physical candidate training requires the dynamic primary environment")
            current = environment.reset(scenario_id=scenario_ids[scenario_cursor])
            episode_interactions = 0
            episode_reward = 0.0
        else:
            current = next_view

    final_partial_size = fresh_since_update
    if method in ON_POLICY_METHODS and fresh_since_update:
        last_metrics = _update_physical_algorithm(algorithm, vehicle_trainable=condition_vehicle_trainable)
        update_count += 1
        fresh_since_update = 0
    if method in OFF_POLICY_METHODS:
        _clear_off_policy_replay(algorithm)

    finite_metrics = all(
        math.isfinite(float(value))
        for value in last_metrics.values()
        if isinstance(value, (int, float, np.integer, np.floating))
    )
    algorithm.set_evaluation(True)
    trained_digest = evaluation_state_digest(algorithm)
    pending_count, replay_rows = _terminal_buffer_counts(algorithm)
    if pending_count != 0 or replay_rows != 0:
        raise RuntimeError("terminal validation checkpoint still contains training transitions")

    checkpoint = job_output / "checkpoint.pt"
    save_training_checkpoint(
        checkpoint,
        {
            "algorithm": algorithm.state_dict(),
            "training_mode": "physical_development",
            "interaction_count": target,
            "optimizer_update_count": update_count,
            "resumable_mid_training": False,
        },
        checkpoint_provenance,
    )
    restored, _ = load_training_checkpoint(
        checkpoint,
        lambda: build_algorithm(method, contract, device, candidate_id=candidate_id, scale=scale),
        checkpoint_provenance,
    )
    checkpoint_digest = evaluation_state_digest(restored)
    if checkpoint_digest != trained_digest:
        raise RuntimeError("terminal checkpoint evaluation state differs from the trained policy")

    training_log = job_output / "physical-episodes.jsonl"
    log_bytes = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        for row in episode_rows
    )
    atomic_write_bytes(training_log, log_bytes)
    summary_path = job_output / "summary.json"
    manifest_path = job_output / "manifest.json"
    summary: dict[str, Any] = {
        "schema_version": PHYSICAL_TRAINING_SCHEMA_VERSION,
        "status": "completed",
        "training_mode": "physical_development",
        "scenario_execution": True,
        "method": method,
        "algorithm_id": method,
        "condition_id": condition,
        "partition": "development",
        "scenario_id": scenario_ids[0],
        "scenario_ids": list(scenario_ids),
        "executed_scenario_ids": executed_scenarios,
        "training_seed": seed,
        "scale": scale,
        "interaction_count": target,
        "interactions": target,
        "candidate_id": candidate_id,
        "candidate_config_hash": candidate.config_hash,
        "optimizer_update_count": update_count,
        "updates": update_count,
        "update_schedule": schedule_name,
        "update_interval": update_interval,
        "final_partial_block_size": final_partial_size,
        "checkpoint_after_update_count": update_count,
        "finite_metrics": finite_metrics,
        "evaluation_frozen": True,
        "trained_evaluation_state_digest": trained_digest,
        "checkpoint_evaluation_state_digest": checkpoint_digest,
        "algorithm_state_digest": trained_digest,
        "checkpoint": str(checkpoint),
        "checkpoint_provenance": checkpoint_provenance,
        "checkpoint_bytes": checkpoint.stat().st_size,
        "terminal_checkpoint_kind": "inference_evaluation_complete",
        "pending_on_policy_envelopes": pending_count,
        "off_policy_replay_rows": replay_rows,
        "resumable_mid_training": False,
        "interrupted": False,
        "training_log": str(training_log),
        "summary": str(summary_path),
        "manifest": str(manifest_path),
        "source_provenance": source_provenance,
        "reward_source": "signed_normalized_dynamic_prey_change",
        "shared_team_reward": True,
        "replenished_resource": "pesticide",
        "initial_onboard_pesticide_l": 0.2875,
        "battery_replenishment_enabled": False,
        "validation_accessed": False,
        "sealed_accessed": False,
        "canonical": canonical,
        "evidence_status": "canonical_candidate_evidence" if canonical else "noncanonical_test_only",
        "vehicle_controller": (
            resolve_condition_execution(condition).vehicle_controller
            if condition != method
            else "learned"
        ),
        "vehicle_trainable": (
            resolve_condition_execution(condition).vehicle_trainable
            if condition != method
            else True
        ),
        "condition_training_mode": (
            resolve_condition_execution(condition).training_mode
            if condition != method
            else "joint"
        ),
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()) if str(device).lower() == "cuda" else 0,
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()) if str(device).lower() == "cuda" else 0,
    }
    atomic_write_bytes(summary_path, _json_bytes(summary))
    manifest = {
        "schema_version": PHYSICAL_MANIFEST_SCHEMA_VERSION,
        "status": "pass",
        "identity": {
            "method": method,
            "algorithm_id": method,
            "condition_id": condition,
            "partition": "development",
            "scenario_id": scenario_ids[0],
            "scenario_ids": list(scenario_ids),
            "candidate_id": candidate_id,
            "candidate_config_hash": candidate.config_hash,
            "training_seed": seed,
            "interaction_count": target,
            "scale": scale,
        },
        "artifacts": [
            {"path": path.name, "sha256": artifact_sha256(path), "bytes": path.stat().st_size}
            for path in (checkpoint, training_log, summary_path)
        ],
        "canonical": canonical,
        "evidence_status": "canonical_candidate_evidence" if canonical else "noncanonical_test_only",
        "checkpoint_evaluation_state_digest": checkpoint_digest,
        "source_provenance": source_provenance,
        "validation_accessed": False,
        "sealed_accessed": False,
    }
    atomic_write_bytes(manifest_path, _json_bytes(manifest))
    return validate_physical_training_completion(
        manifest_path,
        contract=contract,
        method=method,
        condition_id=condition,
        candidate_id=candidate_id,
        config_hash=candidate.config_hash,
        seed=seed,
        interactions=target,
        scale=scale,
        device=device,
        canonical=canonical,
    )


def run_physical_candidate_training(
    job: Mapping[str, Any], device: str, max_interactions: int, output_root: Path | str
) -> dict[str, Any]:
    """Run one canonical 200,000-interaction candidate identity."""

    if type(max_interactions) is not int or max_interactions != CANONICAL_INTERACTIONS:
        raise ValueError("canonical physical candidate training requires exactly 200000 interactions")
    return _run_physical_candidate_training(
        job, device, max_interactions, output_root, canonical=True
    )


def run_noncanonical_physical_candidate_training_for_test(
    job: Mapping[str, Any], device: str, max_interactions: int, output_root: Path | str
) -> dict[str, Any]:
    """Run a short, unmistakably noncanonical candidate path under a test temp root."""

    return _run_physical_candidate_training(
        job, device, max_interactions, output_root, canonical=False
    )


def run_physical_development_refit_training(
    job: Mapping[str, Any], device: str, max_interactions: int, output_root: Path | str
) -> dict[str, Any]:
    """Run a physical development refit identity under the G5 output root.

    The outer pilot condition is supplied by the refit orchestrator. The
    physical candidate runner owns the learning method and candidate state;
    the orchestrator records the outer condition separately so no synthetic
    Task10 transition path can be used for the refit evidence.
    """

    if type(max_interactions) is not int or max_interactions <= 0:
        raise ValueError("physical development refit interactions must be positive")
    return _run_physical_candidate_training(
        job,
        device,
        max_interactions,
        output_root,
        canonical=False,
        allow_g5_output=True,
    )


__all__ = [
    "EXPECTED_BUDGET_SHA256",
    "EXPECTED_CANDIDATE_SHA256",
    "PHYSICAL_TRAINING_SCHEMA_VERSION",
    "physical_checkpoint_provenance",
    "build_physical_envelope",
    "evaluation_state_digest",
    "run_physical_candidate_training",
    "run_noncanonical_physical_candidate_training_for_test",
    "run_physical_development_refit_training",
    "validate_physical_training_completion",
]
