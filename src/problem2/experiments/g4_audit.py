from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping

from .g4_activation import validate_activation_band
from .g4_contract import G4Contract, load_g4_contract, load_g4_probe_manifest
from .g4_counterfactual import run_counterfactual_probe


ROOT = Path(__file__).resolve().parents[3]
PROBE_MANIFEST_PATH = ROOT / "docs/evidence/g4/g4_probe_manifest.yaml"
G2_CONFIG_PATH = ROOT / "configs/problem2/g2_deterministic.yaml"
CANONICAL_G4_ROOT = (ROOT / "outputs/problem2_sr_mappo_v1/g4").resolve()
SUPPORTED_G4_SUFFIXES = frozenset({".json", ".jsonl"})
SELF_GENERATED_AUDIT_REPORT = "g4-mechanism-audit.json"
ARM_DIRECTORIES = (
    ("fixed", "fixed_support_probe"),
    ("mobile", "mobile_support_probe"),
)
COUNT_METRICS = ("request_count", "reservation_count", "service_count")
NUMERIC_METRICS = (
    "total_requested_l",
    "total_transferred_l",
    "final_vehicle_inventory_l",
    "vehicle_inventory_used_l",
    "started_service_waiting_time_s",
    "euclidean_service_start_distance_m",
    "pesticide_disabled_time_s",
    "sprayed_volume_l",
    "conservation_error_l",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40,64}$")
