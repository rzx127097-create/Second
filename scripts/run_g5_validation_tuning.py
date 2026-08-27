from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from statistics import fmean
import sys
from typing import Any, Iterable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_checkpoint
from problem2.evaluation.runner import evaluate_episode
from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.runner import run_training_job
from problem2.training.selection import select_candidates
from problem2.training.pilot import build_pilot_matrix, run_pilot_matrix, verify_pilot_artifacts
from problem2.training.tuning import (
    ValidationAccessLedger,
    build_validation_environment,
    validate_validation_episode,
)


EXPECTED_CANDIDATE_SHA256 = "67e6784b3d00d0385310d467c351f5b3374f02c7a7d7c22c571d4de29190419a"
EXPECTED_BUDGET_SHA256 = "048138954f336c95e3d339aed594c71e23167ef30cc1f4a373d5c2b10bb049cb"
METHODS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile", "maddpg_mobile", "iql_mobile")
SEEDS = (51001, 51002, 51003)
VALIDATION_IDS = tuple(range(20000, 20050))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    atomic_write_bytes(path, (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
        handle.flush()


def _row_key(row: dict[str, Any]) -> tuple[str, str, int, int]:
    return (
        str(row["method"]),
        str(row["candidate_id"]),
        int(row["training_seed"]),
        int(row["scenario_id"]),
    )


def _load_training_result(path: Path, *, method: str, candidate_id: str, config_hash: str, seed: int, interactions: int) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "method": method,
        "candidate_id": candidate_id,
        "candidate_config_hash": config_hash,
        "training_seed": seed,
        "interactions": interactions,
        "interrupted": False,
        "finite_metrics": True,
        "evaluation_frozen": True,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"recovered training result drifted: {path}")
    if not Path(payload.get("checkpoint", "")).is_file():
        raise RuntimeError(f"recovered training checkpoint is missing: {path}")
    return payload


def run_selected_refit(
    contract: Any,
    *,
    output_root: Path,
    selected: dict[str, dict[str, Any]],
    device: str,
    interactions: int = 128,
) -> dict[str, Any]:
    refit_root = output_root / "refit"
    audit_path = refit_root / "audits" / "pilot-audit.json"
    episodes_path = refit_root / "validated" / "pilot-episodes.jsonl"
    manifest_path = refit_root / "audits" / "pilot-artifact-manifest.json"
    if audit_path.is_file() and episodes_path.is_file() and manifest_path.is_file():
        verify_pilot_artifacts(contract, episodes_path, audit_path, manifest_path)
        return json.loads(audit_path.read_text(encoding="utf-8"))

    def selected_runner(job: dict[str, Any], runner_device: str, max_interactions: int, job_root: Path) -> dict[str, Any]:
        choice = selected[str(job["method"])]
        return run_training_job(
            {**job, "candidate_id": choice["candidate_id"]},
            runner_device,
            max_interactions,
            job_root,
        )

    result = run_pilot_matrix(
        contract,
        refit_root,
        jobs=build_pilot_matrix(contract),
        interactions=interactions,
        device=device,
        runner=selected_runner,
    )
    rows = [json.loads(line) for line in Path(result["episodes_path"]).read_text(encoding="utf-8").splitlines()]
    for row in rows:
        choice = selected[str(row["method"])]
        training = row["training_result"]
        if training.get("candidate_id") != choice["candidate_id"] or training.get("candidate_config_hash") != choice["config_hash"]:
            raise RuntimeError("selected development refit contains a candidate mismatch")
    _write_json(refit_root / "selected-refit.json", {
        "schema_version": "g5-selected-refit-v1",
        "status": "pass",
        "job_count": result["job_count"],
        "episode_count": result["episode_count"],
        "selected": selected,
        "episodes_sha256": _sha256(Path(result["episodes_path"])),
        "validation_accessed": True,
        "sealed_accessed": False,
    })
    return result


def run_validation_tuning(
    root: Path,
    *,
    output_root: Path,
    device: str = "cpu",
    interactions: int = 200000,
    methods: Iterable[str] = METHODS,
    seeds: Iterable[int] = SEEDS,
    scenario_ids: Iterable[int] = VALIDATION_IDS,
) -> dict[str, Any]:
    root = root.resolve()
    output_root = output_root.resolve()
    candidates_path = root / "outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json"
    budget_path = root / "outputs/problem2_sr_mappo_v1/g5/manifests/pilot-budget.json"
    if _sha256(candidates_path) != EXPECTED_CANDIDATE_SHA256 or _sha256(budget_path) != EXPECTED_BUDGET_SHA256:
        raise RuntimeError("frozen candidate or budget hash differs before validation access")
    contract = load_g5_contract(root)
    scenario_tuple = tuple(scenario_ids)
    method_tuple = tuple(methods)
    seed_tuple = tuple(seeds)
    if scenario_tuple != VALIDATION_IDS:
        raise ValueError("validation tuning requires exactly scenarios 20000-20049")
    if interactions != 200000 and output_root == (root / "outputs/problem2_sr_mappo_v1/g5/validation").resolve():
        raise ValueError("canonical validation tuning requires exactly 200000 interactions")
    ledger = ValidationAccessLedger(candidates_path, budget_path, output_root / "validation-access.json")
    if interactions != ledger.interactions:
        if output_root == (root / "outputs/problem2_sr_mappo_v1/g5/validation").resolve():
            raise ValueError("canonical candidate budget drifted")
        ledger.interactions = interactions
    candidate_payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    consolidated = output_root / "validation-episodes.jsonl"
    existing_rows = [] if not consolidated.exists() else [
        json.loads(line) for line in consolidated.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ledger.verify_rows(existing_rows)
    existing_by_key: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for row in existing_rows:
        key = _row_key(row)
        if key in existing_by_key:
            raise RuntimeError("validation recovery contains a duplicate identity")
        existing_by_key[key] = row
    expected_order = [
        (method, candidate["candidate_id"], seed, scenario_id)
        for method in method_tuple
        for candidate in candidate_payload["candidates"][method]
        for seed in seed_tuple
        for scenario_id in scenario_tuple
    ]
    if list(existing_by_key) != expected_order[: len(existing_by_key)]:
        raise RuntimeError("validation recovery rows are not an exact execution prefix")
    summaries: list[dict[str, Any]] = []
    for method in method_tuple:
        if method not in METHODS:
            raise ValueError(f"unknown tuning method {method}")
        for candidate in candidate_payload["candidates"][method]:
            candidate_rows: list[dict[str, Any]] = []
            candidate_id = candidate["candidate_id"]
            for seed in seed_tuple:
                train_root = output_root / "training" / method / candidate_id / str(seed)
                summary_path = train_root / f"{method}__{method}__{seed}" / "summary.json"
                result = _load_training_result(
                    summary_path,
                    method=method,
                    candidate_id=candidate_id,
                    config_hash=candidate["config_hash"],
                    seed=seed,
                    interactions=interactions,
                )
                if result is None:
                    try:
                        result = run_training_job(
                            {
                                "source_root": root,
                                "_contract": contract,
                                "method": method,
                                "condition_id": method,
                                "candidate_id": candidate_id,
                                "partition": "development",
                                "scenario_id": 10000,
                                "scenario_ids": list(range(10000, 10020)),
                                "training_seed": seed,
                                "scale": "g20x20_d2",
                            },
                            device,
                            interactions,
                            train_root,
                        )
                    except Exception as exc:
                        _write_json(output_root / "failures" / f"{method}__{candidate_id}__{seed}.json", {
                            "method": method,
                            "candidate_id": candidate_id,
                            "config_hash": candidate["config_hash"],
                            "training_seed": seed,
                            "interaction_count": interactions,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "validation_accessed": bool(existing_rows),
                            "sealed_accessed": False,
                        })
                        raise
                algorithm, _ = load_checkpoint(
                    Path(result["checkpoint"]),
                    lambda: build_algorithm(method, contract, device, candidate_id=candidate_id, scale="g20x20_d2"),
                    expected_provenance=result["provenance"],
                )
                for scenario_id in scenario_tuple:
                    key = (method, candidate_id, seed, scenario_id)
                    if key in existing_by_key:
                        candidate_rows.append(existing_by_key[key])
                        continue
                    environment = build_validation_environment(root, scenario_id=scenario_id, scale="g20x20_d2")
                    record = evaluate_episode(environment, algorithm, "validation", scenario_id)
                    row = {
                        "method": method,
                        "candidate_id": candidate_id,
                        "config_hash": candidate["config_hash"],
                        "partition": "validation",
                        "scenario_id": scenario_id,
                        "training_seed": seed,
                        "interaction_count": interactions,
                        "initial_total_pest": float(environment.initial_pest.sum()),
                        "final_total_pest": float(environment.pest.sum()),
                        "reduction_rate": float(record.reduction_rate or 0.0),
                        "success_at_0_85": bool(record.success_at_0_85),
                        "spray_action_count": environment.spray_action_count,
                        "sprayed_pesticide_l": environment.sprayed_pesticide_l,
                        "metric_source": "action_driven_environment",
                        "validation_accessed": True,
                        "sealed_accessed": False,
                        "battery_replenishment_enabled": False,
                        "episode_metrics": asdict(record),
                    }
                    validate_validation_episode(row)
                    ledger.append(row)
                    _append_jsonl(consolidated, row)
                    candidate_rows.append(row)
            summary = {
                "method": method,
                "candidate_id": candidate_id,
                "config_hash": candidate["config_hash"],
                "mean_validation_reduction_rate": fmean(row["reduction_rate"] for row in candidate_rows),
                "success_probability": fmean(float(row["success_at_0_85"]) for row in candidate_rows),
                "interaction_count": interactions,
                "episode_count": len(candidate_rows),
                "failed_episode_count": 0,
                "sealed_accessed": False,
            }
            summaries.append(summary)
            _write_json(output_root / "summaries" / f"{method}__{candidate_id}.json", summary)
    selected = select_candidates(summaries)
    payload = {
        "schema_version": "g5-validation-selection-v1",
        "status": "selected_mechanically",
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_SHA256,
        "budget_manifest_sha256": EXPECTED_BUDGET_SHA256,
        "candidate_results": summaries,
        "selected": selected,
        "validation_episode_count": sum(item["episode_count"] for item in summaries),
        "validation_accessed": True,
        "sealed_accessed": False,
        "actual_unlock_count": 0,
    }
    _write_json(output_root / "selected-configurations.json", payload)
    refit = run_selected_refit(contract, output_root=output_root, selected=selected, device=device)
    payload["selected_refit"] = {
        "job_count": refit["job_count"],
        "episode_count": refit["episode_count"],
        "status": refit["status"],
    }
    _write_json(output_root / "selected-configurations.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, default=Path("outputs/problem2_sr_mappo_v1/g5/validation"))
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--interactions", type=int, default=200000)
    args = parser.parse_args()
    print(json.dumps(run_validation_tuning(args.root, output_root=args.output_root, device=args.device, interactions=args.interactions), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
