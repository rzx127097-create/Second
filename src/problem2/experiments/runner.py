"""Small job runner with explicit lifecycle states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .job_identity import JobIdentity


@dataclass
class JobRecord:
    identity: JobIdentity
    status: str = "pending"
    attempts: int = 0
    result: Any = None
    error: str | None = None


class JobRunner:
    def __init__(self, worker: Callable[[JobRecord], Any]) -> None:
        self.worker = worker

    def run(self, record: JobRecord) -> JobRecord:
        record.status = "running"
        record.attempts += 1
        try:
            record.result = self.worker(record)
            record.status = "completed"
        except Exception as exc:  # noqa: BLE001 - persisted job failure
            record.error = repr(exc)
            record.status = "failed"
        return record
