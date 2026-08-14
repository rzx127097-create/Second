"""Persisted immutable experiment jobs and traceable raw rows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import traceback
from typing import Any, Callable

from .job_identity import JobIdentity


@dataclass
class JobRecord:
    identity: JobIdentity
    status: str = "pending"
    attempts: int = 0
    checkpoint_path: Path | None = None
    result: Any = None
    error: str | None = None

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
        )
        if str(payload["job_id"]) != identity.job_id:
            raise ValueError("job record identity hash mismatch")
        return cls(
            identity=identity,
            status=str(payload.get("status", "pending")),
            attempts=int(payload.get("attempts", 0)),
            checkpoint_path=Path(payload["checkpoint_path"]) if payload.get("checkpoint_path") else None,
            error=str(payload["error"]) if payload.get("error") is not None else None,
        )


class JobRunner:
    def __init__(
        self,
        worker: Callable[[JobRecord], Any],
        *,
        max_attempts: int = 2,
        record_path: str | Path | None = None,
        checkpoint_validator: Callable[[Path], Any] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.worker = worker
        self.max_attempts = int(max_attempts)
        self.record_path = Path(record_path) if record_path is not None else None
        self.checkpoint_validator = checkpoint_validator

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
                    self._validate_checkpoint(record.checkpoint_path)
                except Exception as exc:  # noqa: BLE001 - preserve checkpoint diagnosis
                    record.status = "failed"
                    record.error = "".join(traceback.format_exception(exc)).strip()
                    self._persist(record)
            return record
        if record.status not in {"pending", "failed"}:
            raise ValueError(f"job cannot run from status: {record.status}")
        if record.attempts >= self.max_attempts:
            record.status = "failed"
            record.error = record.error or f"retry limit reached ({self.max_attempts} attempts)"
            self._persist(record)
            return record
        record.status = "running"
        record.attempts += 1
        record.error = None
        self._persist(record)
        try:
            record.result = self.worker(record)
            if isinstance(record.result, dict) and record.result.get("checkpoint_path"):
                record.checkpoint_path = Path(str(record.result["checkpoint_path"]))
            if record.checkpoint_path is not None and not record.checkpoint_path.is_file():
                raise FileNotFoundError(f"checkpoint is missing or inaccessible: {record.checkpoint_path}")
            if record.checkpoint_path is not None:
                self._validate_checkpoint(record.checkpoint_path)
            record.status = "completed"
        except Exception as exc:  # noqa: BLE001 - persisted job failure
            record.error = "".join(traceback.format_exception(exc)).strip()
            record.status = "failed"
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
        transferred_l = sum(
            float(event.get("amount_l", 0.0))
            for event in episode.events
            if event.get("event_type") in {"pesticide_transfer", "transfer"}
        )
        rows.append({
            **row,
            "run_id": f"{record.job_id}:{index}",
            "update": int(index) + 1,
            "method": record.identity.method,
            "scale": record.identity.scale,
            "training_seed": record.identity.training_seed,
            "scenario_id": row.get("scenario_id") or record.identity.scale,
            "split": split,
            "config_hash": record.identity.config_hash,
            "git_commit": record.identity.git_commit,
            "family": record.identity.family,
            "condition_id": record.identity.condition_id,
            "protocol_hash": record.identity.protocol_hash,
            "intervention_id": row.get("intervention_id", record.identity.condition_id),
            "intervention_hash": row.get("intervention_hash", ""),
            "transferred_l": transferred_l,
        })
    return rows
