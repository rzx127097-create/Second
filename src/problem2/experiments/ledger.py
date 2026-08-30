"""Append-only job ledger with replayed state and exclusive leases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from datetime import datetime, timezone
import os
import platform
from pathlib import Path
import re
import time
import uuid
from typing import Any

from .artifacts import append_jsonl


class LedgerError(RuntimeError):
    pass


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _validate_initial_provenance(event: dict[str, Any]) -> None:
    required = ("input_hash", "config_hash", "protocol_hash", "source_commit")
    if not set(required) <= set(event):
        raise LedgerError("initial pending provenance is incomplete")
    for field in ("input_hash", "config_hash", "protocol_hash"):
        value = event.get(field)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise LedgerError(f"initial pending provenance hash is invalid: {field}")
    source_commit = event.get("source_commit")
    if not isinstance(source_commit, str) or not _SHA1.fullmatch(source_commit):
        raise LedgerError("initial pending provenance hash is invalid: source_commit")
    for field in ("checkpoint_hash", "scenario_panel_hash"):
        if field in event:
            value = event.get(field)
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise LedgerError(f"initial pending provenance hash is invalid: {field}")


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
        enriched = {
            **event,
            "utc_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "host_id": platform.node() or "unknown",
            "process_id": os.getpid(),
            "artifact_hashes": dict(event.get("artifact_hashes") or {}),
        }
        append_jsonl(self.path, enriched)
        self._apply(enriched, replay=False)

    def _apply(self, event: dict[str, Any], *, replay: bool) -> None:
        identity = event.get("identity")
        if not isinstance(identity, str):
            raise LedgerError("ledger event identity is invalid")
        new_state = event.get("new_state")
        if new_state == JobState.PENDING.value and event.get("old_state") is None:
            if identity in self._jobs:
                raise LedgerError("duplicate initial pending event")
            _validate_initial_provenance(event)
            self._jobs[identity] = {
                "identity": identity,
                "input_hash": event.get("input_hash"),
                "config_hash": event.get("config_hash"),
                "protocol_hash": event.get("protocol_hash"),
                "source_commit": event.get("source_commit"),
                "checkpoint_hash": event.get("checkpoint_hash"),
                "scenario_panel_hash": event.get("scenario_panel_hash"),
                "state": JobState.PENDING,
                "attempt": 0,
            }
            return
        job = self._jobs.get(identity)
        if job is None:
            raise LedgerError("transition references unknown job")
        old_state = event.get("old_state")
        if old_state != job["state"].value:
            raise LedgerError("transition prior state mismatch")
        legal = {
            "pending": {"running", "stale"},
            "running": {"completed", "failed", "stale"},
            "failed": {"pending", "stale"},
            "completed": {"stale"},
            "stale": set(),
        }
        if new_state not in legal.get(old_state, set()):
            raise LedgerError("illegal ledger transition")
        prior_attempt = int(job["attempt"])
        attempt = event.get("attempt")
        if isinstance(attempt, bool) or not isinstance(attempt, int):
            raise LedgerError("transition attempt is invalid")
        if new_state == "running" and attempt != prior_attempt + 1:
            raise LedgerError("running attempt is not monotonic")
        if new_state in {"completed", "failed", "stale"} and attempt != prior_attempt:
            raise LedgerError("terminal attempt changed")
        if new_state == "pending" and attempt != prior_attempt:
            raise LedgerError("retry attempt changed before acquisition")
        if new_state == "running":
            if not isinstance(event.get("worker_id"), str) or not event["worker_id"] or not isinstance(event.get("lease_id"), str) or not event["lease_id"]:
                raise LedgerError("running transition lease metadata is missing")
            if not isinstance(event.get("expires_at"), (int, float)) or not math.isfinite(float(event["expires_at"])):
                raise LedgerError("running lease expiry is invalid")
        if new_state in {"completed", "failed", "stale"} and old_state == "running":
            if event.get("lease_id") != getattr(job.get("lease"), "lease_id", None) or event.get("worker_id") != getattr(job.get("lease"), "worker_id", None):
                raise LedgerError("terminal lease ownership mismatch")
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
            fields = ("input_hash", "config_hash", "protocol_hash", "source_commit", "checkpoint_hash", "scenario_panel_hash")
            if {key: existing.get(key) for key in fields} != {key: job.get(key) for key in fields}:
                raise LedgerError("identity input drift")
            return
        required = {"identity", "input_hash", "config_hash", "protocol_hash", "source_commit"}
        if set(job) < required:
            raise LedgerError("job is missing provenance hashes")
        _validate_initial_provenance(job)
        self._append({"event": "transition", "identity": identity, "old_state": None, "new_state": "pending", "attempt": 0, **{key: value for key, value in job.items() if key != "identity"}})

    def acquire(self, identity: str, *, worker_id: str, lease_seconds: float = 3600.0) -> Lease:
        job = self._job(identity)
        if job["state"] == JobState.RUNNING and identity in self._leases:
            raise LedgerError("active lease already exists")
        if job["state"] is not JobState.PENDING:
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

    def complete(
        self,
        identity: str,
        *,
        lease_id: str,
        worker_id: str,
        artifact_hashes: dict[str, str] | None = None,
    ) -> None:
        lease = self._check_lease(identity, lease_id, worker_id)
        self._append({"event": "transition", "identity": identity, "old_state": "running", "new_state": "completed", "attempt": lease.attempt, "lease_id": lease_id, "worker_id": worker_id, "artifact_hashes": artifact_hashes or {}})

    def fail(
        self,
        identity: str,
        *,
        lease_id: str,
        worker_id: str,
        reason: str,
        artifact_hashes: dict[str, str] | None = None,
    ) -> None:
        lease = self._check_lease(identity, lease_id, worker_id)
        self._append({"event": "transition", "identity": identity, "old_state": "running", "new_state": "failed", "attempt": lease.attempt, "lease_id": lease_id, "worker_id": worker_id, "reason": reason, "artifact_hashes": artifact_hashes or {}})

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
        self._append({"event": "transition", "identity": identity, "old_state": "failed", "new_state": "pending", "attempt": int(job["attempt"]), "reason": "same-identity retry"})
        return self.acquire(identity, worker_id=worker_id)

    def requeue(self, identity: str, *, input_hash: str, config_hash: str | None = None, protocol_hash: str | None = None, source_commit: str | None = None, checkpoint_hash: str | None = None, scenario_panel_hash: str | None = None) -> None:
        """Return a failed identity to pending without acquiring a lease.

        The scheduler uses this two-phase form when recovery must load a
        checkpoint before claiming the next worker lease.
        """
        job = self._job(identity)
        if job["state"] is JobState.STALE:
            raise LedgerError("stale job cannot be requeued")
        observed = {"input_hash": input_hash, "config_hash": config_hash, "protocol_hash": protocol_hash, "source_commit": source_commit, "checkpoint_hash": checkpoint_hash, "scenario_panel_hash": scenario_panel_hash}
        drift = input_hash != job["input_hash"] or any(value is not None and value != job.get(key) for key, value in observed.items() if key != "input_hash")
        if drift:
            self.mark_stale(identity, reason="input/provenance drift", observed_input_hash=input_hash)
            raise LedgerError("input or provenance drift marks job stale")
        if job["state"] is not JobState.FAILED:
            raise LedgerError("only failed jobs may be requeued")
        self._append({"event": "transition", "identity": identity, "old_state": "failed", "new_state": "pending", "attempt": int(job["attempt"]), "reason": "same-identity recovery requeue"})

    def mark_stale(self, identity: str, *, reason: str, observed_input_hash: str | None = None) -> None:
        job = self._job(identity)
        if job["state"] is JobState.STALE:
            return
        event = {"event": "transition", "identity": identity, "old_state": job["state"].value, "new_state": "stale", "attempt": int(job["attempt"]), "reason": reason, "observed_input_hash": observed_input_hash}
        if job["state"] is JobState.RUNNING and job.get("lease") is not None:
            event.update({"lease_id": job["lease"].lease_id, "worker_id": job["lease"].worker_id})
        self._append(event)

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
