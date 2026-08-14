"""Input/output hash manifest for artifact traceability."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pipeline_source_identity() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for source in sorted(root.glob("*.py")):
        digest.update(source.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_evidence_manifest(path: Path, input_path: Path, output_paths: Mapping[str, Path], records: list[Mapping[str, object]], *, provisional: bool = True) -> dict[str, object]:
    manifest: dict[str, object] = {
        "input": {"path": str(input_path), "sha256": _sha256(input_path)},
        "outputs": {name: {"path": str(value), "sha256": _sha256(value)} for name, value in output_paths.items() if value.exists()},
        "identity": {
            "config_hash": sorted({str(row["config_hash"]) for row in records}),
            "git_commit": sorted({str(row["git_commit"]) for row in records}),
            "source_tree_hash": sorted({str(row.get("source_tree_hash", "")) for row in records}),
            "checkpoint_sha256": sorted({str(row.get("checkpoint_sha256", "")) for row in records}),
            "method": sorted({str(row["method"]) for row in records}),
            "scale": sorted({str(row["scale"]) for row in records}),
            "split": sorted({str(row["split"]) for row in records}),
        },
        "script_version": f"sha256:{_pipeline_source_identity()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provisional": provisional,
        "self": {"path": str(path), "sha256": None, "sha256_note": "self-hash omitted because serialization changes its own bytes"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
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


def write_chapter45_evidence_manifest(
    path: Path,
    *,
    input_paths: Sequence[Path],
    protocol_path: Path,
    output_paths: Mapping[str, Path],
    records: Sequence[Mapping[str, object]],
    maturity: str,
    uncertainty: Mapping[str, object],
    metric_definitions: Mapping[str, object],
) -> dict[str, object]:
    """Write the complete Chapter 4.5 source-to-artifact evidence map."""

    manifest: dict[str, object] = {
        "inputs": [
            {"path": str(value), "sha256": _sha256(value)} for value in input_paths
        ],
        "protocol": {"path": str(protocol_path), "sha256": _sha256(protocol_path)},
        "outputs": {
            name: {"path": str(value), "sha256": _sha256(value)}
            for name, value in sorted(output_paths.items())
            if value.exists()
        },
        "identity": {
            "config_hash": sorted({str(row["config_hash"]) for row in records}),
            "protocol_hash": sorted({str(row["protocol_hash"]) for row in records}),
            "git_commit": sorted({str(row["git_commit"]) for row in records}),
            "family": sorted({str(row["family"]) for row in records}),
            "method": sorted({str(row["method"]) for row in records}),
            "scale": sorted({str(row["scale"]) for row in records}),
            "split": sorted({str(row["split"]) for row in records}),
        },
        "maturity": str(maturity),
        "uncertainty": dict(uncertainty),
        "metric_definitions": dict(metric_definitions),
        "scenario_selection_rule": "all registered shared scenarios in the declared evaluation split; no representative-scene selection",
        "script_version": f"sha256:{_pipeline_source_identity()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "self": {
            "path": str(path),
            "sha256": None,
            "sha256_note": "self-hash omitted because serialization changes its own bytes",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return manifest
