"""Crash-safe checkpoint persistence and recovery."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from .artifacts import artifact_sha256


def atomic_checkpoint_write(path: Path, payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise TypeError("checkpoint payload must be an object")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        import os
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        candidate = Path(temporary)
        if json.loads(candidate.read_text(encoding="utf-8")) != payload:
            raise IOError("checkpoint reload verification failed")
        if path.exists():
            # Never rotate a corrupt current checkpoint over the known-good sibling.
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(current, dict):
                    raise ValueError("current checkpoint is not an object")
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise IOError("refusing to rotate an invalid current checkpoint") from exc
            previous = path.with_suffix(path.suffix + ".previous")
            previous.write_bytes(path.read_bytes())
        os.replace(temporary, path)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass
    return artifact_sha256(path)


def recover_checkpoint(
    path: Path,
    *,
    expected_identity: str | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    path = Path(path)
    candidates = [path, path.with_suffix(path.suffix + ".previous")]
    errors: list[str] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            if expected_sha256 is not None and artifact_sha256(candidate) != expected_sha256:
                raise ValueError("checkpoint hash mismatch")
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("checkpoint is not an object")
            if expected_identity is not None and payload.get("identity") != expected_identity:
                raise ValueError("checkpoint identity mismatch")
            return payload
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{candidate}: {exc}")
    raise ValueError("no valid checkpoint available" + (": " + "; ".join(errors) if errors else ""))


__all__ = ["atomic_checkpoint_write", "recover_checkpoint"]
