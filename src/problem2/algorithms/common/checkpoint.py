"""Atomic SR-MAPPO checkpoint persistence."""

from __future__ import annotations

import os
import pickle
import random
from pathlib import Path
from typing import Any, Callable


def _payload(algorithm: Any, step: int) -> dict[str, Any]:
    trainer = getattr(algorithm, "_trainer", None)
    payload = {
        "step": int(step),
        "algorithm": algorithm.state_dict(),
        "trainer": trainer.state_dict() if trainer is not None else None,
        "format": 2,
        "training_seed": getattr(algorithm, "training_seed", None),
    }
    try:
        import numpy as np
        payload["rng"] = {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
        }
        try:
            import torch
        except ImportError:
            pass
        else:
            payload["rng"]["torch"] = torch.get_rng_state()
            if torch.cuda.is_available():
                payload["rng"]["torch_cuda"] = torch.cuda.get_rng_state_all()
    except ImportError:
        payload["rng"] = {"python": random.getstate()}
    return payload


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
    rng = payload.get("rng") or {}
    if rng.get("python") is not None:
        random.setstate(rng["python"])
    try:
        import numpy as np
    except ImportError:
        pass
    else:
        if rng.get("numpy") is not None:
            np.random.set_state(rng["numpy"])
    try:
        import torch
    except ImportError:
        pass
    else:
        if rng.get("torch") is not None:
            torch.set_rng_state(rng["torch"])
        if rng.get("torch_cuda") is not None and torch.cuda.is_available():
            torch.cuda.set_rng_state_all(rng["torch_cuda"])
    return algorithm, {"step": int(payload["step"]), "format": int(payload.get("format", 1))}
