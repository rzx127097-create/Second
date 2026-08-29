from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.experiments.artifacts import artifact_sha256, atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.experiments.identity import canonical_training_identity, experiment_identity
from problem2.training.pilot import PILOT_SCENARIO_IDS, build_pilot_matrix
from problem2.training.selection import build_formal_freeze_payloads, select_candidates
from problem2.training.tuning import CanonicalValidationStore, validate_validation_episode


G5_RELATIVE = Path("outputs/problem2_sr_mappo_v1/g5")
DYNAMIC_G5_RELATIVE = Path("outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5")
METHODS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SCOPE = (
    "src/problem2",
    "scripts/freeze_g5.py",
    "scripts/run_g5_validation_tuning.py",
    "configs/problem2/g5",
    "docs/evidence/g5/physical_scenario_contract.yaml",
)


def _dynamic_evaluator_hash(root: Path) -> str:
    """Bind validation to the maintained evaluator/selector implementation."""

    return _stable_hash(
        {
            "runner": artifact_sha256(root / "src/problem2/evaluation/runner.py"),
            "selector": artifact_sha256(root / "src/problem2/evaluation/selection.py"),
        }
    )
_PROTECTED_FILE_HASHES = {
    "C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/方向.docx": "dd614abf8d221b79ce379d6830b0dd9dd384ed53a449f512ece424ccdb833a89",
    "C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/无人机蝗灾.docx": "363284c6d7dd4f0d46a95e1f45ad723e2c2b1780bcd87c1c50db428ffd30d127",
    "C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/消融.docx": "ec0a620d6ab5cb6e2055c4c1d3a90344fae6b67474b33bbc46b97879e8f9f43a",
    "D:/Pycharm/Locust_rl/data/jodhpur_drive.graphml": "b3af36efbfc87fff30bd61d204283dc40c5b8c83a80ba0ee09f3da5ef52a9462",
    "D:/Pycharm/Locust_rl/data/jodhpur_buildings.geojson": "08a81df6c8fa401014ac d161661072714d9231b2b95173cbe932c86fe57f37db".replace(" ", ""),
    "D:/Pycharm/Locust_rl/data/jodhpur_green.geojson": "b80f54c7c03ee42b4f8e8a55bfbc fbd4b7a166ed5e3eb97cd443069398ce0647".replace(" ", ""),
}


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


def _expected_refit_counts(contract: Any) -> tuple[int, int]:
    """Return the selected-refit job and scenario-reference counts from the frozen pilot matrix."""

    job_count = len(build_pilot_matrix(contract))
    return job_count, job_count * len(PILOT_SCENARIO_IDS)


