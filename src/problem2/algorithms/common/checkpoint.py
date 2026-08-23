"""Atomic, provenance-bound checkpoint persistence for G3."""

from __future__ import annotations

import os
import random
import tempfile
import copy
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch


CHECKPOINT_FORMAT_VERSION = "g3-checkpoint-v1"
TRAINING_CHECKPOINT_FORMAT_VERSION = "g5-training-checkpoint-v1"


@dataclass(frozen=True)
class CheckpointRecord:
    path: Path
    format_version: str
    sha256: str
    provenance: dict[str, Any]
    state: dict[str, Any]
    previous_sha256: str | None = None


def _rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def _restore_rng(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    if state.get("torch_cuda") is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_training_payload(path: Path) -> dict[str, Any]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or payload.get("format_version") != TRAINING_CHECKPOINT_FORMAT_VERSION:
        raise ValueError("unsupported G5 training checkpoint format")
    if not isinstance(payload.get("state"), dict):
        raise ValueError("training checkpoint state must be a mapping")
    if not isinstance(payload.get("provenance"), dict):
        raise ValueError("training checkpoint provenance must be a mapping")
    if not isinstance(payload["state"].get("rng"), dict):
        raise ValueError("training checkpoint RNG state is missing")
    return payload


def _training_record(path: Path, payload: dict[str, Any], previous_sha256: str | None = None) -> CheckpointRecord:
    return CheckpointRecord(
        path=path,
        format_version=payload["format_version"],
        sha256=_sha256(path),
        provenance=copy.deepcopy(payload["provenance"]),
        state=copy.deepcopy(payload["state"]),
        previous_sha256=previous_sha256,
    )


def save_training_checkpoint(path: Path, state: Mapping[str, Any], provenance: Mapping[str, Any]) -> CheckpointRecord:
    """Persist a verified G5 checkpoint and retain ``<path>.previous`` on rotation."""

    destination = Path(path)
    if not isinstance(state, Mapping) or not isinstance(provenance, Mapping):
        raise TypeError("training checkpoint state and provenance must be mappings")
    if "algorithm" not in state or not isinstance(state["algorithm"], Mapping):
        raise ValueError("training checkpoint state must include algorithm state")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stored_state = copy.deepcopy(dict(state))
    stored_state["rng"] = _rng_state()
    payload = {"format_version": TRAINING_CHECKPOINT_FORMAT_VERSION, "state": stored_state, "provenance": copy.deepcopy(dict(provenance))}
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary = Path(temporary_name)
    previous = Path(f"{destination}.previous")
    previous_sha256: str | None = None
    try:
        with os.fdopen(descriptor, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        _load_training_payload(temporary)
        temporary_sha256 = _sha256(temporary)
        if destination.exists():
            _load_training_payload(destination)
            previous_sha256 = _sha256(destination)
            os.replace(destination, previous)
        os.replace(temporary, destination)
        final_payload = _load_training_payload(destination)
        if _sha256(destination) != temporary_sha256:
            raise RuntimeError("training checkpoint hash changed during atomic replacement")
        return _training_record(destination, final_payload, previous_sha256)
    finally:
        temporary.unlink(missing_ok=True)


def load_training_checkpoint(path: Path, algorithm_factory: Callable[[], Any], expected_hashes: Mapping[str, str]) -> tuple[Any, CheckpointRecord]:
    """Load G5 state only when frozen source/config/protocol ancestry match."""

    source = Path(path)
    payload = _load_training_payload(source)
    if not isinstance(expected_hashes, Mapping):
        raise TypeError("expected_hashes must be a mapping")
    mismatches = [key for key, expected in expected_hashes.items() if payload["provenance"].get(key) != expected]
    if mismatches:
        raise ValueError("training checkpoint provenance mismatch: " + ", ".join(sorted(mismatches)))
    algorithm = algorithm_factory()
    algorithm.load_state_dict(payload["state"]["algorithm"])
    _restore_rng(payload["state"]["rng"])
    return algorithm, _training_record(source, payload)


def save_checkpoint(
    path: str | Path,
    algorithm: Any,
    step: int,
    *,
    provenance: dict[str, Any] | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": CHECKPOINT_FORMAT_VERSION,
        "step": int(step),
        "algorithm": algorithm.state_dict(),
        "trainer": (
            algorithm._trainer.state_dict()
            if getattr(algorithm, "_trainer", None) is not None
            else None
        ),
        "provenance": dict(provenance or {}),
        "rng": _rng_state(),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_checkpoint(
    path: str | Path,
    algorithm_factory: Callable[[], Any],
    *,
    expected_provenance: Mapping[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    source = Path(path)
    payload = torch.load(source, map_location="cpu", weights_only=False)
    if payload.get("format_version") != CHECKPOINT_FORMAT_VERSION:
        raise ValueError("unsupported G3 checkpoint format")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("checkpoint provenance must be a mapping")
    if expected_provenance is not None:
        mismatches = [
            key
            for key, expected in expected_provenance.items()
            if provenance.get(key) != expected
        ]
        if mismatches:
            raise ValueError(
                "checkpoint provenance mismatch: " + ", ".join(sorted(mismatches))
            )
    algorithm = algorithm_factory()
    algorithm.load_state_dict(payload["algorithm"])
    trainer = getattr(algorithm, "_trainer", None)
    trainer_state = payload.get("trainer")
    if trainer is not None and trainer_state is not None:
        trainer.load_state_dict(trainer_state)
    _restore_rng(payload["rng"])
    return algorithm, {
        "format_version": payload["format_version"],
        "step": int(payload["step"]),
        "provenance": dict(provenance),
    }


__all__ = [
    "CHECKPOINT_FORMAT_VERSION",
    "TRAINING_CHECKPOINT_FORMAT_VERSION",
    "CheckpointRecord",
    "load_checkpoint",
    "load_training_checkpoint",
    "save_checkpoint",
    "save_training_checkpoint",
]
