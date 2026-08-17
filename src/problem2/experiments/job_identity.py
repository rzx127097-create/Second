"""Immutable identity for one method/scale/seed/config/commit job."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
    source_tree_hash: str = ""
    git_dirty: bool = False

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
            "source_tree_hash": self.source_tree_hash,
            "git_dirty": self.git_dirty,
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
    source_tree_hash: str = "",
    git_dirty: bool = False,
) -> JobIdentity:
    payload = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = str(config_hash) if config_hash is not None else hashlib.sha256(payload).hexdigest()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
        raise ValueError("config_hash must be a SHA-256 hexadecimal digest")
    if execution_profile not in {"formal", "simulation", "smoke"}:
        raise ValueError("execution_profile must be formal, simulation or smoke")
    if int(target_updates) < 0 or int(rollout_horizon) < 0:
        raise ValueError("target_updates and rollout_horizon must be non-negative")
    if scenario_split not in {"train", "validation", "sealed_test"}:
        raise ValueError("scenario_split must be train, validation or sealed_test")
    if protocol_hash and (len(protocol_hash) != 64 or any(character not in "0123456789abcdef" for character in protocol_hash.lower())):
        raise ValueError("protocol_hash must be an empty value or SHA-256 hexadecimal digest")
    if source_tree_hash and (
        len(source_tree_hash) != 64
        or any(character not in "0123456789abcdef" for character in source_tree_hash.lower())
    ):
        raise ValueError("source_tree_hash must be an empty value or SHA-256 hexadecimal digest")
    if not str(family).strip() or not str(condition_id).strip():
        raise ValueError("family and condition_id must be non-empty")
    return JobIdentity(
        str(method), str(scale), int(training_seed), digest, str(git_commit),
        execution_profile, int(target_updates), int(rollout_horizon),
        str(family), str(condition_id), str(scenario_split), str(protocol_hash),
        str(source_tree_hash), bool(git_dirty),
    )


@dataclass(frozen=True)
class GitProvenance:
    commit: str
    source_tree_hash: str
    dirty: bool


def _git(args: list[str], cwd: str | None, *, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args], cwd=cwd, text=text,
        encoding="utf-8" if text else None,
        capture_output=True, check=False,
    )


def capture_git_provenance(cwd: str | None = None) -> GitProvenance:
    """Hash the commit plus every tracked/untracked source-tree difference."""

    commit_result = _git(["rev-parse", "HEAD"], cwd)
    if commit_result.returncode != 0 or not commit_result.stdout.strip():
        raise RuntimeError(f"unable to capture git commit: {commit_result.stderr.strip()}")
    commit = commit_result.stdout.strip()
    status_result = _git(["status", "--porcelain=v1", "--untracked-files=all"], cwd)
    diff_result = _git(["diff", "--binary", "HEAD", "--"], cwd, text=False)
    if status_result.returncode != 0 or diff_result.returncode != 0:
        raise RuntimeError("unable to capture Git source-tree state")
    digest = hashlib.sha256()
    digest.update(commit.encode("utf-8"))
    digest.update(b"\0")
    digest.update(status_result.stdout.encode("utf-8"))
    digest.update(b"\0")
    digest.update(diff_result.stdout)
    root_result = _git(["rev-parse", "--show-toplevel"], cwd)
    if root_result.returncode != 0:
        raise RuntimeError("unable to locate Git worktree root")
    root = Path(root_result.stdout.strip())
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z"], cwd, text=False)
    if untracked.returncode != 0:
        raise RuntimeError("unable to enumerate untracked source files")
    for raw_name in sorted(value for value in untracked.stdout.split(b"\0") if value):
        relative = raw_name.decode("utf-8")
        source = root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    dirty = bool(status_result.stdout.strip())
    return GitProvenance(commit, digest.hexdigest(), dirty)


def assert_clean_formal_source(provenance: GitProvenance) -> None:
    if provenance.dirty:
        raise ValueError(
            "formal execution requires a clean Git worktree; commit the exact tested source first"
        )


def capture_git_commit(cwd: str | None = None) -> str:
    """Capture the exact repository revision used for an immutable job."""
    return capture_git_provenance(cwd).commit


__all__ = [
    "GitProvenance",
    "JobIdentity",
    "assert_clean_formal_source",
    "capture_git_commit",
    "capture_git_provenance",
    "make_job_identity",
]