def _assert_source_clean(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("source tree cleanliness cannot be established")
    if result.stdout.strip():
        raise ValueError("source tree is dirty")


def _assert_json_payload(path: Path, expected: dict[str, Any]) -> None:
    try:
        observed = _load(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"frozen payload drifted or is unreadable: {path}") from exc
    if observed != expected:
        raise ValueError(f"frozen payload drifted: {path}")


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ValueError("frozen source ancestry cannot be established")
    return result.returncode == 0


def _source_scope_hash(root: Path) -> str:
    files: list[Path] = []
    for relative in _SOURCE_SCOPE:
        candidate = root / relative
        if candidate.is_dir():
            files.extend(path for path in candidate.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
        elif candidate.is_file():
            files.append(candidate)
        else:
            raise ValueError(f"frozen source scope is missing: {relative}")
    entries = []
    for path in sorted(set(files)):
        relative = path.relative_to(root).as_posix()
        entries.append((relative, artifact_sha256(path)))
    return _stable_hash(entries)


def _protected_asset_audit() -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    for raw_path, expected in _PROTECTED_FILE_HASHES.items():
        path = Path(raw_path)
        if not path.is_file():
            raise ValueError(f"protected asset is missing: {raw_path}")
        observed = artifact_sha256(path)
        if observed != expected:
            raise ValueError(f"protected asset changed: {raw_path}")
        checked.append({"path": raw_path, "sha256": observed})
    return {"status": "pass", "checked_files": checked, "external_writes": False}


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


def _selected_jobs(
    root: Path,
    selected: dict[str, dict[str, Any]],
    source_commit: str,
    protocol_hash: str,
    source_scope_hash: str,
    contract: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    skeleton = _load(root / G5_RELATIVE / "manifests" / "g6-training-jobs.json")
    old_jobs = skeleton.get("jobs")
    if not isinstance(old_jobs, list) or len(old_jobs) != 375:
        raise ValueError("G6 training skeleton must contain 375 jobs")
    jobs: list[dict[str, Any]] = []
    canonical_map: dict[str, str] = {}
    max_steps_by_scale = {
        "g20x20_d2": 150,
        "g20x30_d3": 180,
        "g20x40_d3": 220,
        "g30x30_d3": 220,
        "g30x40_d4": 280,
        "g30x50_d4": 350,
    }
    candidate_manifest_sha256 = artifact_sha256(root / G5_RELATIVE / "manifests" / "validation-candidates.json")
    budget_manifest_sha256 = artifact_sha256(root / G5_RELATIVE / "manifests" / "pilot-budget.json")
    physical_contract_hash = contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"]
    candidate_payload = _load(root / G5_RELATIVE / "manifests" / "validation-candidates.json")
    candidate_panel_hashes = {
        str(item.get("scenario_panel_hash"))
        for rows in candidate_payload.get("candidates", {}).values()
        for item in rows
        if isinstance(item, dict)
    }
    if len(candidate_panel_hashes) != 1:
        raise ValueError("frozen candidate scenario panel hash is incomplete")
    validation_panel_hash = next(iter(candidate_panel_hashes))
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
            "environment_interactions": 200000,
            "checkpoint_interval": 10000,
            "checkpoint_count": 20,
            "max_physical_decision_steps": max_steps_by_scale[str(old["scale"])],
            "deterministic_evaluation": True,
            "validation_scenario_ids": list(range(20000, 20050)),
            "validation_scenario_panel_hash": validation_panel_hash,
            "dependency_graph": {
                "candidate_id": choice["candidate_id"],
                "candidate_config_hash": choice["config_hash"],
                "candidate_manifest_sha256": candidate_manifest_sha256,
                "budget_manifest_sha256": budget_manifest_sha256,
                "physical_scenario_contract_sha256": physical_contract_hash,
                "protocol_hash": protocol_hash,
                "source_commit": source_commit,
                "source_scope_sha256": source_scope_hash,
            },
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


def write_dynamic_replacement_manifests(
    root: Path,
    *,
    source_commit: str | None = None,
    source_scope_sha256: str | None = None,
) -> dict[str, Path]:
    """Write Phase 2 replacement manifests below the dynamic G5 root."""

    root = Path(root).resolve()
    historical = _load(root / G5_RELATIVE / "manifests" / "g6-training-jobs.json")
    jobs = historical.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 375:
        raise ValueError("historical G6 skeleton must contain 375 jobs")
    validation = _load(root / G5_RELATIVE / "manifests" / "g6-validation-evaluations.json")
    panel_hash = validation.get("scenario_panel_hash")
    protocol_hash = validation.get("provenance", {}).get("protocol_hash")
    commit = source_commit or _git_commit(root)
    scope = source_scope_sha256 or _source_scope_hash(root)
    rebound_jobs: list[dict[str, Any]] = []
    for original in jobs:
        job = dict(original)
        job["git_commit"] = commit
        job["source_scope_sha256"] = scope
        dependency = dict(job.get("dependency_graph") or {})
        dependency["source_commit"] = commit
        dependency["source_scope_sha256"] = scope
        job["dependency_graph"] = dependency
        canonical = canonical_training_identity(
            str(job["method"]),
            str(job["scale"]),
            int(job["training_seed"]),
            str(job["config_hash"]),
            commit,
        )
        job["canonical_training_identity"] = canonical
        job["identity"] = experiment_identity(
            str(job["family"]), str(job["condition_id"]), str(protocol_hash), canonical
        )
        rebound_jobs.append(job)
    jobs = rebound_jobs
    payloads = build_formal_freeze_payloads(
        jobs,
        validation_scenario_ids=range(20000, 20050),
        validation_panel_hash=panel_hash,
        sealed_scenario_ids=range(30000, 30100),
        sealed_panel_hash=_stable_hash(list(range(30000, 30100))),
        source_commit=commit,
        protocol_hash=protocol_hash,
        source_scope_sha256=scope,
    )
    payloads["g6_training"].update({
        "manifest_id": "G6-TRAINING-JOBS",
        "output_root": "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6",
        "ecology_id": "dynamic_pest_v1",
    })
    payloads["g6_validation"].update({
        "manifest_id": "G6-VALIDATION-EVALUATIONS",
        "output_root": "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6",
        "ecology_id": "dynamic_pest_v1",
        "deterministic_policy": True,
        "checkpoint_count_per_job": 20,
        "evaluator_hash": _dynamic_evaluator_hash(root),
    })
    manifest_root = root / DYNAMIC_G5_RELATIVE / "manifests"
    manifest_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "g6_training": manifest_root / "g6-training-jobs.json",
        "g6_validation": manifest_root / "g6-validation-evaluations.json",
    }
    for name, path in paths.items():
        _write(path, payloads[name])
    return paths


def freeze(root: Path, *, write: bool) -> dict[str, Any]:
    root = root.resolve()
    g5 = root / G5_RELATIVE
    validation = g5 / "validation"
    candidate_path = g5 / "manifests" / "validation-candidates.json"
    budget_path = g5 / "manifests" / "pilot-budget.json"
    selection_path = validation / "selected-configurations.json"
    episodes_path = validation / "validation-episodes.jsonl"
    validated_path = g5 / "validated" / "validation-episodes.jsonl"
    refit_path = validation / "refit" / "selected-refit.json"
    freeze_path = g5 / "freeze-manifest.json"
    for path in (candidate_path, budget_path, selection_path, episodes_path, refit_path):
        if not path.is_file():
            raise ValueError(f"required G5 freeze input is missing: {path}")
    _assert_source_clean(root)
    current_commit = _git_commit(root)
    recorded_freeze = _load(freeze_path) if freeze_path.is_file() else None
    if write:
        source_commit = current_commit
    else:
        if not isinstance(recorded_freeze, dict):
            raise ValueError("G5 freeze manifest is missing")
        source_commit = recorded_freeze.get("source_commit")
        if not isinstance(source_commit, str) or _SHA256.fullmatch(source_commit) is not None or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise ValueError("G5 freeze source commit is invalid")
        if not _is_ancestor(root, source_commit, current_commit):
            raise ValueError("G5 freeze source commit is not an ancestor of current HEAD")
    source_scope_hash = _source_scope_hash(root)
    if not write and recorded_freeze.get("source_scope_sha256") != source_scope_hash:
        raise ValueError("G5 freeze source scope drifted")
    protected_audit = _protected_asset_audit()
    selection = _load(selection_path)
    selected = selection.get("selected")
    if not isinstance(selected, dict) or set(selected) != set(METHODS):
        raise ValueError("selected configuration registry is incomplete")
    contract = load_g5_contract(root)
    if not contract.validation_tuning_authorized or contract.sealed_accessed:
        raise ValueError("G5 access contract is unsafe")
    if any(artifact_sha256(root / relative) != expected for relative, expected in contract.file_hashes.items()):
        raise ValueError("frozen contract artifact hash drifted")
    expected_refit_jobs, expected_refit_episodes = _expected_refit_counts(contract)
    candidates = _load(candidate_path)
    validation_hash = candidates.get("scenario_panel", {}).get("scenario_ids_hash")
    if not isinstance(validation_hash, str) or not _SHA256.fullmatch(validation_hash):
        raise ValueError("validation scenario panel hash is invalid")
    ledger = CanonicalValidationStore(
        root,
        output_root=validation,
        candidate_manifest=candidate_path,
        budget_manifest=budget_path,
        source_commit=source_commit,
        protocol_hash=contract.file_hashes["configs/problem2/g5/protocol.yaml"],
        scenario_panel_hash=validation_hash,
        physical_scenario_contract_hash=contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"],
    )
    rows = ledger.recover()
    if len(rows) != 20 * 3 * 50:
        raise ValueError(f"validation long table must contain 3000 rows, got {len(rows)}")
    consolidated_bytes = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        for row in rows
    )
    if write:
        atomic_write_bytes(episodes_path, consolidated_bytes)
        atomic_write_bytes(validated_path, consolidated_bytes)
    elif episodes_path.read_bytes() != consolidated_bytes or validated_path.read_bytes() != consolidated_bytes:
        raise ValueError("validated validation table drifted from canonical row files")
    if artifact_sha256(episodes_path) != artifact_sha256(validated_path):
        raise ValueError("validated and canonical validation tables differ")
    refit = _load(refit_path)
    if refit.get("status") != "pass" or refit.get("job_count") != expected_refit_jobs or refit.get("episode_count") != expected_refit_episodes:
        raise ValueError("selected development refit is incomplete")
    refit_records_path = validation / "refit" / "validated" / "pilot-episodes.jsonl"
    refit_audit_path = validation / "refit" / "audits" / "pilot-audit.json"
    refit_manifest_path = validation / "refit" / "audits" / "pilot-artifact-manifest.json"
    if not all(path.is_file() for path in (refit_records_path, refit_audit_path, refit_manifest_path)):
        raise ValueError("selected development refit artifacts are incomplete")
    refit_records = [json.loads(line) for line in refit_records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(refit_records) != expected_refit_episodes:
        raise ValueError("selected development refit long table is incomplete")
    if any(
        item.get("training_result", {}).get("refit_execution_mode") != "physical_development"
        or item.get("training_result", {}).get("training_mode") != "physical_development"
        for item in refit_records
    ):
        raise ValueError("selected development refit contains nonphysical training evidence")
    protocol_hash = contract.file_hashes["configs/problem2/g5/protocol.yaml"]
    jobs, references, decomposition = _selected_jobs(root, selected, source_commit, protocol_hash, source_scope_hash, contract)
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
    registry_hashes = {
        relative: contract.file_hashes[relative]
        for relative in (
            "configs/problem2/g5/families.yaml",
            "configs/problem2/g5/ablations.yaml",
            "configs/problem2/g5/sensitivity.yaml",
        )
    }
    payloads["g6_training"].update({
        "manifest_id": "G6-TRAINING-JOBS",
        "references": references,
        "reference_count": len(references),
        "decomposition": decomposition,
        "selected_configurations_sha256": artifact_sha256(selection_path),
        "source_scope_sha256": source_scope_hash,
        "registry_hashes": registry_hashes,
        "candidate_manifest_sha256": artifact_sha256(candidate_path),
        "budget_manifest_sha256": artifact_sha256(budget_path),
        "checkpoint_interval": 10000,
        "checkpoint_count": 20,
        "environment_interactions": 200000,
    })
    payloads["g6_training"]["ecology_id"] = "dynamic_pest_v1"
    payloads["g6_training"]["output_root"] = "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6"
    payloads["g6_training"]["source_scope_sha256"] = source_scope_hash
    payloads["g6_validation"].update({
        "manifest_id": "G6-VALIDATION-EVALUATIONS",
        "checkpoint_count_per_job": 20,
        "expected_evaluation_count": 375 * 20 * 50,
        "evaluator_hash": _dynamic_evaluator_hash(root),
        "checkpoint_selection_contract_sha256": artifact_sha256(root / "docs/evidence/g5/checkpoint_selection.yaml"),
    })
    payloads["g6_validation"].update({
        "deterministic_policy": True,
        "ecology_id": "dynamic_pest_v1",
        "output_root": "outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6",
        "source_scope_sha256": source_scope_hash,
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
        "expected_evaluation_count": 42500,
        "sealed_panel_hash": sealed_hash,
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
    expected_payloads = {
        "g6_training": payloads["g6_training"],
        "g6_validation": payloads["g6_validation"],
        "g7_sealed": payloads["g7_sealed"],
        "g7_analysis": g7_analysis,
        "diagnosis": diagnosis,
    }
    for name, expected in expected_payloads.items():
        if write:
            _write(paths[name], expected)
        else:
            _assert_json_payload(paths[name], expected)
    if write:
        dynamic_manifest_root = root / DYNAMIC_G5_RELATIVE / "manifests"
        dynamic_manifest_root.mkdir(parents=True, exist_ok=True)
        _write(dynamic_manifest_root / "g6-training-jobs.json", payloads["g6_training"])
        _write(dynamic_manifest_root / "g6-validation-evaluations.json", payloads["g6_validation"])
    for name, path in paths.items():
        if not path.is_file():
            raise ValueError(f"frozen artifact is missing: {name}")
    artifact_paths = (*paths.values(), selection_path, episodes_path, validated_path, refit_path, refit_records_path, refit_audit_path, refit_manifest_path, ledger.ledger_path)
    freeze_manifest = {
        "schema_version": "g5-freeze-v1",
        "status": "pass",
        "source_commit": source_commit,
        "source_scope_sha256": source_scope_hash,
        "validation_accessed": True,
        "sealed_accessed": False,
        "actual_unlock_count": 0,
        "counts": {"validation_rows": len(rows), "refit_jobs": expected_refit_jobs, "refit_episodes": expected_refit_episodes, "g6_base_jobs": 150, "g6_total_jobs": 375, "g7_expected_evaluations": 42500},
        "contract_hashes": dict(contract.file_hashes),
        "protected_asset_audit": protected_audit,
        "artifacts": {str(path.relative_to(root)).replace("\\", "/"): artifact_sha256(path) for path in artifact_paths},
    }
    if write:
        _write(freeze_path, freeze_manifest)
    else:
        _assert_json_payload(freeze_path, freeze_manifest)
    sealed = (root / "docs/evidence/g1/sealed_test_lock.yaml").read_text(encoding="utf-8")
    if "status: locked" not in sealed or "actual_unlock_count: 0" not in sealed or "maximum_unlock_count: 1" not in sealed:
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
