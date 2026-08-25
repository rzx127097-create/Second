"""Deterministic scheduling primitives; execution remains outside Task 8."""

from __future__ import annotations

import math
import json
import os
from pathlib import Path

from problem2.experiments.ledger import Lease, LedgerError


def deterministic_interleave(jobs: list[dict]) -> list[dict]:
    """Round-robin sorted scale/seed blocks, preserving method ordering within blocks."""
    if not isinstance(jobs, list):
        raise TypeError("jobs must be a list")
    groups: dict[tuple[str, int], list[dict]] = {}
    method_order: dict[str, int] = {}
    for job in jobs:
        method = str(job.get("method", ""))
        method_order.setdefault(method, len(method_order))
        groups.setdefault((str(job.get("scale", "")), int(job.get("training_seed", 0))), []).append(job)
    result: list[dict] = []
    for key in sorted(groups):
        block = sorted(groups[key], key=lambda item: (method_order[str(item.get("method", ""))], str(item.get("identity", ""))))
        result.extend(block)
    return result


class GpuTrainingLease:
    """Process-local single-GPU lease used by the future G6 scheduler."""

    def __init__(self, coordination_path: Path | None = None):
        self._active: Lease | None = None
        self.history: list[dict] = []
        self.coordination_path = Path(coordination_path) if coordination_path is not None else None

    def acquire(self, identity: str, *, worker_id: str) -> Lease:
        if self._active is not None:
            raise LedgerError("GPU lease is already active")
        if not isinstance(identity, str) or not identity or not isinstance(worker_id, str) or not worker_id:
            raise LedgerError("GPU lease identity/worker is invalid")
        lease = Lease(identity, 1, f"gpu-{len(self.history) + 1}", worker_id, 0.0)
        if self.coordination_path is not None:
            self.coordination_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(self.coordination_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump({"identity": identity, "worker_id": worker_id, "lease_id": lease.lease_id}, handle, sort_keys=True)
            except FileExistsError as exc:
                raise LedgerError("GPU lease is already active") from exc
        self._active = lease
        return lease

    def release(self, lease_id: str, *, peak_memory_bytes: int, runtime_seconds: float, environment: str | None = None) -> None:
        if self._active is None or self._active.lease_id != lease_id:
            raise LedgerError("GPU lease ownership mismatch")
        if isinstance(peak_memory_bytes, bool) or not isinstance(peak_memory_bytes, (int, float)) or not isinstance(runtime_seconds, (int, float)):
            raise LedgerError("runtime telemetry must be numeric")
        if not math.isfinite(float(peak_memory_bytes)) or not math.isfinite(float(runtime_seconds)):
            raise LedgerError("runtime telemetry must be finite")
        if peak_memory_bytes < 0 or runtime_seconds < 0:
            raise LedgerError("runtime telemetry must be non-negative")
        self.history.append({"identity": self._active.identity, "attempt": self._active.attempt, "lease_id": lease_id, "worker_id": self._active.worker_id, "peak_memory_bytes": peak_memory_bytes, "runtime_seconds": runtime_seconds, "environment": environment})
        self._active = None
        if self.coordination_path is not None:
            try:
                self.coordination_path.unlink()
            except FileNotFoundError:
                raise LedgerError("GPU coordination lease disappeared")


__all__ = ["deterministic_interleave", "GpuTrainingLease"]