G3_ENDPOINT_PATTERNS = (
    "outputs/problem2_sr_mappo_v1/g3",
    "g3-smoke.json",
    "training-smoke",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_g4_artifact_manifest(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).resolve()
    manifest_path = root / "artifact-manifest.json"
    audit_report_path = root / SELF_GENERATED_AUDIT_REPORT
    artifacts = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.resolve() in {
            manifest_path.resolve(), audit_report_path.resolve()
        }:
            continue
        relative = path.relative_to(root).as_posix()
        if _is_g3_endpoint_reference(relative):
            raise ValueError("G3 artifact paths cannot be endpoint evidence")
        artifacts.append({"path": relative, "sha256": _sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": "g4-artifact-manifest.v1", "artifacts": artifacts}


def _is_g3_endpoint_reference(value: str) -> bool:
    normalized = value.replace("\\", "/").casefold()
    return any(pattern in normalized for pattern in G3_ENDPOINT_PATTERNS)


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
    resolved_paths: set[str] = set()
    ignored_paths = ignored_paths or set()
    for entry in artifacts:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("G4 artifact manifest entry is invalid")
        relative = Path(entry["path"])
        normalized = relative.as_posix()
        if _is_g3_endpoint_reference(entry["path"]):
            raise ValueError("G3 artifact paths cannot be endpoint evidence")
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("G4 artifact manifest contains path traversal")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("G4 artifact path escapes output root") from exc
        if not path.is_file():
            raise ValueError(f"recorded G4 artifact is missing: {normalized}")
        resolved_key = str(path).casefold()
        if normalized in recorded_paths or resolved_key in resolved_paths:
            raise ValueError(f"duplicate G4 artifact manifest path: {normalized}")
        actual_hash = _sha256(path)
        if actual_hash != entry.get("sha256"):
            raise ValueError(f"G4 artifact hash mismatch: {normalized}")
        if entry.get("bytes") != path.stat().st_size:
            raise ValueError(f"G4 artifact byte mismatch: {normalized}")
        recorded_paths.add(normalized)
        resolved_paths.add(resolved_key)
        verified.append({"path": normalized, "sha256": actual_hash, "bytes": path.stat().st_size})
    manifest_path = root / "artifact-manifest.json"
    current_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read G4 JSONL evidence {path.name}") from exc
    records = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed G4 JSONL evidence {path.name}:{line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"G4 JSONL record must be an object: {path.name}:{line_number}")
        records.append(record)
    if not records:
        raise ValueError(f"G4 JSONL evidence is empty: {path.name}")
    return records


def _require_under(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must remain under the canonical G4 root") from exc
    return resolved


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
    elif isinstance(value, str):
        if _is_g3_endpoint_reference(value):
            raise ValueError("G3 endpoint references cannot be endpoint evidence")


def _git(*args: str) -> str:
    try:
        value = subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("G4 provenance requires resolvable Git objects") from exc
    if not value:
        raise ValueError("G4 provenance contains empty Git identity")
    return value


@lru_cache(maxsize=None)
def _tree_for_commit(commit: str) -> str:
    if _git("rev-parse", commit) != commit:
        raise ValueError("G4 provenance source_tree_commit is unresolved")
    return _git("rev-parse", f"{commit}^{{tree}}")


def _require_lineage(lineage: Any, contract: G4Contract) -> dict[str, Any]:
    if not isinstance(lineage, dict):
        raise ValueError("G4 provenance is missing")
    _check_boundary(lineage)
    for field, path in (
        ("g4_contract_sha256", contract.source_path),
        ("probe_manifest_sha256", PROBE_MANIFEST_PATH),
        ("g2_config_sha256", G2_CONFIG_PATH),
    ):
        value = lineage.get(field)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise ValueError(f"G4 provenance {field} is invalid")
        if path is None or value != _sha256(path):
            raise ValueError(f"G4 provenance {field} does not match frozen input")
    commit = lineage.get("source_tree_commit")
    tree = lineage.get("source_tree_hash")
    if not isinstance(commit, str) or not GIT_OBJECT_RE.fullmatch(commit):
        raise ValueError("G4 provenance source_tree_commit is invalid")
    if not isinstance(tree, str) or not GIT_OBJECT_RE.fullmatch(tree):
        raise ValueError("G4 provenance source_tree_hash is invalid")
    if _tree_for_commit(commit) != tree:
        raise ValueError("G4 provenance source_tree_hash does not match its commit")
    return lineage


def _levels(contract: G4Contract) -> tuple[float, float, float]:
    lower, upper = contract.admissible_band
    return lower, round((lower + upper) / 2.0, 10), upper


def _record_key(record: Mapping[str, Any]) -> tuple[str, int, float]:
    scale = record.get("scale_id")
    seed = record.get("seed")
    level = record.get("scarcity_level_l")
    if not isinstance(scale, str) or not scale:
        raise ValueError("G4 raw matrix scale_id is invalid")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("G4 raw matrix seed is invalid")
    if isinstance(level, bool) or not isinstance(level, (int, float)) or not math.isfinite(level):
        raise ValueError("G4 raw matrix scarcity_level_l is invalid")
    return scale, seed, float(level)


def _expected_keys(contract: G4Contract) -> set[tuple[str, int, float]]:
    return {
        (scale, seed, level)
        for scale in contract.probe_scales
        for seed in contract.probe_seeds
        for level in _levels(contract)
    }


def _require_record_semantics(
    record: Mapping[str, Any], contract: G4Contract, expected_policy: str
) -> None:
    key = _record_key(record)
    if record.get("support_policy") != expected_policy:
        raise ValueError(f"G4 raw matrix support_policy must be {expected_policy}")
    if record.get("initial_uav_pesticide_l") != key[2]:
        raise ValueError("G4 raw matrix executed scarcity axis does not match scarcity_level_l")
    if record.get("initial_vehicle_inventory_l") != contract.fixed_vehicle_inventory_l:
        raise ValueError("G4 raw matrix fixed vehicle inventory drifted")
    fingerprint = record.get("input_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError("G4 raw matrix input fingerprint is invalid")
    if not isinstance(record.get("scarcity_active"), bool):
        raise ValueError("G4 raw matrix scarcity_active is invalid")
    for name in COUNT_METRICS:
        value = record.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"G4 raw matrix {name} must be a non-negative integer")
    for name in NUMERIC_METRICS:
        value = record.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"G4 raw matrix {name} must be finite")
        if value < 0:
            raise ValueError(f"G4 raw matrix {name} must be non-negative")
    if record["scarcity_active"] and any(record[name] <= 0 for name in COUNT_METRICS):
        raise ValueError("G4 active record must contain a complete service cycle")
    if record["scarcity_active"] and (
        record["total_requested_l"] <= 0 or record["total_transferred_l"] <= 0
    ):
        raise ValueError("G4 active record must contain positive demand and transfer")
    if not math.isclose(
        float(record["initial_vehicle_inventory_l"]) - float(record["final_vehicle_inventory_l"]),
        float(record["vehicle_inventory_used_l"]),
        abs_tol=1.0e-9,
    ):
        raise ValueError("G4 raw matrix vehicle inventory accounting drifted")
    if not math.isclose(
        float(record["total_transferred_l"]),
        float(record["vehicle_inventory_used_l"]),
        abs_tol=1.0e-9,
    ):
        raise ValueError("G4 raw matrix transfer and vehicle-use accounting drifted")
    if record["conservation_error_l"] > 1.0e-9:
        raise ValueError("G4 raw matrix conservation error exceeds tolerance")
    _require_lineage(record.get("lineage"), contract)


def _require_exact_raw_matrix(
    records: Iterable[Mapping[str, Any]], contract: G4Contract, expected_policy: str
) -> dict[tuple[str, int, float], dict[str, Any]]:
    by_key: dict[tuple[str, int, float], dict[str, Any]] = {}
    for record in records:
        key = _record_key(record)
        if key in by_key:
            raise ValueError("G4 frozen raw matrix contains duplicate probe records")
        _require_record_semantics(record, contract, expected_policy)
        by_key[key] = dict(record)
    if set(by_key) != _expected_keys(contract):
        raise ValueError("G4 frozen raw matrix does not match the exact 3x3x3 probe matrix")
    return by_key


def _require_arm(
    root: Path, directory: str, expected_policy: str, contract: G4Contract
) -> tuple[dict[str, Any], dict[tuple[str, int, float], dict[str, Any]]]:
    arm_root = root / directory
    summary = _read_json(arm_root / "activation-summary.json")
    raw_by_key = _require_exact_raw_matrix(
        _read_jsonl(arm_root / "raw-probe.jsonl"), contract, expected_policy
    )
    summary_records = summary.get("records")
    if not isinstance(summary_records, list):
        raise ValueError(f"G4 {directory} summary lacks records")
    summary_by_key = _require_exact_raw_matrix(summary_records, contract, expected_policy)
    if raw_by_key != summary_by_key:
        raise ValueError(f"G4 {directory} raw records do not match activation summary")
    if summary.get("support_policy") != expected_policy:
        raise ValueError(f"G4 {directory} summary support policy drifted")
    lineage = _require_lineage(summary.get("lineage"), contract)
    windows = validate_activation_band(summary_by_key.values(), _levels(contract))
    if set(windows.values()) != {contract.admissible_band}:
        raise ValueError(f"G4 {directory} activation window does not match frozen contract")
    if summary.get("activation_window") != list(contract.admissible_band):
        raise ValueError(f"G4 {directory} activation summary window drifted")
    if summary.get("scarcity_active") is not True:
        raise ValueError(f"G4 {directory} summary must report active scarcity")
    for name in COUNT_METRICS:
        if summary.get(name) != sum(record[name] for record in raw_by_key.values()):
            raise ValueError(f"G4 {directory} summary {name} does not match raw records")
    for name in NUMERIC_METRICS:
        if name == "conservation_error_l":
            continue
        expected = sum(float(record[name]) for record in raw_by_key.values())
        observed = summary.get(name)
        if not isinstance(observed, (int, float)) or not math.isclose(observed, expected, abs_tol=1.0e-12):
            raise ValueError(f"G4 {directory} summary {name} does not match raw records")
    expected_error = max(float(record["conservation_error_l"]) for record in raw_by_key.values())
    if summary.get("conservation_error_l") != expected_error:
        raise ValueError(f"G4 {directory} summary conservation_error_l does not match raw records")
    if _read_json(arm_root / "provenance.json") != lineage:
        raise ValueError(f"G4 {directory} provenance file does not match activation summary")
    return summary, raw_by_key


def audit_g4_mechanism(
    config_path: str | Path,
    output_root: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    """Audit the exact frozen G4 diagnostic support-probe evidence bundle."""

    contract = load_g4_contract(config_path)
    manifest = load_g4_probe_manifest(PROBE_MANIFEST_PATH)
    root = _require_under(Path(output_root), CANONICAL_G4_ROOT.resolve(), "output_root")
    destination = _require_under(Path(report_path), CANONICAL_G4_ROOT.resolve(), "report_path")
    if not root.is_dir():
        raise ValueError("G4 output root does not exist")
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix().lower()
        if path.is_file() and path.suffix.lower() not in SUPPORTED_G4_SUFFIXES:
            raise ValueError(f"unsupported G4 artifact file type: {relative}")
        if path.is_file() and _is_g3_endpoint_reference(relative):
            raise ValueError("G3 artifacts cannot be used as endpoint evidence")
    recorded_path = root / "artifact-manifest.json"
    if not recorded_path.exists():
        raise ValueError("G4 artifact manifest is missing")
    recorded = _read_json(recorded_path)
    artifacts = recorded.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("G4 artifact manifest must contain artifacts")
    for entry in artifacts:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            if _is_g3_endpoint_reference(entry["path"]):
                raise ValueError("G3 artifact paths cannot be endpoint evidence")
    for path in root.rglob("*.json"):
        if path.resolve() != recorded_path.resolve():
            _check_boundary(_read_json(path))
    for path in root.rglob("*.jsonl"):
        for record in _read_jsonl(path):
            _check_boundary(record)

    fixed, fixed_records = _require_arm(root, *ARM_DIRECTORIES[0], contract)
    mobile, mobile_records = _require_arm(root, *ARM_DIRECTORIES[1], contract)
    if fixed["activation_window"] != mobile["activation_window"]:
        raise ValueError("fixed and mobile activation bands must match")
    if fixed["lineage"] != mobile["lineage"]:
        raise ValueError("fixed and mobile provenance must match")
    for key in fixed_records:
        if fixed_records[key]["input_fingerprint"] != mobile_records[key]["input_fingerprint"]:
            raise ValueError("fixed and mobile raw input fingerprints must match")

    matrix = _read_json(root / "probe-matrix-summary.json")
    if matrix.get("activation_window") != list(contract.admissible_band):
        raise ValueError("probe matrix activation window drifted")
    if matrix.get("arms") != [fixed, mobile]:
        raise ValueError("probe matrix arms do not match activation summaries")
    if matrix.get("lineage") != fixed["lineage"]:
        raise ValueError("probe matrix provenance does not match activation summaries")
    expected_pairs = [
        {"fixed": fixed_records[key], "mobile": mobile_records[key]}
        for key in sorted(fixed_records)
    ]
    if matrix.get("paired_inputs") != expected_pairs:
        raise ValueError("probe matrix paired inputs do not match raw records")

    index = _read_json(root / "activation-summary.json")
    if index.get("activation_window") != list(contract.admissible_band):
        raise ValueError("activation index window drifted")
    if index.get("arms") != {
        "fixed_support_probe": "fixed/activation-summary.json",
        "mobile_support_probe": "mobile/activation-summary.json",
    }:
        raise ValueError("activation index support-probe labels drifted")
    if index.get("paired_counterfactual") != "counterfactual-summary.json":
        raise ValueError("activation index counterfactual path drifted")
    _require_lineage(index, contract)
    index_lineage = {key: index.get(key) for key in fixed["lineage"]}
    if index_lineage != fixed["lineage"]:
        raise ValueError("activation index provenance does not match activation summaries")
    root_provenance = _read_json(root / "provenance.json")
    if _require_lineage(root_provenance, contract) != fixed["lineage"]:
        raise ValueError("root provenance does not match activation summaries")

    recomputed = run_counterfactual_probe(fixed, mobile)
    counterfactual = _read_json(root / "counterfactual-summary.json")
    if counterfactual != recomputed:
        raise ValueError("stored counterfactual summary does not match recomputed values")
    if counterfactual.get("comparison") != list(contract.comparator_pair):
        raise ValueError("counterfactual diagnostic support-probe labels drifted")

    ignored = {destination.relative_to(root).as_posix()} if destination.is_relative_to(root) else set()
    verified_artifacts = _verify_manifest(root, recorded, ignored_paths=ignored)

    report: dict[str, Any] = {
        "status": "pass",
        "audit": "g4-mechanism-compliance",
        "frozen_contract_sha256": _sha256(Path(config_path)),
        "artifact_manifest_sha256": _sha256(recorded_path),
        "activation_band": list(contract.admissible_band),
        "probe_matrix_shape": [len(contract.probe_scales), len(contract.probe_seeds), len(_levels(contract))],
        "paired_deltas": counterfactual["paired_deltas"],
        "output_artifact_hashes": verified_artifacts,
        "hard_boundary": {
            "validation_accessed": False,
            "sealed_test_accessed": False,
            "battery_replenishment_enabled": False,
            "g3_endpoint_evidence_accepted": False,
            "g3_actor_or_checkpoint_executed": False,
        },
        "probe_manifest": str(manifest.source_path),
        "provenance": fixed["lineage"],
        "claim_boundary": contract.permitted_claim_boundary,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_json(destination, report)
    return report


__all__ = ["audit_g4_mechanism", "build_g4_artifact_manifest"]
