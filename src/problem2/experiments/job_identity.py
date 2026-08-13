"""Immutable identity for one method/scale/seed/config/commit job."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobIdentity:
    method: str
    scale: str
    training_seed: int
    config_hash: str
    git_commit: str

    def __str__(self) -> str:
        return f"{self.method}+{self.scale}+{self.training_seed}+{self.config_hash[:12]}+{self.git_commit[:12]}"


def make_job_identity(method: str, scale: str, training_seed: int, config: Any, *, git_commit: str) -> JobIdentity:
    payload = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return JobIdentity(str(method), str(scale), int(training_seed), hashlib.sha256(payload).hexdigest(), str(git_commit))
