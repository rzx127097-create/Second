"""Atomic, provenance-bound checkpoint persistence for G3."""

from __future__ import annotations

import os
import random
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch


CHECKPOINT_FORMAT_VERSION = "g3-checkpoint-v1"


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


__all__ = ["CHECKPOINT_FORMAT_VERSION", "load_checkpoint", "save_checkpoint"]
