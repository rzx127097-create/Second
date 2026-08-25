"""Append-only job ledger with replayed state and exclusive leases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import time
import uuid
from typing import Any

from .artifacts import append_jsonl


class LedgerError(RuntimeError):
    pass


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


@dataclass(frozen=True)
class Lease:
    identity: str
    attempt: int
    lease_id: str
    worker_id: str
    expires_at: float


class AppendOnlyLedger:
    """JSONL event log; state is rebuilt from immutable transition events."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, dict[str, Any]] = {}
        self._leases: dict[str, Lease] = {}
        self._replay()

    def _replay(self) -> None:
        if not self.path.exists():
            return
        for line_number, line in enumerate(self.path.read_bytes().splitlines(), 1):
            try:
                event = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LedgerError(f"invalid ledger event at line {line_number}") from exc
            self._apply(event, replay=True)

    def _append(self, event: dict[str, Any]) -> None:
        append_jsonl(self.path, event)
        self._apply(event, replay=False)

    def _apply(self, event: dict[str, Any], *, replay: bool) -> None:
        identity = event.get("identity")
        if not isinstance(identity, str):
            raise LedgerError("ledger event identity is invalid")
        new_state = event.get("new_state")
        if new_state == JobState.PENDING.value and event.get("old_state") is None:
            self._jobs[identity] = {
                "identity": identity,
                "input_hash": event.get("input_hash"),
                "config_hash": event.get("config_hash"),
                "protocol_hash": event.get("protocol_hash"),
                "source_commit": event.get("source_commit"),
                "state": JobState.PENDING,
                "attempt": 0,
            }
            return
        job = self._jobs.get(identity)
        if job is None:
            raise LedgerError("transition references unknown job")
        if new_state is not None:
            job["state"] = JobState(new_state)
        if "attempt" in event:
            job["attempt"] = int(event["attempt"])
        lease_id = event.get("lease_id")
        if new_state == JobState.RUNNING.value and lease_id:
            lease = Lease(identity, int(event["attempt"]), lease_id, event["worker_id"], float(event["expires_at"]))
            self._leases[identity] = lease
            job["lease"] = lease
        elif new_state in {JobState.COMPLETED.value, JobState.FAILED.value, JobState.STALE.value}:
            self._leases.pop(identity, None)
            job.pop("lease", None)

    def _job(self, identity: str) -> dict[str, Any]:
        try:
            return self._jobs[identity]
        except KeyError as exc:
            raise LedgerError("unknown job identity") from exc

    def register(self, job: dict[str, Any]) -> None:
        identity = job.get("identity")
        if not isinstance(identity, str) or not identity:
            raise LedgerError("job identity is required")
        if identity in self._jobs:
            existing = self._jobs[identity]
            if {existing.get(key) for key in ("input_hash", "config_hash", "protocol_hash", "source_commit")} != {job.get(key) for key in ("input_hash", "config_hash", "protocol_hash", "source_commit")}:
                raise LedgerError("identity input drift")
            return
        required = {"identity", "input_hash", "config_hash", "protocol_hash", "source_commit"}
        if set(job) < required:
            raise LedgerError("job is missing provenance hashes")
        self._append({"event": "transition", "identity": identity, "old_state": None, "new_state": "pending", "attempt": 0, **{key: job[key] for key in required if key != "identity"}})

    def acquire(self, identity: str, *, worker_id: str, lease_seconds: float = 3600.0) -> Lease:
        job = self._job(identity)
        if job["state"] == JobState.RUNNING and identity in self._leases:
            raise LedgerError("active lease already exists")
        if job["state"] not in {JobState.PENDING, JobState.FAILED}:
            raise LedgerError(f"job is {job['state'].value}, cannot acquire")
        attempt = int(job["attempt"]) + 1
        lease = Lease(identity, attempt, uuid.uuid4().hex, worker_id, time.time() + float(lease_seconds))
        self._append({"event": "transition", "identity": identity, "old_state": job["state"].value, "new_state": "running", "attempt": attempt, "lease_id": lease.lease_id, "worker_id": worker_id, "expires_at": lease.expires_at})
        return lease

    def _check_lease(self, identity: str, lease_id: str, worker_id: str) -> Lease:
        lease = self._leases.get(identity)
        if lease is None or lease.lease_id != lease_id or lease.worker_id != worker_id:
            raise LedgerError("lease ownership mismatch")
        return lease

    def complete(self, identity: str, *, lease_id: str, worker_id: str) -> None:
        lease = self._check_lease(identity, lease_id, worker_id)
        self._append({"event": "transition", "identity": identity, "old_state": "running", "new_state": "completed", "attempt": lease.attempt, "lease_id": lease_id, "worker_id": worker_id})

    def fail(self, identity: str, *, lease_id: str, worker_id: str, reason: str) -> None:
        lease = self._check_lease(identity, lease_id, worker_id)
        self._append({"event": "transition", "identity": identity, "old_state": "running", "new_state": "failed", "attempt": lease.attempt, "lease_id": lease_id, "worker_id": worker_id, "reason": reason})

    def retry(self, identity: str, *, worker_id: str, input_hash: str, config_hash: str | None = None, protocol_hash: str | None = None, source_commit: str | None = None, checkpoint_hash: str | None = None, scenario_panel_hash: str | None = None) -> Lease:
        job = self._job(identity)
        if job["state"] is JobState.STALE:
            raise LedgerError("stale job cannot be retried")
        observed = {"input_hash": input_hash, "config_hash": config_hash, "protocol_hash": protocol_hash, "source_commit": source_commit, "checkpoint_hash": checkpoint_hash, "scenario_panel_hash": scenario_panel_hash}
        drift = input_hash != job["input_hash"] or any(value is not None and value != job.get(key) for key, value in observed.items() if key != "input_hash")
        if drift:
            self.mark_stale(identity, reason="input/provenance drift", observed_input_hash=input_hash)
            raise LedgerError("input or provenance drift marks job stale")
        if job["state"] is not JobState.FAILED:
            raise LedgerError("only failed jobs may be retried")
        return self.acquire(identity, worker_id=worker_id)

    def mark_stale(self, identity: str, *, reason: str, observed_input_hash: str | None = None) -> None:
        job = self._job(identity)
        if job["state"] is JobState.STALE:
            return
        self._append({"event": "transition", "identity": identity, "old_state": job["state"].value, "new_state": "stale", "attempt": int(job["attempt"]), "reason": reason, "observed_input_hash": observed_input_hash})

    def current(self, identity: str) -> Any:
        return _StateView(self._job(identity))

    def events(self, identity: str) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if json.loads(line).get("identity") == identity]


class _StateView:
    def __init__(self, record: dict[str, Any]):
        self.state = record["state"]
        self.attempt = record["attempt"]
        self.identity = record["identity"]
        self.input_hash = record.get("input_hash")
        self.lease = record.get("lease")


__all__ = ["AppendOnlyLedger", "JobState", "LedgerError", "Lease"]
