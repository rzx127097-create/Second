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
CANONICAL_G4_ROOT = (ROOT / "outputs/problem2_sr_mappo_v1/g4").resolve()
SUPPORTED_G4_SUFFIXES = frozenset({".json", ".jsonl"})


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


def _require_under(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must remain under the canonical G4 root") from exc
    return resolved


def _structured_payloads(root: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if path.name == "artifact-manifest.json":
            continue
        payloads.append(_read_json(path))
    for path in sorted(root.rglob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"cannot read G4 JSONL evidence {path.name}") from exc
        record_count = 0
        if not lines:
            raise ValueError(f"G4 JSONL evidence is empty: {path.name}")
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed G4 JSONL evidence {path.name}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"G4 JSONL record must be an object: {path.name}:{line_number}")
            payloads.append(value)
            record_count += 1
        if record_count == 0:
            raise ValueError(f"G4 JSONL evidence is empty: {path.name}")
    return payloads


def _check_boundary(value: Any) -> None:
    if isinstance(value, dict):
        for key in ("validation_accessed", "sealed_test_accessed", "battery_replenishment_enabled"):
            if key in value and value[key] is not False:
                raise ValueError(f"{key} must remain false")
        for nested in value.values():
            _check_boundary(nested)
    elif isinstance(value, list):
        for nested in value:
            _check_boundary(nested)


def _reject_manifest_g3_paths(recorded: dict[str, Any]) -> None:
    artifacts = recorded.get("artifacts", [])
    if not isinstance(artifacts, list):
        return
    for entry in artifacts:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            path = Path(entry["path"])
            if "g3" in {part.lower() for part in path.parts}:
                raise ValueError("G3 artifact paths cannot be endpoint evidence")
def audit_g4_mechanism(
    config_path: str | Path,
    output_root: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    """Audit only G4 mechanism evidence and fail closed on boundary violations."""

    contract = load_g4_contract(config_path)
    manifest = load_g4_probe_manifest(PROBE_MANIFEST_PATH)
    canonical_root = CANONICAL_G4_ROOT.resolve()
    root = _require_under(Path(output_root), canonical_root, "output_root")
    destination = _require_under(Path(report_path), canonical_root, "report_path")
    if not root.is_dir():
        raise ValueError("G4 output root does not exist")
    for path in root.rglob("*"):
        relative_text = path.relative_to(root).as_posix().lower()
        if path.is_file() and path.suffix.lower() not in SUPPORTED_G4_SUFFIXES:
            raise ValueError(f"unsupported G4 artifact file type: {relative_text}")
        if path.is_file() and "g3" in Path(relative_text).parts:
            raise ValueError("G3 artifacts cannot be used as endpoint evidence")
    payloads = _structured_payloads(root)
    for payload in payloads:
        _check_boundary(payload)
    provenance = [payload.get("lineage") for payload in payloads if isinstance(payload.get("lineage"), dict)]
    recorded_path = root / "artifact-manifest.json"
    recorded = _read_json(recorded_path) if recorded_path.exists() else None
    if recorded is not None:
        _reject_manifest_g3_paths(recorded)

    fixed = _read_json(root / "fixed" / "activation-summary.json")
    mobile = _read_json(root / "mobile" / "activation-summary.json")
    if fixed.get("activation_window") != mobile.get("activation_window"):
        raise ValueError("fixed and mobile activation bands must match")
    if fixed.get("activation_window") != list(contract.admissible_band):
        raise ValueError("activation band does not match the frozen contract")
    recomputed = run_counterfactual_probe(fixed, mobile)
    counterfactual_path = root / "counterfactual-summary.json"
    if counterfactual_path.exists():
        counterfactual = _read_json(counterfactual_path)
        if counterfactual != recomputed:
            raise ValueError("stored counterfactual summary does not match recomputed values")
    else:
        counterfactual = recomputed
        counterfactual_path.write_text(json.dumps(counterfactual, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if recorded is not None:
        verified_artifacts = _verify_manifest(
            root,
            recorded,
            ignored_paths={destination.relative_to(root).as_posix()}
            if destination.is_relative_to(root)
            else set(),
        )

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
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


__all__ = ["audit_g4_mechanism", "build_g4_artifact_manifest"]
