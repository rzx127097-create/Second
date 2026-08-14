"""Immutable identity for one method/scale/seed/config/commit job."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobIdentity:
    method: str
    scale: str
    training_seed: int
    config_hash: str
    git_commit: str
    execution_profile: str = "formal"
    target_updates: int = 0
    rollout_horizon: int = 0
    family: str = "main_comparison"
    condition_id: str = "direct"
    scenario_split: str = "train"
    protocol_hash: str = ""

    @property
    def job_id(self) -> str:
        """Stable filesystem-safe identifier for exactly one immutable job."""
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "scale": self.scale,
            "training_seed": self.training_seed,
            "config_hash": self.config_hash,
            "git_commit": self.git_commit,
            "execution_profile": self.execution_profile,
            "target_updates": self.target_updates,
            "rollout_horizon": self.rollout_horizon,
            "family": self.family,
            "condition_id": self.condition_id,
            "scenario_split": self.scenario_split,
            "protocol_hash": self.protocol_hash,
        }

    def __str__(self) -> str:
        return f"{self.method}+{self.scale}+{self.training_seed}+{self.config_hash[:12]}+{self.git_commit[:12]}"


def make_job_identity(
    method: str,
    scale: str,
    training_seed: int,
    config: Any,
    *,
    git_commit: str,
    config_hash: str | None = None,
    execution_profile: str = "formal",
    target_updates: int = 0,
    rollout_horizon: int = 0,
    family: str = "main_comparison",
    condition_id: str = "direct",
    scenario_split: str = "train",
    protocol_hash: str = "",
) -> JobIdentity:
    payload = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = str(config_hash) if config_hash is not None else hashlib.sha256(payload).hexdigest()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
        raise ValueError("config_hash must be a SHA-256 hexadecimal digest")
    if execution_profile not in {"formal", "smoke"}:
        raise ValueError("execution_profile must be formal or smoke")
    if int(target_updates) < 0 or int(rollout_horizon) < 0:
        raise ValueError("target_updates and rollout_horizon must be non-negative")
    if scenario_split not in {"train", "validation", "sealed_test"}:
        raise ValueError("scenario_split must be train, validation or sealed_test")
    if protocol_hash and (len(protocol_hash) != 64 or any(character not in "0123456789abcdef" for character in protocol_hash.lower())):
        raise ValueError("protocol_hash must be an empty value or SHA-256 hexadecimal digest")
    if not str(family).strip() or not str(condition_id).strip():
        raise ValueError("family and condition_id must be non-empty")
    return JobIdentity(
        str(method), str(scale), int(training_seed), digest, str(git_commit),
        execution_profile, int(target_updates), int(rollout_horizon),
        str(family), str(condition_id), str(scenario_split), str(protocol_hash),
    )


def capture_git_commit(cwd: str | None = None) -> str:
    """Capture the exact repository revision used for an immutable job."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"unable to capture git commit: {result.stderr.strip()}")
    return result.stdout.strip()
