"""Controlled, non-sealed G3 training smoke."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from problem2.algorithms.common.checkpoint import save_checkpoint
from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
from problem2.algorithms.sr_mappo.rollout import RolloutBatch
from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
from problem2.config import load_g3_config

from .development_env import (
    DevelopmentCooperativeEnv,
    scenario_seed_manifest_provenance,
)


CANONICAL_G3_OUTPUT_ROOT = Path("outputs/problem2_sr_mappo_v1/g3")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_TREE_ROOTS = (
    "src",
    "scripts",
    "tests",
    "configs",
    "pyproject.toml",
    "requirements-g2.lock",
    "requirements-g3.lock",
)


def _source_tree_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _source_tree_clean() -> bool:
    try:
        completed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *SOURCE_TREE_ROOTS,
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0 and not completed.stdout.strip()


def source_tree_hash() -> str:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                *SOURCE_TREE_ROOTS,
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return "unknown"
    if completed.returncode != 0:
        return "unknown"

    digest = hashlib.sha256()
    paths = sorted(
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    )
    for relative in paths:
        path = REPOSITORY_ROOT / Path(relative)
        if not path.is_file():
            return "unknown"
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _transition(
    current: dict[str, Any],
    details: dict[str, Any],
    value: float,
    next_value: float,
    next_state: dict[str, Any],
) -> dict[str, Any]:
    masks = current["masks"]
    valid_actor_sample = {
        "uav": (masks["uav"].sum(axis=1) > 1).tolist(),
        "vehicle": (masks["vehicle"].sum(axis=1) > 1).tolist(),
    }
    return {
        "role": current["agent_ids"],
        "agent_id": current["agent_ids"],
        "raw_observation": current["observations"],
        "normalized_policy_observation": details["policy_observations"],
        "critic_state": current["critic_state"],
        "action": details["actions"],
        "action_mask": masks,
        "old_log_prob": details["log_probs"],
        "value": value,
        "next_value": next_value,
        "reward": float(next_state["reward"]),
        "reward_components": next_state["reward_components"],
        "terminated": bool(next_state["terminated"]),
        "truncated": bool(next_state["truncated"]),
        "valid_actor_sample": valid_actor_sample,
        "candidate_mapping": current["candidate_mapping"],
        "normalization_versions": details["normalization_versions"],
        "episode_id": current["episode_id"],
        "config_hash": current["config_hash"],
        "valid": True,
    }


def run_training_smoke(
    config_path: str | Path,
    output_root: str | Path,
    *,
    seed: int,
    updates: int,
    allow_noncanonical_output_root: bool = False,
) -> dict[str, Any]:
    config = load_g3_config(config_path)
    if updates <= 0:
        raise ValueError("updates must be positive")
    root = Path(output_root).resolve()
    canonical_root = (
        REPOSITORY_ROOT / CANONICAL_G3_OUTPUT_ROOT
    ).resolve()
    if not allow_noncanonical_output_root and root != canonical_root:
        raise ValueError(
            "output root must remain the canonical G3 output root: "
            f"{canonical_root}"
        )
    source_tree_clean = _source_tree_clean()
    implementation_tree_hash = source_tree_hash()
    if implementation_tree_hash == "unknown":
        raise ValueError("canonical G3 smoke requires a resolvable implementation tree")
    if not allow_noncanonical_output_root and not source_tree_clean:
        raise ValueError("canonical G3 smoke requires a clean source tree")
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = root / "checkpoints" / "g3-smoke.pt"
    raw_log_path = root / "training-smoke.jsonl"
    provenance_path = root / "provenance.json"

    algorithm = SRMAPPOAlgorithm(
        config.uav_obs_dim,
        config.vehicle_obs_dim,
        config.critic_state_dim,
        config.uav_action_dim,
        config.vehicle_action_dim,
        stability_components=config.stability_components,
    )
    trainer = SRMAPPOTrainer(
        algorithm,
        learning_rate=config.learning_rate,
        value_coef=config.value_loss_coef,
        entropy_coef=config.entropy_coef,
        max_grad_norm=config.max_grad_norm,
    )
    environment = DevelopmentCooperativeEnv(seed=seed, config=config)
    source_tree_commit = _source_tree_commit()
    seed_manifest_provenance = scenario_seed_manifest_provenance()
    records: list[str] = []
    finite_loss_checks = True

    for update in range(updates):
        current = environment.reset()
        batch = RolloutBatch()
        for _ in range(min(config.rollout_horizon, environment.horizon)):
            details = algorithm.act(
                current["observations"],
                current["masks"],
                deterministic=False,
                return_details=True,
            )
            value = float(algorithm.value(current["critic_state"]).detach().cpu().reshape(-1)[0])
            next_state = environment.step(details["actions"])
            next_value = float(algorithm.value(next_state["critic_state"]).detach().cpu().reshape(-1)[0])
            batch.add(_transition(current, details, value, next_value, next_state))
            current = next_state
            if next_state["terminated"] or next_state["truncated"]:
                break
        batch.finish(config.gamma, config.gae_lambda)
        metrics = trainer.update(
            batch,
            epochs=config.ppo_epochs,
            progress=float(update + 1) / float(updates),
        )
        numeric_losses = [
            value
            for key, value in metrics.items()
            if "loss" in key and isinstance(value, (int, float))
        ]
        finite_losses = bool(numeric_losses) and all(np.isfinite(numeric_losses))
        finite_loss_checks = finite_loss_checks and finite_losses
        record = {
            "update": update + 1,
            "seed": int(seed),
            "config_hash": config.config_hash,
            "source_tree_commit": source_tree_commit,
            "source_tree_clean": source_tree_clean,
            "source_tree_hash": implementation_tree_hash,
            "training_partition": config.training_partition,
            "validation_scenarios_accessed": False,
            **seed_manifest_provenance,
            "rollout_steps": len(batch),
            "metrics": metrics,
            "finite_losses": finite_losses,
            "sealed_test_accessed": False,
            "battery_replenishment_enabled": False,
            "replenished_resource": "pesticide",
        }
        records.append(json.dumps(record, sort_keys=True, allow_nan=False))

    provenance = {
        "artifact_type": "g3_development_training_smoke",
        "config_hash": config.config_hash,
        "source_tree_commit": source_tree_commit,
        "source_tree_clean": source_tree_clean,
        "source_tree_hash": implementation_tree_hash,
        "training_partition": config.training_partition,
        "seed": int(seed),
        "updates": int(updates),
        "finite_loss_checks": bool(finite_loss_checks),
        "sealed_test_accessed": False,
        "validation_scenarios_accessed": False,
        **seed_manifest_provenance,
        "battery_replenishment_enabled": False,
        "replenished_resource": "pesticide",
    }
    save_checkpoint(
        checkpoint_path,
        algorithm,
        step=updates,
        provenance=provenance,
    )
    raw_log_path.parent.mkdir(parents=True, exist_ok=True)
    raw_log_path.write_text("\n".join(records) + "\n", encoding="utf-8")
    _write_json(provenance_path, provenance)
    return {
        "updates": int(updates),
        "seed": int(seed),
        "config_hash": config.config_hash,
        "source_tree_commit": provenance["source_tree_commit"],
        "finite_loss_checks": bool(finite_loss_checks),
        "sealed_test_accessed": False,
        "checkpoint": str(checkpoint_path),
        "raw_log": str(raw_log_path),
        "provenance": str(provenance_path),
    }


__all__ = [
    "CANONICAL_G3_OUTPUT_ROOT",
    "SOURCE_TREE_ROOTS",
    "run_training_smoke",
    "source_tree_hash",
]
