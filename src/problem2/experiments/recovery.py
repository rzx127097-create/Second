"""Atomic job checkpoints and identity-preserving retries."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .runner import JobRecord, JobRunner


def atomic_checkpoint(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(temp, target)
    return target


def load_checkpoint(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def retry_failed_job(record: JobRecord, runner: JobRunner, checkpoint_path: str | Path) -> JobRecord:
    if record.status != "failed":
        raise ValueError("only failed jobs may be retried")
    result = runner.run(record)
    if result.status == "completed":
        atomic_checkpoint(checkpoint_path, {"identity": str(record.identity), **(result.result or {})})
    return result
