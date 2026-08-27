from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable

import numpy as np

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_checkpoint
from problem2.evaluation.runner import evaluate_episode
from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.runner import run_training_job
from problem2.training.selection import select_candidates
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
    if tuple(scenario_ids) != VALIDATION_IDS:
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
    if consolidated.exists():
        raise RuntimeError("validation output already exists; use the recovery audit instead of overwriting")
    summaries: list[dict[str, Any]] = []
    for method in tuple(methods):
        if method not in METHODS:
            raise ValueError(f"unknown tuning method {method}")
        for candidate in candidate_payload["candidates"][method]:
            candidate_rows: list[dict[str, Any]] = []
            candidate_id = candidate["candidate_id"]
            for seed in tuple(seeds):
                train_root = output_root / "training" / method / candidate_id / str(seed)
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
                algorithm, _ = load_checkpoint(
                    Path(result["checkpoint"]),
                    lambda: build_algorithm(method, contract, device, candidate_id=candidate_id, scale="g20x20_d2"),
                    expected_provenance=result["provenance"],
                )
                for scenario_id in VALIDATION_IDS:
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
