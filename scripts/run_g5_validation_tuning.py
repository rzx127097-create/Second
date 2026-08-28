from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from statistics import fmean
import subprocess
import sys
from typing import Any, Iterable, Mapping

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import load_training_checkpoint
from problem2.evaluation.runner import evaluate_episode
from problem2.experiments.artifacts import atomic_write_bytes, write_quarantine
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.runner import run_training_job
from problem2.training.physical_training import (
    EXPECTED_BUDGET_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    PHYSICAL_TRAINING_SCHEMA_VERSION,
    run_physical_candidate_training,
    run_physical_development_refit_training,
    run_noncanonical_physical_candidate_training_for_test,
    validate_physical_training_completion,
)
from problem2.training.selection import select_candidates
from problem2.training.pilot import build_pilot_matrix, run_pilot_matrix, verify_pilot_artifacts
from problem2.training.tuning import (
    CANONICAL_SCALE,
    CanonicalValidationStore,
    build_validation_environment,
    map_validation_episode_to_raw,
    validate_validation_episode,
)


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


def _load_training_result(
    path: Path,
    *,
    root: Path,
    method: str,
    candidate_id: str,
    config_hash: str,
    seed: int,
    interactions: int,
    device: str,
    canonical: bool,
) -> dict[str, Any] | None:
    """Load only a manifest-complete identity through the shared strict validator."""

    if not path.is_file():
        if path.parent.is_dir() and any(
            (path.parent / name).exists()
            for name in ("checkpoint.pt", "physical-episodes.jsonl", "summary.json")
        ):
            raise RuntimeError(f"physical training completion manifest is missing: {path}")
        return None
    contract = load_g5_contract(root)
    return validate_physical_training_completion(
        path,
        contract=contract,
        method=method,
        candidate_id=candidate_id,
        config_hash=config_hash,
        seed=seed,
        interactions=interactions,
        scale=CANONICAL_SCALE if canonical else "g20x20_d2",
        device=device,
        canonical=canonical,
    )


