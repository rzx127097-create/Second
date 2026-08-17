"""Persisted immutable experiment jobs and traceable raw rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import socket
import traceback
from typing import Any, Callable

from .job_identity import JobIdentity
from .process_liveness import pid_is_alive


@dataclass
class JobRecord:
    identity: JobIdentity
    status: str = "pending"
    attempts: int = 0
    checkpoint_path: Path | None = None
    result: Any = None
    error: str | None = None
    owner_pid: int | None = None
    owner_host: str | None = None
    lease_started_at: str | None = None
    checkpoint_sha256: str | None = None
    checkpoint_step: int | None = None

    @property
    def job_id(self) -> str:
        return self.identity.job_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            **self.identity.to_dict(),
            "status": self.status,
            "attempts": self.attempts,
            "checkpoint_path": str(self.checkpoint_path) if self.checkpoint_path is not None else None,
            "error": self.error,
            "owner_pid": self.owner_pid,
            "owner_host": self.owner_host,
            "lease_started_at": self.lease_started_at,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_step": self.checkpoint_step,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        identity = JobIdentity(
            method=str(payload["method"]),
            scale=str(payload["scale"]),
            training_seed=int(payload["training_seed"]),
            config_hash=str(payload["config_hash"]),
            git_commit=str(payload["git_commit"]),
            execution_profile=str(payload.get("execution_profile", "formal")),
            target_updates=int(payload.get("target_updates", 0)),
            rollout_horizon=int(payload.get("rollout_horizon", 0)),
            family=str(payload.get("family", "main_comparison")),
            condition_id=str(payload.get("condition_id", "direct")),
            scenario_split=str(payload.get("scenario_split", "train")),
            protocol_hash=str(payload.get("protocol_hash", "")),
            source_tree_hash=str(payload.get("source_tree_hash", "")),
            git_dirty=bool(payload.get("git_dirty", False)),
        )
        if str(payload["job_id"]) != identity.job_id:
            raise ValueError("job record identity hash mismatch")
        return cls(
            identity=identity,
            status=str(payload.get("status", "pending")),
            attempts=int(payload.get("attempts", 0)),
            checkpoint_path=Path(payload["checkpoint_path"]) if payload.get("checkpoint_path") else None,
            error=str(payload["error"]) if payload.get("error") is not None else None,
            owner_pid=int(payload["owner_pid"]) if payload.get("owner_pid") is not None else None,
            owner_host=str(payload["owner_host"]) if payload.get("owner_host") is not None else None,
            lease_started_at=str(payload["lease_started_at"]) if payload.get("lease_started_at") is not None else None,
            checkpoint_sha256=str(payload["checkpoint_sha256"]) if payload.get("checkpoint_sha256") is not None else None,
            checkpoint_step=int(payload["checkpoint_step"]) if payload.get("checkpoint_step") is not None else None,
        )


class JobRunner:
    def __init__(
        self,
        worker: Callable[[JobRecord], Any],
        *,
        max_attempts: int = 2,
        record_path: str | Path | None = None,
        checkpoint_validator: Callable[[Path], Any] | None = None,
        running_job_is_stale: Callable[[JobRecord], bool] | None = None,
        lease_timeout_s: float = 86_400.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if not isinstance(lease_timeout_s, (int, float)) or float(lease_timeout_s) <= 0:
            raise ValueError("lease_timeout_s must be positive")
        self.worker = worker
        self.max_attempts = int(max_attempts)
        self.record_path = Path(record_path) if record_path is not None else None
        self.checkpoint_validator = checkpoint_validator
        self.lease_timeout_s = float(lease_timeout_s)
        self.running_job_is_stale = running_job_is_stale or self._running_job_is_stale

    def _running_job_is_stale(self, record: JobRecord) -> bool:
        if record.owner_pid is None or record.owner_host is None:
            return True
        if record.owner_host != socket.gethostname():
            if record.lease_started_at is None:
                return True
            try:
                started = datetime.fromisoformat(record.lease_started_at)
            except ValueError:
                return True
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - started).total_seconds()
            return age_s > self.lease_timeout_s
        return not pid_is_alive(record.owner_pid)

    @staticmethod
    def _validate_checkpoint_payload(path: Path) -> None:
        """Validate the canonical checkpoint envelope before trusting completion."""
        import pickle
        from collections.abc import Mapping

        try:
            try:
                import torch
            except ImportError:
                with path.open("rb") as handle:
                    payload = pickle.load(handle)
            else:
                payload = torch.load(path, map_location="cpu", weights_only=False)
        except Exception as exc:  # noqa: BLE001 - normalize corrupt persistence
            raise ValueError(f"invalid checkpoint payload: {path}") from exc
        if not isinstance(payload, Mapping) or type(payload.get("format")) is not int or payload.get("format") != 2:
            raise ValueError(f"invalid checkpoint payload: {path}")
        if type(payload.get("step")) is not int or payload.get("step") < 0 or not isinstance(payload.get("algorithm"), Mapping):
            raise ValueError(f"invalid checkpoint payload: {path}")

    def _validate_checkpoint(self, path: Path) -> None:
        if self.checkpoint_validator is not None:
            self.checkpoint_validator(path)
        else:
            self._validate_checkpoint_payload(path)

    def _persist(self, record: JobRecord) -> None:
        if self.record_path is not None:
            from .recovery import save_job_record

            save_job_record(self.record_path, record)

    def run(self, record: JobRecord) -> JobRecord:
        if record.status == "completed":
            if record.checkpoint_path is None:
                record.status = "failed"
                record.error = "checkpoint path is missing for completed job"
                self._persist(record)
            elif not record.checkpoint_path.is_file():
                record.status = "failed"
                record.error = f"checkpoint is missing or inaccessible: {record.checkpoint_path}"
                self._persist(record)
            elif record.checkpoint_path is not None:
                try:
                    if (
                        record.checkpoint_sha256 is not None
                        and hashlib.sha256(record.checkpoint_path.read_bytes()).hexdigest()
                        != record.checkpoint_sha256
                    ):
                        raise ValueError("checkpoint SHA-256 differs from the completed job record")
                    self._validate_checkpoint(record.checkpoint_path)
                except Exception as exc:  # noqa: BLE001 - preserve checkpoint diagnosis
                    record.status = "failed"
                    record.error = "".join(traceback.format_exception(exc)).strip()
                    self._persist(record)
            return record
        if record.status == "running":
            if not self.running_job_is_stale(record):
                raise ValueError("job has an active lease and cannot be stolen")
            record.status = "stale"
            record.error = "previous worker lease is stale; resuming from committed checkpoint"
            self._persist(record)
        if record.status not in {"pending", "failed", "stale"}:
            raise ValueError(f"job cannot run from status: {record.status}")
        if record.attempts >= self.max_attempts:
            record.status = "failed"
            record.error = record.error or f"retry limit reached ({self.max_attempts} attempts)"
            self._persist(record)
            return record
        record.status = "running"
        record.attempts += 1
        record.error = None
        record.owner_pid = os.getpid()
        record.owner_host = socket.gethostname()
        record.lease_started_at = datetime.now(timezone.utc).isoformat()
        self._persist(record)
        try:
            record.result = self.worker(record)
            if isinstance(record.result, dict) and record.result.get("checkpoint_path"):
                record.checkpoint_path = Path(str(record.result["checkpoint_path"]))
            if isinstance(record.result, dict) and record.result.get("checkpoint_step") is not None:
                record.checkpoint_step = int(record.result["checkpoint_step"])
            if record.checkpoint_path is not None and not record.checkpoint_path.is_file():
                raise FileNotFoundError(f"checkpoint is missing or inaccessible: {record.checkpoint_path}")
            if record.checkpoint_path is not None:
                self._validate_checkpoint(record.checkpoint_path)
                record.checkpoint_sha256 = hashlib.sha256(
                    record.checkpoint_path.read_bytes()
                ).hexdigest()
            record.status = "completed"
        except Exception as exc:  # noqa: BLE001 - persisted job failure
            record.error = "".join(traceback.format_exception(exc)).strip()
            record.status = "failed"
        record.owner_pid = None
        record.owner_host = None
        self._persist(record)
        return record


def evaluate_job(
    policy: Any,
    scenario_factory: Any,
    *,
    scenarios: Any,
    split: str,
    deterministic: bool = True,
    measure_decision_time: bool = False,
) -> list[Any]:
    """Small runner entry point for the shared deterministic policy protocol."""
    from .evaluation import evaluate_policy

    return evaluate_policy(
        policy, scenario_factory, scenarios=scenarios, split=split,
        deterministic=deterministic, measure_decision_time=measure_decision_time,
    )


def traceable_episode_rows(records: list[Any], record: JobRecord, *, split: str, index_offset: int = 0) -> list[dict[str, Any]]:
    """Enrich physical episode metrics at the experiment boundary, not in the model."""
    rows: list[dict[str, Any]] = []
    for index, episode in enumerate(records, start=int(index_offset)):
        row = dict(episode.to_row())
        scenario_id = str(row.get("scenario_id") or record.identity.scale)
        run_id = f"{record.job_id}:{index}"
        if split != "train":
            run_id = f"{run_id}:{scenario_id}"
        transferred_l = sum(
            float(event.get("amount_l", 0.0))
            for event in episode.events
            if event.get("event_type") in {"pesticide_transfer", "transfer"}
        )
        rows.append({
            **row,
            "run_id": run_id,
            "job_id": record.job_id,
            "update": int(index) + 1,
            "method": record.identity.method,
            "scale": record.identity.scale,
            "training_seed": record.identity.training_seed,
            "scenario_id": scenario_id,
            "split": split,
            "config_hash": record.identity.config_hash,
            "git_commit": record.identity.git_commit,
            "source_tree_hash": record.identity.source_tree_hash,
            "git_dirty": record.identity.git_dirty,
            "execution_profile": record.identity.execution_profile,
            "target_updates": record.identity.target_updates,
            "rollout_horizon": record.identity.rollout_horizon,
            "checkpoint_sha256": record.checkpoint_sha256,
            "checkpoint_step": record.checkpoint_step,
            "family": record.identity.family,
            "condition_id": record.identity.condition_id,
            "protocol_hash": record.identity.protocol_hash,
            "intervention_id": row.get("intervention_id", record.identity.condition_id),
            "intervention_hash": row.get("intervention_hash", ""),
            "transferred_l": transferred_l,
        })
    return rows
