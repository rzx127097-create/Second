"""Evaluate completed Chapter 4.5 jobs on shared registered scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.orchestrator import Chapter45Orchestrator, select_jobs
from problem2.experiments.process import run_utf8_json_child
from problem2.experiments.recovery import load_job_record
from problem2.experiments.freeze import verify_sealed_evidence
from problem2.experiments.simulation_preflight import audit_simulation_preflight


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _is_provisional(orchestrator: Chapter45Orchestrator) -> bool:
    config = orchestrator.config
    sections = (
        config.parameters,
        config.scales,
        config.environment,
        config.algorithm,
        config.experiments,
    )
    return (
        any(section.get("status") != "verified" for section in sections)
        or config.scenario_status != "verified"
        or orchestrator.spec.status != "verified"
    )


def _scenarios_for_job(
    orchestrator: Chapter45Orchestrator,
    *,
    split: str,
    scale: str,
) -> tuple[str, ...]:
    declared = orchestrator.config.experiments[f"{split}_scenarios"]
    scenarios = tuple(
        str(scenario_id)
        for scenario_id in declared
        if str(orchestrator.config.scenarios[str(scenario_id)]["scale"]) == str(scale)
    )
    if not scenarios:
        raise ValueError(f"no {split} scenarios registered for scale {scale}")
    return scenarios


def _validate_existing_evaluation(
    path: Path,
    *,
    planned: Any,
    job: Any,
    split: str,
    scenario: str,
) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1 or not lines[0].strip():
        raise ValueError(f"existing evaluation must contain exactly one row: {path}")
    try:
        row = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ValueError(f"existing evaluation is invalid JSONL: {path}") from exc
    identity = planned.identity
    expected = {
        "method": identity.method,
        "scale": identity.scale,
        "training_seed": identity.training_seed,
        "scenario_id": scenario,
        "split": split,
        "config_hash": identity.config_hash,
        "git_commit": identity.git_commit,
        "family": identity.family,
        "condition_id": identity.condition_id,
        "protocol_hash": identity.protocol_hash,
        "job_id": identity.job_id,
        "source_tree_hash": identity.source_tree_hash,
        "checkpoint_sha256": job.checkpoint_sha256,
        "checkpoint_step": job.checkpoint_step,
    }
    mismatches = {
        key: (row.get(key), value)
        for key, value in expected.items()
        if row.get(key) != value
    }
    expected_run_id = f"{identity.job_id}:0:{scenario}"
    if row.get("run_id") != expected_run_id:
        mismatches["run_id"] = (row.get("run_id"), expected_run_id)
    if mismatches:
        raise ValueError(f"existing evaluation identity mismatch at {path}: {mismatches}")
    return row


def _sealed_receipt_allows_reuse(
    row: dict[str, Any],
    *,
    raw_path: Path,
    freeze_path: str | Path,
    unlock_path: str | Path,
) -> bool:
    verification = {
        "evidence_paths": [raw_path],
        "freeze_path": freeze_path,
        "unlock_path": unlock_path,
    }
    try:
        verify_sealed_evidence([row], **verification)
        return True
    except ValueError as exc:
        if "no consumed unlock receipt" in str(exc):
            return False
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--protocol")
    parser.add_argument(
        "--family",
        default="main_comparison",
        choices=["main_comparison", "mechanism", "sensitivity", "adaptation", "ablation"],
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--split", choices=["validation", "sealed_test"], required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--scale", action="append", default=[])
    parser.add_argument("--method", action="append", default=[])
    parser.add_argument("--seed", action="append", type=int, default=[])
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--max-scenarios", type=int)
    parser.add_argument("--freeze-manifest")
    parser.add_argument("--sealed-unlock")
    args = parser.parse_args(argv)

    try:
        if args.simulation and args.smoke:
            raise ValueError("--simulation and --smoke cannot be combined")
        if args.max_jobs < 1:
            raise ValueError("max-jobs must be positive")
        if args.max_scenarios is not None and args.max_scenarios < 1:
            raise ValueError("max-scenarios must be positive")
        orchestrator = Chapter45Orchestrator(
            args.config_dir,
            args.output_root,
            protocol_path=args.protocol,
        )
        provisional = _is_provisional(orchestrator)
        preflight = (
            audit_simulation_preflight(orchestrator.config_dir)
            if args.simulation else None
        )
        if preflight is not None and not preflight.ready:
            raise ValueError("controlled-simulation matrix evaluation failed technical preflight")
        if args.split == "sealed_test" and provisional and not args.simulation:
            raise ValueError("sealed_test is blocked because configuration or protocol status is provisional")
        if args.split == "sealed_test" and (not args.freeze_manifest or not args.sealed_unlock):
            raise ValueError("sealed_test requires a validation freeze manifest and sealed unlock record")
        if provisional and not args.smoke and not args.simulation:
            raise ValueError("formal matrix evaluation is blocked because configuration or protocol status is provisional")

        execution_profile = (
            "smoke" if args.smoke else ("simulation" if args.simulation else "formal")
        )
        family_jobs = orchestrator.plan(
            args.family,
            execution_profile=execution_profile,
        )
        jobs = select_jobs(
            family_jobs,
            scales=args.scale,
            methods=args.method,
            seeds=args.seed,
        )
        selected = jobs[: args.max_jobs]
        output_root = Path(args.output_root).resolve()
        evaluations: list[dict[str, object]] = []
        complete_scenario_sets = True
        for planned in selected:
            identity = planned.identity
            job_path = output_root / "jobs" / f"{identity.job_id}.json"
            if not job_path.is_file():
                evaluations.append({
                    "job_id": identity.job_id,
                    "method": identity.method,
                    "status": "failed",
                    "error": f"completed training job record is missing: {job_path}",
                })
                continue
            job = load_job_record(job_path)
            if job.identity != identity or job.status != "completed" or job.checkpoint_path is None:
                evaluations.append({
                    "job_id": identity.job_id,
                    "method": identity.method,
                    "status": "failed",
                    "error": "training job identity/status/checkpoint is not evaluation-ready",
                })
                continue
            scenarios = _scenarios_for_job(
                orchestrator, split=args.split, scale=identity.scale,
            )
            if args.max_scenarios is not None:
                complete_scenario_sets = complete_scenario_sets and args.max_scenarios >= len(scenarios)
                scenarios = scenarios[: args.max_scenarios]
            for scenario in scenarios:
                raw_path = output_root / "raw" / f"evaluation-{identity.job_id}-{scenario}.jsonl"
                if raw_path.is_file():
                    row = _validate_existing_evaluation(
                        raw_path, planned=planned, job=job,
                        split=args.split, scenario=scenario,
                    )
                    reusable = True
                    if args.split == "sealed_test":
                        reusable = _sealed_receipt_allows_reuse(
                            row,
                            raw_path=raw_path,
                            freeze_path=str(args.freeze_manifest),
                            unlock_path=str(args.sealed_unlock),
                        )
                    if reusable:
                        evaluations.append({
                            "job_id": identity.job_id,
                            "method": identity.method,
                            "scenario": scenario,
                            "status": "completed",
                            "raw_path": str(raw_path),
                            "reused": True,
                        })
                        continue
                result = run_utf8_json_child(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "evaluate.py"),
                        "--config-dir", str(args.config_dir),
                        "--protocol", str(orchestrator.protocol_path),
                        "--checkpoint", str(job.checkpoint_path),
                        "--split", args.split,
                        "--scenario", scenario,
                        *(
                            [
                                "--freeze-manifest", str(args.freeze_manifest),
                                "--sealed-unlock", str(args.sealed_unlock),
                            ]
                            if args.split == "sealed_test" else []
                        ),
                        *(["--smoke"] if args.smoke else []),
                        *(["--simulation"] if args.simulation else []),
                    ],
                    cwd=ROOT,
                )
                payload = result["payload"]
                evaluations.append({
                    "job_id": identity.job_id,
                    "method": identity.method,
                    "scenario": scenario,
                    "status": payload.get("status", "failed"),
                    "raw_path": payload.get("raw_path", str(raw_path)),
                    "returncode": result["returncode"],
                    "error": payload.get("error"),
                    "reused": False,
                })

        failed = [item for item in evaluations if item.get("status") != "completed"]
        all_jobs_selected = len(selected) == len(jobs)
        status = "failed" if failed else (
            "completed" if all_jobs_selected and complete_scenario_sets else "partial"
        )
        _emit({
            "status": status,
            "family": args.family,
            "split": args.split,
            "smoke": bool(args.smoke),
            "simulation": bool(args.simulation),
            "evidence_mode": preflight.evidence_mode if preflight is not None else "formal",
            "preflight": preflight.to_dict() if preflight is not None else None,
            "protocol_hash": orchestrator.protocol_hash,
            "family_job_count": len(family_jobs),
            "selected_job_count": len(jobs),
            "executed_job_count": len(selected),
            "total_job_count": len(jobs),
            "evaluation_count": len(evaluations),
            "evaluations": evaluations,
        })
        return 1 if failed else 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary preserves diagnostics
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
