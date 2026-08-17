"""Validation freeze and consumable sealed-test access ledger."""

from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import time
from typing import Any, Mapping, Sequence
from uuid import uuid4

from .runner import JobRecord
from .process_liveness import pid_is_alive


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _timestamp_age_s(value: object) -> float:
    try:
        created = datetime.fromisoformat(str(value))
    except ValueError:
        return float("inf")
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - created).total_seconds())


def _lock_is_stale(path: Path, *, stale_after_s: float) -> bool:
    try:
        payload = _read_json(path)
    except ValueError:
        try:
            return time.time() - path.stat().st_mtime > stale_after_s
        except OSError:
            return True
    if str(payload.get("owner_host", "")) == socket.gethostname():
        try:
            return not pid_is_alive(int(payload.get("owner_pid")))
        except (TypeError, ValueError):
            return True
    return _timestamp_age_s(payload.get("created_at")) > stale_after_s


@contextmanager
def _ledger_lock(
    unlock_path: Path,
    *,
    timeout_s: float = 10.0,
    stale_after_s: float = 60.0,
):
    lock_path = unlock_path.with_suffix(unlock_path.suffix + ".lock")
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            descriptor = os.open(
                str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            if _lock_is_stale(lock_path, stale_after_s=stale_after_s):
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out acquiring sealed ledger lock: {lock_path}")
            time.sleep(0.01)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "owner_pid": os.getpid(),
                    "owner_host": socket.gethostname(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                handle,
            )
        break
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON evidence record: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON evidence record must be an object: {path}")
    return value


def _checkpoint_payload(path: Path) -> Mapping[str, Any]:
    try:
        try:
            import torch
        except ImportError:
            import pickle

            with path.open("rb") as handle:
                value = pickle.load(handle)
        else:
            value = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:  # noqa: BLE001 - normalize persistence diagnostics
        raise ValueError(f"invalid frozen checkpoint: {path}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"invalid frozen checkpoint: {path}")
    return value


def _validation_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank validation row at {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"validation row must be an object at {path}:{line_number}")
            rows.append(value)
    return rows


def _statistics_identity(statistics: Mapping[str, object]) -> str:
    margin = statistics.get("practical_equivalence_margin")
    if (
        isinstance(margin, bool)
        or not isinstance(margin, (int, float))
        or not math.isfinite(float(margin))
        or float(margin) <= 0.0
    ):
        raise ValueError("validation freeze requires a finite positive practical-equivalence margin")
    basis = statistics.get("practical_equivalence_basis")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("validation freeze requires a practical-equivalence basis")
    return _canonical_hash(dict(statistics))


def _selected_checkpoint(
    job: JobRecord, *, execution_profile: str,
) -> dict[str, object]:
    if job.status != "completed" or job.identity.execution_profile != execution_profile:
        raise ValueError(f"validation freeze requires completed {execution_profile} jobs")
    if job.identity.git_dirty or not job.identity.source_tree_hash:
        raise ValueError("validation freeze rejects dirty or unidentified source trees")
    if job.checkpoint_path is None or not job.checkpoint_path.is_file():
        raise ValueError("validation freeze requires an existing checkpoint")
    digest = _sha256(job.checkpoint_path)
    if job.checkpoint_sha256 != digest:
        raise ValueError("job checkpoint hash does not match its persisted record")
    if job.checkpoint_step != job.identity.target_updates:
        raise ValueError("selected checkpoint is not the registered final update")
    payload = _checkpoint_payload(job.checkpoint_path)
    if payload.get("format") != 2 or payload.get("step") != job.checkpoint_step:
        raise ValueError("selected checkpoint envelope does not match its persisted step")
    expected_provenance = {"job_id": job.job_id, **job.identity.to_dict()}
    if payload.get("provenance") != expected_provenance:
        raise ValueError("selected checkpoint provenance does not match its job identity")
    return {
        "job_id": job.job_id,
        **job.identity.to_dict(),
        "checkpoint_path": str(job.checkpoint_path.resolve()),
        "checkpoint_sha256": digest,
        "checkpoint_step": int(job.checkpoint_step),
    }


def create_validation_freeze(
    path: str | Path,
    *,
    config_hash: str,
    protocol_hash: str,
    statistics: Mapping[str, object],
    jobs: Sequence[JobRecord],
    expected_job_ids: Sequence[str],
    validation_paths: Sequence[str | Path],
    validation_scenarios_by_scale: Mapping[str, Sequence[str]],
    execution_profile: str = "formal",
) -> dict[str, object]:
    """Freeze validation completion and one final checkpoint per immutable job."""

    destination = Path(path).resolve()
    if execution_profile not in {"formal", "simulation"}:
        raise ValueError("validation freeze execution_profile must be formal or simulation")
    if destination.exists():
        raise FileExistsError(f"validation freeze already exists: {destination}")
    if not jobs:
        raise ValueError("validation freeze requires at least one selected job")
    expected_ids = tuple(str(value) for value in expected_job_ids)
    if not expected_ids or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("validation freeze requires a unique non-empty formal job set")
    observed_ids = [job.job_id for job in jobs]
    if len(set(observed_ids)) != len(observed_ids) or set(observed_ids) != set(expected_ids):
        raise ValueError(
            "validation freeze formal job set is incomplete or contains extras; "
            f"missing={len(set(expected_ids) - set(observed_ids))}, "
            f"extra={len(set(observed_ids) - set(expected_ids))}"
        )
    selected = [
        _selected_checkpoint(job, execution_profile=execution_profile)
        for job in jobs
    ]
    if len({str(item["job_id"]) for item in selected}) != len(selected):
        raise ValueError("duplicate job in validation freeze")
    if any(item["config_hash"] != config_hash for item in selected):
        raise ValueError("selected job config hash does not match freeze identity")
    if any(item["protocol_hash"] != protocol_hash for item in selected):
        raise ValueError("selected job protocol hash does not match freeze identity")

    inputs = [Path(value).resolve() for value in validation_paths]
    if not inputs or any(not value.is_file() for value in inputs):
        raise ValueError("validation freeze requires existing validation evidence")
    rows = _validation_rows(inputs)
    expected = {
        (job.job_id, str(scenario_id))
        for job in jobs
        for scenario_id in validation_scenarios_by_scale.get(job.identity.scale, ())
    }
    observed: set[tuple[str, str]] = set()
    selected_by_job = {str(item["job_id"]): item for item in selected}
    for row in rows:
        if row.get("split") != "validation":
            raise ValueError("validation freeze input contains a non-validation row")
        job_id = str(row.get("job_id", ""))
        scenario_id = str(row.get("scenario_id", ""))
        key = (job_id, scenario_id)
        if key in observed:
            raise ValueError("duplicate validation job/scenario evidence")
        observed.add(key)
        checkpoint = selected_by_job.get(job_id)
        if checkpoint is None:
            raise ValueError("validation evidence references an unselected job")
        for field in (
            "method", "scale", "training_seed", "config_hash", "git_commit",
            "family", "condition_id", "protocol_hash", "source_tree_hash",
            "git_dirty", "execution_profile", "checkpoint_sha256", "checkpoint_step",
        ):
            if row.get(field) != checkpoint.get(field):
                raise ValueError(f"validation evidence {field} mismatch")
    if observed != expected:
        raise ValueError(
            "validation evidence is incomplete or contains extra scenarios; "
            f"missing={len(expected - observed)}, extra={len(observed - expected)}"
        )
    base: dict[str, object] = {
        "schema_version": 1,
        "status": "frozen",
        "config_hash": str(config_hash),
        "protocol_hash": str(protocol_hash),
        "execution_profile": execution_profile,
        "statistics": dict(statistics),
        "statistics_hash": _statistics_identity(statistics),
        "validation_inputs": [
            {"path": str(value), "sha256": _sha256(value)} for value in inputs
        ],
        "validation_record_count": len(rows),
        "expected_job_count": len(expected_ids),
        "selected_checkpoints": sorted(selected, key=lambda item: str(item["job_id"])),
        "expected_validation_keys": [
            {"job_id": job_id, "scenario_id": scenario_id}
            for job_id, scenario_id in sorted(expected)
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest = {**base, "freeze_hash": _canonical_hash(base)}
    _write_json(destination, manifest)
    return manifest


def verify_validation_freeze(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    manifest = _read_json(source)
    freeze_hash = str(manifest.get("freeze_hash", ""))
    base = {key: value for key, value in manifest.items() if key != "freeze_hash"}
    if freeze_hash != _canonical_hash(base):
        raise ValueError("validation freeze hash mismatch")
    if manifest.get("status") != "frozen" or manifest.get("schema_version") != 1:
        raise ValueError("unsupported validation freeze")
    for item in manifest.get("validation_inputs", []):
        evidence = Path(str(item["path"]))
        if not evidence.is_file() or _sha256(evidence) != item.get("sha256"):
            raise ValueError("validation evidence hash mismatch after freeze")
    for item in manifest.get("selected_checkpoints", []):
        checkpoint = Path(str(item["checkpoint_path"]))
        if not checkpoint.is_file() or _sha256(checkpoint) != item.get("checkpoint_sha256"):
            raise ValueError("checkpoint hash mismatch after validation freeze")
        payload = _checkpoint_payload(checkpoint)
        if payload.get("step") != item.get("checkpoint_step"):
            raise ValueError("checkpoint step mismatch after validation freeze")
        expected = {
            "job_id": item["job_id"],
            **{
                key: item[key]
                for key in (
                    "method", "scale", "training_seed", "config_hash", "git_commit",
                    "execution_profile", "target_updates", "rollout_horizon", "family",
                    "condition_id", "scenario_split", "protocol_hash",
                    "source_tree_hash", "git_dirty",
                )
            },
        }
        if payload.get("provenance") != expected:
            raise ValueError("checkpoint provenance mismatch after validation freeze")
    return manifest


def create_sealed_unlock(
    path: str | Path,
    *,
    freeze_path: str | Path,
    sealed_scenarios: Sequence[str],
) -> dict[str, object]:
    destination = Path(path).resolve()
    if destination.exists():
        raise FileExistsError(f"sealed unlock already exists: {destination}")
    freeze_source = Path(freeze_path).resolve()
    freeze = verify_validation_freeze(freeze_source)
    scenarios = tuple(sorted({str(value) for value in sealed_scenarios if str(value)}))
    if not scenarios:
        raise ValueError("sealed unlock requires at least one scenario")
    immutable = {
        "schema_version": 1,
        "status": "unlocked",
        "freeze_path": str(freeze_source),
        "freeze_file_sha256": _sha256(freeze_source),
        "freeze_hash": freeze["freeze_hash"],
        "allowed_scenarios": list(scenarios),
        "permitted_job_ids": sorted(
            str(item["job_id"]) for item in freeze["selected_checkpoints"]
        ),
    }
    payload: dict[str, object] = {
        **immutable,
        "unlock_id": _canonical_hash(immutable),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reservations": [],
        "consumed": [],
    }
    _write_json(destination, payload)
    return payload


def _verified_unlock(unlock_path: Path, freeze_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    freeze = verify_validation_freeze(freeze_path)
    unlock = _read_json(unlock_path)
    immutable_keys = (
        "schema_version", "status", "freeze_path", "freeze_file_sha256",
        "freeze_hash", "allowed_scenarios", "permitted_job_ids",
    )
    immutable = {key: unlock.get(key) for key in immutable_keys}
    if unlock.get("unlock_id") != _canonical_hash(immutable):
        raise ValueError("sealed-test unlock identity mismatch")
    if unlock.get("status") != "unlocked" or unlock.get("schema_version") != 1:
        raise ValueError("sealed-test unlock is not active")
    if Path(str(unlock.get("freeze_path", ""))).resolve() != freeze_path.resolve():
        raise ValueError("sealed-test unlock references a different freeze")
    if unlock.get("freeze_file_sha256") != _sha256(freeze_path):
        raise ValueError("sealed-test unlock freeze file hash mismatch")
    if unlock.get("freeze_hash") != freeze.get("freeze_hash"):
        raise ValueError("sealed-test unlock freeze identity mismatch")
    return freeze, unlock


def _reservation_is_stale(item: Mapping[str, object], *, ttl_s: float) -> bool:
    if str(item.get("owner_host", "")) == socket.gethostname():
        try:
            return not pid_is_alive(int(item.get("owner_pid")))
        except (TypeError, ValueError):
            return True
    return _timestamp_age_s(item.get("reserved_at")) > ttl_s


def reserve_sealed_access(
    unlock_path: str | Path,
    *,
    freeze_path: str | Path,
    job_id: str,
    scenario_id: str,
    reservation_ttl_s: float = 3600.0,
) -> dict[str, object]:
    if not math.isfinite(float(reservation_ttl_s)) or float(reservation_ttl_s) <= 0:
        raise ValueError("reservation_ttl_s must be finite and positive")
    unlock_source = Path(unlock_path).resolve()
    freeze_source = Path(freeze_path).resolve()
    with _ledger_lock(unlock_source):
        _freeze, unlock = _verified_unlock(unlock_source, freeze_source)
        job_id, scenario_id = str(job_id), str(scenario_id)
        if job_id not in unlock.get("permitted_job_ids", []):
            raise ValueError("sealed access job is not present in the validation freeze")
        if scenario_id not in unlock.get("allowed_scenarios", []):
            raise ValueError("sealed access scenario is not permitted by the unlock")
        access_key = f"{job_id}:{scenario_id}"
        consumed = list(unlock.get("consumed", []))
        if any(str(item.get("access_key")) == access_key for item in consumed):
            raise ValueError("sealed access was already consumed for this job and scenario")
        reservations = [
            dict(item)
            for item in unlock.get("reservations", [])
            if not _reservation_is_stale(item, ttl_s=float(reservation_ttl_s))
        ]
        if any(str(item.get("access_key")) == access_key for item in reservations):
            raise ValueError("sealed access already has an active reservation")
        reservation: dict[str, object] = {
            "reservation_id": uuid4().hex,
            "access_key": access_key,
            "job_id": job_id,
            "scenario_id": scenario_id,
            "owner_pid": os.getpid(),
            "owner_host": socket.gethostname(),
            "reserved_at": datetime.now(timezone.utc).isoformat(),
        }
        reservations.append(reservation)
        unlock["reservations"] = reservations
        _write_json(unlock_source, unlock)
        return reservation


def release_sealed_access(
    unlock_path: str | Path,
    *,
    freeze_path: str | Path,
    reservation_id: str,
) -> bool:
    unlock_source = Path(unlock_path).resolve()
    freeze_source = Path(freeze_path).resolve()
    with _ledger_lock(unlock_source):
        _freeze, unlock = _verified_unlock(unlock_source, freeze_source)
        reservations = list(unlock.get("reservations", []))
        retained = [
            item for item in reservations
            if str(item.get("reservation_id")) != str(reservation_id)
        ]
        changed = len(retained) != len(reservations)
        if changed:
            unlock["reservations"] = retained
            _write_json(unlock_source, unlock)
        return changed


def _single_evidence_row(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"sealed evidence is unreadable: {path}") from exc
    if len(lines) != 1 or not lines[0].strip():
        raise ValueError("sealed evidence must contain exactly one JSONL row")
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ValueError("sealed evidence contains invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("sealed evidence row must be an object")
    return value


def commit_sealed_access(
    unlock_path: str | Path,
    *,
    freeze_path: str | Path,
    reservation_id: str,
    evidence_path: str | Path,
) -> dict[str, object]:
    unlock_source = Path(unlock_path).resolve()
    freeze_source = Path(freeze_path).resolve()
    evidence_source = Path(evidence_path).resolve()
    row = _single_evidence_row(evidence_source)
    digest = _sha256(evidence_source)
    with _ledger_lock(unlock_source):
        _freeze, unlock = _verified_unlock(unlock_source, freeze_source)
        reservations = list(unlock.get("reservations", []))
        matches = [
            dict(item) for item in reservations
            if str(item.get("reservation_id")) == str(reservation_id)
        ]
        if len(matches) != 1:
            raise ValueError("sealed reservation is missing or ambiguous")
        reservation = matches[0]
        if (
            row.get("split") != "sealed_test"
            or str(row.get("job_id", "")) != str(reservation["job_id"])
            or str(row.get("scenario_id", "")) != str(reservation["scenario_id"])
        ):
            raise ValueError("sealed evidence does not match its reservation")
        access_key = str(reservation["access_key"])
        consumed = list(unlock.get("consumed", []))
        if any(str(item.get("access_key")) == access_key for item in consumed):
            raise ValueError("sealed access was already committed")
        receipt: dict[str, object] = {
            "access_key": access_key,
            "job_id": str(reservation["job_id"]),
            "scenario_id": str(reservation["scenario_id"]),
            "reservation_id": str(reservation_id),
            "run_id": str(row.get("run_id", "")),
            "raw_path": str(evidence_source),
            "raw_sha256": digest,
            "committed_at": datetime.now(timezone.utc).isoformat(),
        }
        consumed.append(receipt)
        unlock["consumed"] = consumed
        unlock["reservations"] = [
            item for item in reservations
            if str(item.get("reservation_id")) != str(reservation_id)
        ]
        _write_json(unlock_source, unlock)
        return receipt


def verify_sealed_evidence(
    records: Sequence[Mapping[str, object]],
    *,
    evidence_paths: Sequence[str | Path],
    freeze_path: str | Path,
    unlock_path: str | Path,
) -> dict[str, object]:
    freeze, unlock = _verified_unlock(Path(unlock_path).resolve(), Path(freeze_path).resolve())
    selected = {str(item["job_id"]): item for item in freeze["selected_checkpoints"]}
    consumed = {
        str(item["access_key"]): item for item in unlock.get("consumed", [])
    }
    evidence_by_key: dict[str, tuple[Path, str, dict[str, Any]]] = {}
    for value in evidence_paths:
        path = Path(value).resolve()
        row = _single_evidence_row(path)
        key = f"{row.get('job_id', '')}:{row.get('scenario_id', '')}"
        if key in evidence_by_key:
            raise ValueError("duplicate sealed evidence path for one job/scenario")
        evidence_by_key[key] = (path, _sha256(path), row)
    seen: set[str] = set()
    for row in records:
        if row.get("split") != "sealed_test":
            raise ValueError("formal sealed evidence contains a non-sealed row")
        job_id, scenario_id = str(row.get("job_id", "")), str(row.get("scenario_id", ""))
        access_key = f"{job_id}:{scenario_id}"
        if access_key in seen:
            raise ValueError("duplicate sealed job/scenario evidence")
        seen.add(access_key)
        receipt = consumed.get(access_key)
        if receipt is None:
            raise ValueError("sealed evidence has no consumed unlock receipt")
        evidence = evidence_by_key.get(access_key)
        if evidence is None:
            raise ValueError("sealed evidence has no bound raw input path")
        path, digest, raw_row = evidence
        if (
            str(receipt.get("raw_path", "")) != str(path)
            or str(receipt.get("raw_sha256", "")) != digest
            or str(receipt.get("run_id", "")) != str(row.get("run_id", ""))
            or str(raw_row.get("run_id", "")) != str(row.get("run_id", ""))
        ):
            raise ValueError("sealed evidence hash or receipt identity mismatch")
        checkpoint = selected.get(job_id)
        if checkpoint is None:
            raise ValueError("sealed evidence references a checkpoint outside the freeze")
        for field in (
            "method", "scale", "training_seed", "config_hash", "git_commit",
            "family", "condition_id", "protocol_hash", "source_tree_hash",
            "git_dirty", "checkpoint_sha256", "checkpoint_step",
        ):
            if row.get(field) != checkpoint.get(field):
                raise ValueError(f"sealed evidence {field} mismatch")
    if seen != set(evidence_by_key):
        raise ValueError("sealed evidence paths contain unreported rows")
    return {
        "freeze_hash": freeze["freeze_hash"],
        "unlock_id": unlock["unlock_id"],
        "verified_record_count": len(records),
    }


__all__ = [
    "commit_sealed_access",
    "create_sealed_unlock",
    "create_validation_freeze",
    "release_sealed_access",
    "reserve_sealed_access",
    "verify_sealed_evidence",
    "verify_validation_freeze",
]
