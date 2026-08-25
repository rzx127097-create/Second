"""Deterministic scheduling primitives; execution remains outside Task 8."""

from __future__ import annotations

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

    def __init__(self):
        self._active: Lease | None = None
        self.history: list[dict] = []

    def acquire(self, identity: str, *, worker_id: str) -> Lease:
        if self._active is not None:
            raise LedgerError("GPU lease is already active")
        lease = Lease(identity, 1, f"gpu-{len(self.history) + 1}", worker_id, 0.0)
        self._active = lease
        return lease

    def release(self, lease_id: str, *, peak_memory_bytes: int, runtime_seconds: float, environment: str | None = None) -> None:
        if self._active is None or self._active.lease_id != lease_id:
            raise LedgerError("GPU lease ownership mismatch")
        if peak_memory_bytes < 0 or runtime_seconds < 0:
            raise LedgerError("runtime telemetry must be non-negative")
        self.history.append({"identity": self._active.identity, "attempt": self._active.attempt, "lease_id": lease_id, "worker_id": self._active.worker_id, "peak_memory_bytes": peak_memory_bytes, "runtime_seconds": runtime_seconds, "environment": environment})
        self._active = None


__all__ = ["deterministic_interleave", "GpuTrainingLease"]
