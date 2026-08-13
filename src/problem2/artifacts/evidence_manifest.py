"""Input/output hash manifest for artifact traceability."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(artifacts: Mapping[str, tuple[str | Path, str | Path]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, (source, output) in artifacts.items():
        source_path, output_path = Path(source), Path(output)
        result[str(name)] = {
            "input_path": str(source_path), "output_path": str(output_path),
            "input_sha256": _sha256(source_path), "output_sha256": _sha256(output_path),
        }
    return result
