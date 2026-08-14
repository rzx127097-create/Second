"""Input/output hash manifest for artifact traceability."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_evidence_manifest(path: Path, input_path: Path, output_paths: Mapping[str, Path], records: list[Mapping[str, object]], *, provisional: bool = True) -> dict[str, object]:
    manifest: dict[str, object] = {
        "input": {"path": str(input_path), "sha256": _sha256(input_path)},
        "outputs": {name: {"path": str(value), "sha256": _sha256(value)} for name, value in output_paths.items() if value.exists()},
        "identity": {
            "config_hash": sorted({str(row["config_hash"]) for row in records}),
            "git_commit": sorted({str(row["git_commit"]) for row in records}),
            "method": sorted({str(row["method"]) for row in records}),
            "scale": sorted({str(row["scale"]) for row in records}),
            "split": sorted({str(row["split"]) for row in records}),
        },
        "script_version": "artifact-pipeline-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provisional": provisional,
        "self": {"path": str(path), "sha256": None, "sha256_note": "self-hash omitted because serialization changes its own bytes"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def build_manifest(artifacts: Mapping[str, tuple[str | Path, str | Path]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, (source, output) in artifacts.items():
        source_path, output_path = Path(source), Path(output)
        result[str(name)] = {
            "input_path": str(source_path), "output_path": str(output_path),
            "input_sha256": _sha256(source_path), "output_sha256": _sha256(output_path),
        }
    return result
