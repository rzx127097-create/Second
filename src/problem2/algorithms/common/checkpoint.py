"""Atomic SR-MAPPO checkpoint persistence."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any, Callable


def _payload(algorithm: Any, step: int) -> dict[str, Any]:
    trainer = getattr(algorithm, "_trainer", None)
    return {
        "step": int(step),
        "algorithm": algorithm.state_dict(),
        "trainer": trainer.state_dict() if trainer is not None else None,
        "format": 2,
    }


def save_checkpoint(path: str | Path, algorithm: Any, step: int) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    payload = _payload(algorithm, step)
    try:
        import torch
    except ImportError:
        with temporary.open("wb") as handle:
            pickle.dump(payload, handle)
    else:
        torch.save(payload, temporary)
    os.replace(temporary, destination)
    return destination


def load_checkpoint(path: str | Path, algorithm_factory: Callable[[], Any]) -> tuple[Any, dict[str, Any]]:
    source = Path(path)
    try:
        import torch
    except ImportError:
        with source.open("rb") as handle:
            payload = pickle.load(handle)
    else:
        payload = torch.load(source, map_location="cpu", weights_only=False)
    algorithm = algorithm_factory()
    algorithm.load_state_dict(payload["algorithm"])
    trainer = getattr(algorithm, "_trainer", None)
    if trainer is not None and payload.get("trainer") is not None:
        trainer.load_state_dict(payload["trainer"])
    return algorithm, {"step": int(payload["step"]), "format": int(payload.get("format", 1))}
