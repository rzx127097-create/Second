"""Content-addressed, atomic artifact helpers for the G5 evidence chain."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def artifact_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> str:
    """Write bytes through a same-directory temporary file and return its hash."""
    if not isinstance(data, bytes):
        raise TypeError("artifact payload must be bytes")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if Path(temporary).read_bytes() != data:
            raise IOError("temporary artifact verification failed")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    if artifact_sha256(path) != digest:
        raise IOError("artifact hash changed during replacement")
    return digest


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def write_quarantine(path: Path, raw: bytes, *, locator: str, reason: str) -> dict[str, str]:
    record = {
        "original_bytes_b64": base64.b64encode(raw).decode("ascii"),
        "locator": locator,
        "reason": reason,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }
    append_jsonl(path, record)
    return record


def read_quarantine(path: Path) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []
    records: list[dict[str, str]] = []
    for line_number, line in enumerate(Path(path).read_bytes().splitlines(), 1):
        try:
            item = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid quarantine record at line {line_number}") from exc
        if not isinstance(item, dict):
            raise ValueError("quarantine record must be an object")
        records.append(item)
    return records


__all__ = ["artifact_sha256", "atomic_write_bytes", "append_jsonl", "write_quarantine", "read_quarantine"]
