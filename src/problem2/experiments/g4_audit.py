from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .g4_contract import load_g4_contract, load_g4_probe_manifest
from .g4_counterfactual import run_counterfactual_probe


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "docs/evidence/g4/g4_contract.yaml"
PROBE_MANIFEST_PATH = ROOT / "docs/evidence/g4/g4_probe_manifest.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_g4_artifact_manifest(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).resolve()
    manifest_path = root / "artifact-manifest.json"
    artifacts = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.resolve() == manifest_path.resolve():
            continue
        relative = path.relative_to(root).as_posix()
        if "/g3/" in f"/{relative}/" or relative.startswith("g3/"):
            raise ValueError("G3 artifact paths cannot be endpoint evidence")
        artifacts.append({"path": relative, "sha256": _sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": "g4-artifact-manifest.v1", "artifacts": artifacts}


def _verify_manifest(
    root: Path,
    recorded: dict[str, Any],
    *,
    ignored_paths: set[str] | None = None,
) -> list[dict[str, Any]]:
    artifacts = recorded.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("G4 artifact manifest must contain artifacts")
    verified = []
    recorded_paths: set[str] = set()
    ignored_paths = ignored_paths or set()
    for entry in artifacts:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("G4 artifact manifest entry is invalid")
        relative = Path(entry["path"])
        normalized = relative.as_posix()
        normalized_lower = normalized.lower()
        if "g3" in {part.lower() for part in relative.parts} or "/g3/" in f"/{normalized_lower}/":
            raise ValueError("G3 artifact paths cannot be endpoint evidence")
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("G4 artifact manifest contains path traversal")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("G4 artifact path escapes output root") from exc
        if not path.is_file():
            raise ValueError(f"recorded G4 artifact is missing: {relative.as_posix()}")
        actual = _sha256(path)
        if actual != entry.get("sha256"):
            raise ValueError(f"G4 artifact hash mismatch: {relative.as_posix()}")
        recorded_paths.add(normalized)
        verified.append({"path": relative.as_posix(), "sha256": actual, "bytes": path.stat().st_size})
    current_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "artifact-manifest.json"
    }
    missing_entries = sorted(current_paths - recorded_paths - ignored_paths)
    if missing_entries:
        raise ValueError(f"unrecorded G4 artifact: {missing_entries[0]}")
    return verified


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read G4 JSON artifact {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"G4 JSON artifact {path.name} must be an object")
    return value


def audit_g4_mechanism(
    config_path: str | Path,
    output_root: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    """Audit only G4 mechanism evidence and fail closed on boundary violations."""

    contract = load_g4_contract(config_path)
    manifest = load_g4_probe_manifest(PROBE_MANIFEST_PATH)
    root = Path(output_root).resolve()
    if not root.is_dir():
        raise ValueError("G4 output root does not exist")
    for path in root.rglob("*"):
        relative_text = path.relative_to(root).as_posix().lower()
        if path.is_file() and "g3" in Path(relative_text).parts:
            raise ValueError("G3 artifacts cannot be used as endpoint evidence")
        if path.is_file() and path.name != "artifact-manifest.json":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for flag in (
                '"validation_accessed": true',
                '"sealed_test_accessed": true',
                '"battery_replenishment_enabled": true',
            ):
                if flag in text.lower():
                    boundary = flag.split(":", 1)[0].strip('"')
                    raise ValueError(f"{boundary} must remain false")

    json_artifacts = [path for path in root.rglob("*.json") if path.name != "artifact-manifest.json"]
    provenance = []
    for path in json_artifacts:
        payload = _read_json(path)
        if payload.get("validation_accessed") or payload.get("sealed_test_accessed"):
            raise ValueError("validation or sealed-test access must remain false")
        lineage = payload.get("lineage")
        if isinstance(lineage, dict):
            provenance.append(lineage)
            if lineage.get("validation_accessed") or lineage.get("sealed_test_accessed"):
                raise ValueError("validation or sealed-test access must remain false")
            if lineage.get("battery_replenishment_enabled"):
                raise ValueError("battery replenishment activation must remain false")
        if payload.get("battery_replenishment_enabled"):
            raise ValueError("battery replenishment activation must remain false")
    recorded_path = root / "artifact-manifest.json"
    recorded = _read_json(recorded_path) if recorded_path.exists() else None
    if recorded is not None:
        verified_artifacts = _verify_manifest(
            root,
            recorded,
            ignored_paths={Path(report_path).resolve().relative_to(root).as_posix()}
            if Path(report_path).resolve().is_relative_to(root)
            else set(),
        )

    fixed = _read_json(root / "fixed" / "activation-summary.json")
    mobile = _read_json(root / "mobile" / "activation-summary.json")
    if fixed.get("activation_window") != mobile.get("activation_window"):
        raise ValueError("fixed and mobile activation bands must match")
    counterfactual_path = root / "counterfactual-summary.json"
    if counterfactual_path.exists():
        counterfactual = _read_json(counterfactual_path)
    else:
        counterfactual = run_counterfactual_probe(fixed, mobile, output_path=str(counterfactual_path))
    if not counterfactual.get("paired_deltas"):
        raise ValueError("G4 counterfactual summary has no paired deltas")

    if recorded is None:
        recorded = build_g4_artifact_manifest(root)
        recorded_path.write_text(json.dumps(recorded, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verified_artifacts = _verify_manifest(root, recorded)

    report: dict[str, Any] = {
        "status": "pass",
        "audit": "g4-mechanism-compliance",
        "frozen_contract_sha256": _sha256(Path(config_path)),
        "activation_band": list(counterfactual.get("activation_window", fixed.get("activation_window", []))),
        "paired_deltas": counterfactual["paired_deltas"],
        "output_artifact_hashes": verified_artifacts,
        "hard_boundary": {
            "validation_accessed": False,
            "sealed_test_accessed": False,
            "battery_replenishment_enabled": False,
            "g3_endpoint_evidence_accepted": False,
        },
        "probe_manifest": str(manifest.source_path),
        "provenance_count": len(provenance),
        "claim_boundary": contract.permitted_claim_boundary,
    }
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


__all__ = ["audit_g4_mechanism", "build_g4_artifact_manifest"]
