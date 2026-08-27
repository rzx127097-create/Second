from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.experiments.artifacts import artifact_sha256, atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.identity import canonical_training_identity, experiment_identity
from problem2.training.selection import build_formal_freeze_payloads
from problem2.training.tuning import ValidationAccessLedger, validate_validation_episode


G5_RELATIVE = Path("outputs/problem2_sr_mappo_v1/g5")
METHODS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile")


def _stable_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _write(path: Path, payload: Any) -> None:
    atomic_write_bytes(path, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_commit(root: Path) -> str:
    value = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if len(value) != 40:
        raise RuntimeError("Git HEAD is invalid")
    return value


def _remote_parity(root: Path) -> None:
    head = _git_commit(root)
    upstream = subprocess.check_output(["git", "rev-parse", "@{upstream}"], cwd=root, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
    remote = subprocess.check_output(["git", "ls-remote", "origin", f"refs/heads/{branch}"], cwd=root, text=True).split()[0]
    if not (head == upstream == remote):
        raise RuntimeError("local, upstream, and remote commits do not match")


def _selected_jobs(root: Path, selected: dict[str, dict[str, Any]], source_commit: str, protocol_hash: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    skeleton = _load(root / G5_RELATIVE / "manifests" / "g6-training-jobs.json")
    old_jobs = skeleton.get("jobs")
    if not isinstance(old_jobs, list) or len(old_jobs) != 375:
        raise ValueError("G6 training skeleton must contain 375 jobs")
    jobs: list[dict[str, Any]] = []
    canonical_map: dict[str, str] = {}
    for old in old_jobs:
        method = str(old["method"])
        choice = selected[method]
        config_hash = _stable_hash({
            "selected_candidate_hash": choice["config_hash"],
            "condition_id": old["condition_id"],
            "family": old["family"],
            "ablation_group": old.get("ablation_group"),
            "sensitivity_axis": old.get("sensitivity_axis"),
            "sensitivity_value": old.get("sensitivity_value"),
        })
        canonical = canonical_training_identity(method, old["scale"], int(old["training_seed"]), config_hash, source_commit)
        job = {
            **old,
            "candidate_id": choice["candidate_id"],
            "selected_candidate_config_hash": choice["config_hash"],
            "config_hash": config_hash,
            "git_commit": source_commit,
            "protocol_hash": protocol_hash,
            "canonical_training_identity": canonical,
            "identity": experiment_identity(old["family"], old["condition_id"], protocol_hash, canonical),
        }
        canonical_map[str(old["canonical_training_identity"])] = canonical
        jobs.append(job)
    if len({job["canonical_training_identity"] for job in jobs}) != 375:
        raise ValueError("selected G6 training identities are not unique")
    references = []
    for reference in skeleton.get("references", []):
        canonical = canonical_map[str(reference["canonical_training_identity"])]
        references.append({
            **reference,
            "canonical_training_identity": canonical,
            "experiment_identity": experiment_identity(reference["family"], reference["condition_id"], protocol_hash, canonical),
        })
    return jobs, references, skeleton.get("decomposition", {})


def freeze(root: Path, *, write: bool) -> dict[str, Any]:
    root = root.resolve()
    g5 = root / G5_RELATIVE
    validation = g5 / "validation"
    candidate_path = g5 / "manifests" / "validation-candidates.json"
    budget_path = g5 / "manifests" / "pilot-budget.json"
    selection_path = validation / "selected-configurations.json"
    episodes_path = validation / "validation-episodes.jsonl"
    refit_path = validation / "refit" / "selected-refit.json"
    for path in (candidate_path, budget_path, selection_path, episodes_path, refit_path):
        if not path.is_file():
            raise ValueError(f"required G5 freeze input is missing: {path}")
    selection = _load(selection_path)
    selected = selection.get("selected")
    if not isinstance(selected, dict) or set(selected) != set(METHODS):
        raise ValueError("selected configuration registry is incomplete")
    rows = [json.loads(line) for line in episodes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 20 * 3 * 50:
        raise ValueError(f"validation long table must contain 3000 rows, got {len(rows)}")
    ledger = ValidationAccessLedger(candidate_path, budget_path, validation / "validation-access.json")
    ledger.verify_rows(rows)
    for row in rows:
        validate_validation_episode(row)
    refit = _load(refit_path)
    if refit.get("status") != "pass" or refit.get("job_count") != 510 or refit.get("episode_count") != 10200:
        raise ValueError("selected development refit is incomplete")
    contract = load_g5_contract(root)
    if not contract.validation_tuning_authorized or contract.sealed_accessed:
        raise ValueError("G5 access contract is unsafe")
    source_commit = _git_commit(root)
    protocol_hash = contract.file_hashes["configs/problem2/g5/protocol.yaml"]
    jobs, references, decomposition = _selected_jobs(root, selected, source_commit, protocol_hash)
    candidates = _load(candidate_path)
    validation_hash = candidates["scenario_panel"]["scenario_ids_hash"]
    sealed_hash = _stable_hash(list(range(30000, 30100)))
    payloads = build_formal_freeze_payloads(
        jobs,
        validation_scenario_ids=range(20000, 20050),
        validation_panel_hash=validation_hash,
        sealed_scenario_ids=range(30000, 30100),
        sealed_panel_hash=sealed_hash,
        source_commit=source_commit,
        protocol_hash=protocol_hash,
    )
    payloads["g6_training"].update({
        "manifest_id": "G6-TRAINING-JOBS",
        "references": references,
        "reference_count": len(references),
        "decomposition": decomposition,
        "selected_configurations_sha256": artifact_sha256(selection_path),
    })
    payloads["g6_validation"].update({
        "manifest_id": "G6-VALIDATION-EVALUATIONS",
        "checkpoint_count_per_job": 20,
        "expected_evaluation_count": 375 * 20 * 50,
    })
    g7_analysis = {
        "schema_version": "g5.v1",
        "manifest_id": "G7-ANALYSIS",
        "status": "locked_unexecuted",
        "partition": "sealed_test",
        "statistics_contract_sha256": contract.file_hashes["configs/problem2/g5/statistics.yaml"],
        "exclusion_contract_sha256": contract.file_hashes["docs/evidence/g5/exclusion_contract.yaml"],
        "inputs": [],
        "results": [],
        "sealed_accessed": False,
        "actual_unlock_count": 0,
    }
    diagnosis = {
        "schema_version": "g5-negative-result-diagnosis-v1",
        "status": "descriptive_validation_only",
        "candidate_results": selection["candidate_results"],
        "weak_or_unfavorable_candidates": [
            item for item in selection["candidate_results"]
            if float(item["mean_validation_reduction_rate"]) < 0.85 or float(item["success_probability"]) < 1.0
        ],
        "interpretation_boundary": "pilot diagnosis only; no formal ranking or superiority claim",
        "sealed_accessed": False,
    }
    paths = {
        "g6_training": g5 / "manifests" / "g6-training-jobs.json",
        "g6_validation": g5 / "manifests" / "g6-validation-evaluations.json",
        "g7_sealed": g5 / "manifests" / "g7-sealed-evaluations.json",
        "g7_analysis": g5 / "manifests" / "g7-analysis.json",
        "diagnosis": g5 / "audits" / "negative-result-diagnosis.json",
    }
    if write:
        _write(paths["g6_training"], payloads["g6_training"])
        _write(paths["g6_validation"], payloads["g6_validation"])
        _write(paths["g7_sealed"], payloads["g7_sealed"])
        _write(paths["g7_analysis"], g7_analysis)
        _write(paths["diagnosis"], diagnosis)
    for name, path in paths.items():
        if not path.is_file():
            raise ValueError(f"frozen artifact is missing: {name}")
    freeze_manifest = {
        "schema_version": "g5-freeze-v1",
        "status": "pass",
        "source_commit": source_commit,
        "validation_accessed": True,
        "sealed_accessed": False,
        "actual_unlock_count": 0,
        "counts": {"validation_rows": 3000, "refit_jobs": 510, "g6_base_jobs": 150, "g6_total_jobs": 375, "g7_expected_evaluations": 42500},
        "artifacts": {str(path.relative_to(root)).replace("\\", "/"): artifact_sha256(path) for path in (*paths.values(), selection_path, episodes_path, refit_path)},
    }
    freeze_path = g5 / "freeze-manifest.json"
    if write:
        _write(freeze_path, freeze_manifest)
    elif _load(freeze_path) != freeze_manifest:
        raise ValueError("G5 freeze manifest drifted")
    sealed = (root / "docs/evidence/g1/sealed_test_lock.yaml").read_text(encoding="utf-8")
    if "actual_unlock_count: 0" not in sealed or "maximum_unlock_count: 1" not in sealed:
        raise ValueError("sealed lock count drifted")
    _remote_parity(root)
    return freeze_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify the final G5 freeze.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(freeze(args.root, write=args.write), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
