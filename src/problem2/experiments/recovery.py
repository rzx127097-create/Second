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


def save_job_record(path: str | Path, record: JobRecord) -> Path:
    """Atomically persist a JSON job record with its immutable identity."""
    return atomic_checkpoint(path, record.to_dict())


def load_job_record(path: str | Path) -> JobRecord:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"job record does not exist: {source}")
    try:
        payload = load_checkpoint(source)
        if not isinstance(payload, dict):
            raise ValueError("job record must be a JSON object")
        return JobRecord.from_dict(payload)
    except Exception as exc:  # noqa: BLE001 - distinguish persistence corruption
        raise ValueError(f"invalid job record: {source}") from exc


def retry_failed_job(record: JobRecord, runner: JobRunner, checkpoint_path: str | Path | None = None) -> JobRecord:
    if record.status != "failed":
        raise ValueError("only failed jobs may be retried")
    result = runner.run(record)
    if result.status == "completed" and checkpoint_path is not None and result.checkpoint_path is None:
        atomic_checkpoint(checkpoint_path, {"identity": str(record.identity), **(result.result or {})})
        result.checkpoint_path = Path(checkpoint_path)
        if runner.record_path is not None:
            save_job_record(runner.record_path, result)
    return result