def _quarantine_attempt(identity_root: Path, attempt_root: Path, error: Exception) -> None:
    payload = bytearray()
    for name in ("manifest.json", "summary.json", "physical-episodes.jsonl", "checkpoint.pt"):
        path = attempt_root / name
        if path.is_file():
            payload.extend(name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    write_quarantine(
        identity_root / "quarantine.jsonl",
        bytes(payload),
        locator=str(attempt_root),
        reason=f"{type(error).__name__}: {error}",
    )


def _attempt_roots(identity_root: Path, method: str, seed: int) -> list[tuple[int, Path]]:
    if not identity_root.is_dir():
        return []
    result: list[tuple[int, Path]] = []
    for candidate in identity_root.iterdir():
        match = re.fullmatch(r"attempt-(\d{6})", candidate.name)
        if match and candidate.is_dir():
            result.append((int(match.group(1)), candidate / f"{method}__{method}__{seed}"))
    return sorted(result)


def _train_frozen_candidates(
    root: Path,
    *,
    output_root: Path,
    device: str,
    interactions: int,
    methods: Iterable[str],
    seeds: Iterable[int],
    canonical: bool,
    rerun_invalid_from_scratch: bool,
) -> dict[str, Any]:
    root = root.resolve()
    output_root = output_root.resolve()
    canonical_root = (root / "outputs/problem2_sr_mappo_v1/g5/validation").resolve()
    if canonical:
        if not output_root.is_relative_to(canonical_root):
            raise ValueError("canonical training output must be confined below the G5 validation root")
        if type(interactions) is not int or interactions != 200000:
            raise ValueError("canonical train-only requires exactly 200000 interactions")
    return _run_candidate_matrix(
        root,
        output_root=output_root,
        device=device,
        interactions=interactions,
        methods=methods,
        seeds=seeds,
        canonical=canonical,
        rerun_invalid_from_scratch=rerun_invalid_from_scratch,
    )


def train_frozen_candidates(
    root: Path,
    *,
    output_root: Path,
    device: str,
    interactions: int,
    methods: Iterable[str],
    seeds: Iterable[int],
    rerun_invalid_from_scratch: bool = False,
) -> dict[str, Any]:
    return _train_frozen_candidates(
        root,
        output_root=output_root,
        device=device,
        interactions=interactions,
        methods=methods,
        seeds=seeds,
        canonical=True,
        rerun_invalid_from_scratch=rerun_invalid_from_scratch,
    )


def train_frozen_candidates_for_test(
    root: Path,
    *,
    output_root: Path,
    device: str,
    interactions: int,
    methods: Iterable[str],
    seeds: Iterable[int],
    rerun_invalid_from_scratch: bool = False,
) -> dict[str, Any]:
    canonical_root = (root.resolve() / "outputs/problem2_sr_mappo_v1/g5/validation").resolve()
    if output_root.resolve().is_relative_to(canonical_root):
        raise ValueError("noncanonical test training cannot use the canonical validation root")
    return _train_frozen_candidates(
        root,
        output_root=output_root,
        device=device,
        interactions=interactions,
        methods=methods,
        seeds=seeds,
        canonical=False,
        rerun_invalid_from_scratch=rerun_invalid_from_scratch,
    )


def _run_candidate_matrix(
    root: Path,
    *,
    output_root: Path,
    device: str,
    interactions: int,
    methods: Iterable[str],
    seeds: Iterable[int],
    canonical: bool,
    rerun_invalid_from_scratch: bool,
) -> dict[str, Any]:
    method_tuple = tuple(methods)
    seed_tuple = tuple(seeds)
    if not method_tuple or any(method not in METHODS for method in method_tuple):
        raise ValueError("train-only methods must be registered frozen learning methods")
    if len(set(method_tuple)) != len(method_tuple):
        raise ValueError("train-only methods contain a duplicate identity")
    if not seed_tuple or any(type(seed) is not int or seed not in SEEDS for seed in seed_tuple):
        raise ValueError("train-only training seed is outside the frozen development partition")
    if len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("train-only seeds contain a duplicate identity")
    if type(interactions) is not int or interactions <= 0:
        raise ValueError("train-only interactions must be a positive integer")
    contract = load_g5_contract(root)
    candidates_path = root / "outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json"
    budget_path = root / "outputs/problem2_sr_mappo_v1/g5/manifests/pilot-budget.json"
    if _sha256(candidates_path) != EXPECTED_CANDIDATE_SHA256 or _sha256(budget_path) != EXPECTED_BUDGET_SHA256:
        raise RuntimeError("frozen candidate or budget hash differs before training")
    candidate_payload = _load_training_candidate_manifest(candidates_path)
    if candidate_payload.get("equal_environment_interactions") != 200000:
        raise ValueError("candidate manifest must declare exactly 200000 environment interactions")
    for declared_method, rows in candidate_payload["candidates"].items():
        if declared_method not in METHODS or not isinstance(rows, list) or len(rows) != 4:
            raise ValueError("candidate manifest must declare four candidates for every method")
        for candidate in rows:
            if candidate.get("environment_interactions") != 200000:
                raise ValueError("every candidate must declare exactly 200000 environment interactions")
    completed = 0
    requested_identities: list[dict[str, Any]] = []
    summary_paths: list[str] = []
    validated_results: list[dict[str, Any]] = []
    for method in method_tuple:
        for candidate in candidate_payload["candidates"][method]:
            for seed in seed_tuple:
                identity_root = output_root / "training" / method / candidate["candidate_id"] / str(seed)
                result: dict[str, Any] | None = None
                attempts = _attempt_roots(identity_root, method, seed)
                for _, attempt_root in reversed(attempts):
                    try:
                        result = _load_training_result(
                            attempt_root / "manifest.json",
                            root=root,
                            method=method,
                            candidate_id=candidate["candidate_id"],
                            config_hash=candidate["config_hash"],
                            seed=seed,
                            interactions=interactions,
                            device=device,
                            canonical=canonical,
                        )
                    except Exception as exc:
                        _quarantine_attempt(identity_root, attempt_root, exc)
                        if not rerun_invalid_from_scratch:
                            raise
                        continue
                    if result is not None:
                        break
                if result is None:
                    attempt_number = (max((number for number, _ in attempts), default=0) + 1)
                    train_root = identity_root / f"attempt-{attempt_number:06d}"
                    runner = run_physical_candidate_training if canonical else run_noncanonical_physical_candidate_training_for_test
                    training_scale = CANONICAL_SCALE if canonical else "g20x20_d2"
                    result = runner(
                        {
                            "source_root": root,
                            "_contract": contract,
                            "method": method,
                            "condition_id": method,
                            "candidate_id": candidate["candidate_id"],
                            "partition": "development",
                            "scenario_id": 10000,
                            "scenario_ids": list(range(10000, 10020)),
                            "training_seed": seed,
                            "scale": training_scale,
                        },
                        device,
                        interactions,
                        train_root,
                    )
                    result = _load_training_result(
                        Path(result["manifest"]),
                        root=root,
                        method=method,
                        candidate_id=candidate["candidate_id"],
                        config_hash=candidate["config_hash"],
                        seed=seed,
                        interactions=interactions,
                        device=device,
                        canonical=canonical,
                    )
                requested_identities.append({
                    "method": method,
                    "candidate_id": candidate["candidate_id"],
                    "training_seed": seed,
                })
                summary_paths.append(str(Path(result["summary"]).resolve()))
                validated_results.append(result)
                completed += 1
                print(json.dumps({"event": "training_complete", "method": method, "candidate_id": candidate["candidate_id"], "seed": seed, "completed": completed}), flush=True)
    return {
        "status": "training_complete",
        "job_count": completed,
        "requested_identities": requested_identities,
        "summary_paths": summary_paths,
        "validation_accessed": False,
        "sealed_accessed": False,
        "canonical": canonical,
        "evidence_status": "canonical_candidate_evidence" if canonical else "noncanonical_test_only",
        "_validated_results": validated_results,
    }


def _load_training_candidate_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), dict):
        raise ValueError("validation candidate manifest is invalid")
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
        return _run_selected_refit_job(
            job,
            runner_device,
            max_interactions,
            job_root,
            selected=selected,
            contract=contract,
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


def _run_selected_refit_job(
    job: Mapping[str, Any],
    device: str,
    interactions: int,
    output_root: Path,
    *,
    selected: Mapping[str, Mapping[str, Any]],
    contract: Any,
) -> dict[str, Any]:
    """Run one selected pilot identity through the physical refit runner."""

    method = str(job["method"])
    choice = selected.get(method)
    if not isinstance(choice, Mapping):
        raise ValueError(f"selected refit lacks a configuration for {method}")
    physical_job = {
        **dict(job),
        "condition_id": method,
        "candidate_id": choice["candidate_id"],
        "_contract": contract,
    }
    physical_result = dict(
        run_physical_development_refit_training(
            physical_job,
            device,
            interactions,
            output_root,
        )
    )
    if physical_result.get("candidate_config_hash") != choice.get("config_hash"):
        raise RuntimeError("physical selected refit returned a candidate hash mismatch")
    physical_result["condition_id"] = str(job["condition_id"])
    physical_result["refit_condition_id"] = str(job["condition_id"])
    physical_result["refit_training_condition_id"] = method
    physical_result["refit_execution_mode"] = "physical_development"
    return physical_result


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
    canonical_root = (root / "outputs/problem2_sr_mappo_v1/g5/validation").resolve()
    if output_root != canonical_root:
        raise ValueError("canonical validation output must be the frozen G5 validation root")
    if scenario_tuple != VALIDATION_IDS:
        raise ValueError("validation tuning requires exactly scenarios 20000-20049")
    if method_tuple != METHODS or seed_tuple != SEEDS:
        raise ValueError("validation tuning requires every frozen method and training seed")
    if interactions != 200000:
        raise ValueError("canonical validation tuning requires exactly 200000 interactions")
    candidate_payload = _load_training_candidate_manifest(candidates_path)
    panel_hashes = {str(item["scenario_panel_hash"]) for rows in candidate_payload["candidates"].values() for item in rows}
    if len(panel_hashes) != 1:
        raise RuntimeError("frozen candidate scenario panel hashes disagree")
    protocol_hash = contract.file_hashes["configs/problem2/g5/protocol.yaml"]
    evaluator_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        source_commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("canonical validation requires a Git source commit") from exc
    ledger = CanonicalValidationStore(
        root,
        output_root=output_root,
        candidate_manifest=candidates_path,
        budget_manifest=budget_path,
        source_commit=source_commit,
        protocol_hash=protocol_hash,
        scenario_panel_hash=next(iter(panel_hashes)),
        physical_scenario_contract_hash=contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"],
        require_dynamic_ecology=True,
    )
    if interactions != ledger.interactions:
        raise ValueError("canonical candidate budget drifted")
    with ledger.exclusive_lock():
        training = _train_frozen_candidates(
            root,
            output_root=output_root,
            device=device,
            interactions=interactions,
            methods=method_tuple,
            seeds=seed_tuple,
            canonical=True,
            rerun_invalid_from_scratch=False,
        )
        validated_training = {
            (row["method"], row["candidate_id"], row["training_seed"]): row
            for row in training["_validated_results"]
        }
        existing_rows = ledger.recover()
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
                    result = validated_training[(method, candidate_id, seed)]
                    algorithm, _ = load_training_checkpoint(
                        Path(result["checkpoint"]),
                        lambda: build_algorithm(method, contract, device, candidate_id=candidate_id, scale=CANONICAL_SCALE),
                        result["checkpoint_provenance"],
                    )
                    for scenario_id in scenario_tuple:
                        key = (method, candidate_id, seed, scenario_id)
                        if key in existing_by_key:
                            candidate_rows.append(existing_by_key[key])
                            continue
                        try:
                            environment = build_validation_environment(root, scenario_id=scenario_id, scale=CANONICAL_SCALE)
                            record = evaluate_episode(environment, algorithm, "validation", scenario_id)
                            compact_row = {
                                "method": method,
                                "candidate_id": candidate_id,
                                "config_hash": candidate["config_hash"],
                                "partition": "validation",
                                "scenario_id": scenario_id,
                                "training_seed": seed,
                                "interaction_count": interactions,
                                "initial_total_pest": float(environment.initial_prey.sum()),
                                "final_total_pest": float(environment.prey.sum()),
                                "reduction_rate": 1.0 - float(environment.prey.sum()) / float(environment.initial_prey.sum()),
                                "success_at_0_85": bool(record.success_at_0_85),
                                "spray_action_count": environment.spray_action_count,
                                "sprayed_pesticide_l": environment.sprayed_pesticide_l,
                                "pesticide_initial_l": float(environment.physical.state.ledger.initial_total_l),
                                "pesticide_remaining_l": float(sum(item.pesticide_l for item in environment.physical.state.uavs) + environment.physical.state.vehicle.inventory_l),
                                "pesticide_transferred_l": float(environment.physical.state.ledger.initial_total_l) - float(sum(item.pesticide_l for item in environment.physical.state.uavs) + environment.physical.state.vehicle.inventory_l),
                                "resource_conservation_residual_l": 0.0,
                                "mechanism_metrics": asdict(record),
                                "metric_source": "dynamic_ecology_environment",
                                "ecology_version": environment.ecology.config.version,
                                "ecology_config_sha256": environment.ecology.config.contract_sha256,
                                "ecology_scenario_sha256": environment.ecology.scenario.scenario_sha256,
                                "ecology_source_commit": environment.ecology.scenario.source_commit,
                                "ecology_implementation_version": environment.ecology.scenario.implementation_version,
                                "initial_total_predator": float(environment.initial_predator.sum()),
                                "final_total_predator": float(environment.predator.sum()),
                                "cumulative_deposited_effect": environment.ecology.deposited_effect,
                                "terminal_mean_concentration": float(environment.ecology.concentration.mean()),
                                "terminal_max_concentration": float(environment.ecology.concentration.max()),
                                "terminal_wind_direction": float(environment.ecology.wind_state.direction),
                                "terminal_wind_strength": float(environment.ecology.wind_state.strength),
                                "dynamic_step_count": environment.ecology.step_count,
                                "validation_accessed": True,
                                "sealed_accessed": False,
                                "battery_replenishment_enabled": False,
                                "episode_metrics": asdict(record),
                            }
                            validate_validation_episode(compact_row)
                            row = map_validation_episode_to_raw(
                                compact_row,
                                source_commit=source_commit,
                                protocol_hash=protocol_hash,
                                checkpoint_hash=_sha256(Path(result["checkpoint"])),
                                evaluator_hash=evaluator_hash,
                                scenario_panel_hash=candidate["scenario_panel_hash"],
                                raw_trace_locator=f"{environment.source_provenance.get('ecology_scenario_sha256', 'environment')}:scenario-{scenario_id}",
                                candidate_manifest_sha256=EXPECTED_CANDIDATE_SHA256,
                                budget_manifest_sha256=EXPECTED_BUDGET_SHA256,
                                physical_scenario_contract_sha256=contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"],
                            )
                            ledger.commit_row(row)
                        except Exception as exc:
                            ledger.record_technical_failure(key, exc)
                            raise
                        existing_by_key[key] = row
                        candidate_rows.append(row)
                failure_count = sum(
                    1
                    for failure in ledger.failure_records()
                    if tuple(failure.get("identity", ()))[:2] == (method, candidate_id)
                )
                summary = {
                    "method": method,
                    "candidate_id": candidate_id,
                    "config_hash": candidate["config_hash"],
                    "mean_validation_reduction_rate": fmean(row["reduction_rate"] for row in candidate_rows),
                    "success_probability": fmean(float(row["success_at_0_85"]) for row in candidate_rows),
                    "interaction_count": interactions,
                    "episode_count": len(candidate_rows),
                    "failed_episode_count": failure_count,
                    "sealed_accessed": False,
                }
                summaries.append(summary)
                _write_json(output_root / "summaries" / f"{method}__{candidate_id}.json", summary)
        ledger.consolidate()
        if len(ledger.recover()) != 3000:
            raise RuntimeError("canonical validation requires exactly 3000 committed rows before selection")
        selected = select_candidates(
            summaries,
            require_complete=True,
            expected_cell_count=3000,
            candidate_manifest_sha256=EXPECTED_CANDIDATE_SHA256,
            budget_manifest_sha256=EXPECTED_BUDGET_SHA256,
            physical_scenario_contract_sha256=contract.file_hashes["docs/evidence/g5/physical_scenario_contract.yaml"],
        )
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
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--interactions", type=int, default=200000)
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--rerun-invalid-from-scratch", action="store_true")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in SEEDS))
    args = parser.parse_args()
    root = args.root.resolve()
    output_root = (
        (args.output_root if args.output_root.is_absolute() else root / args.output_root).resolve()
        if args.output_root is not None
        else (root / "outputs/problem2_sr_mappo_v1/g5/validation").resolve()
    )
    methods = tuple(value for value in args.methods.split(",") if value)
    seeds = tuple(int(value) for value in args.seeds.split(",") if value)
    result = (
        train_frozen_candidates(root, output_root=output_root, device=args.device, interactions=args.interactions, methods=methods, seeds=seeds, rerun_invalid_from_scratch=args.rerun_invalid_from_scratch)
        if args.train_only
        else run_validation_tuning(root, output_root=output_root, device=args.device, interactions=args.interactions, methods=methods, seeds=seeds)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
