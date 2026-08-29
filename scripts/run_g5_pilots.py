"""Run the G5 development pilot matrix and freeze validation candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.experiments.artifacts import atomic_write_bytes
from problem2.experiments.ecology_policy import EcologyMode, resolve_output_root
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.conditions import resolve_condition_execution
from problem2.training.physical_training import run_physical_development_refit_training
from problem2.training.budget import select_pilot_budget
from problem2.training.pilot import (
    build_pilot_matrix,
    freeze_validation_candidates,
    run_pilot_matrix,
    write_pilot_artifact_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
G5_ROOT = ROOT / "outputs" / "problem2_sr_mappo_v1" / "dynamic_pest_v1" / "g5"
REPLACEMENT_ROOT = G5_ROOT / "pilots" / "replacement-48"


def _run_dynamic_pilot_job(
    job: Mapping[str, Any], device: str, interactions: int, output_root: Path
) -> dict[str, Any]:
    """Execute one replacement identity through the physical dynamic path."""

    condition_id = str(job["condition_id"])
    execution = resolve_condition_execution(condition_id)
    physical_job = {
        **dict(job),
        "candidate_id": "c01",
        "vehicle_controller": execution.vehicle_controller,
        "vehicle_trainable": execution.vehicle_trainable,
        "training_mode": execution.training_mode,
    }
    result = dict(
        run_physical_development_refit_training(
            physical_job,
            device,
            interactions,
            output_root,
        )
    )
    if result.get("completion_validated") is not True:
        raise RuntimeError("physical dynamic pilot completion was not validated")
    if result.get("candidate_id") != "c01":
        raise RuntimeError("replacement pilot did not execute frozen candidate c01")
    result["condition_id"] = condition_id
    result["vehicle_controller"] = execution.vehicle_controller
    result["vehicle_trainable"] = execution.vehicle_trainable
    result["training_mode"] = "physical_development"
    result["condition_training_mode"] = execution.training_mode
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the development-only G5 pilot matrix.")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--interactions", type=int, default=128)
    parser.add_argument("--limit", type=int, help="development-only bounded probe; cannot freeze candidates")
    parser.add_argument("--output-root", type=Path, default=REPLACEMENT_ROOT)
    parser.add_argument(
        "--ecology-mode",
        choices=tuple(mode.value for mode in EcologyMode),
        default=EcologyMode.DYNAMIC.value,
    )
    args = parser.parse_args()
    try:
        output_root = resolve_output_root(
            ROOT,
            "G5",
            args.output_root,
            primary=True,
            partition="development",
            ecology_mode=args.ecology_mode,
        )
    except ValueError as exc:
        parser.error(str(exc))
    report: dict[str, object] = {
        "schema_version": "g5-pilot-cli-v1",
        "status": "fail",
        "maturity": "M2",
        "validation_accessed": False,
        "sealed_accessed": False,
        "battery_replenishment_enabled": False,
    }
    try:
        contract = load_g5_contract(ROOT)
        jobs = build_pilot_matrix(contract)
        if args.limit is not None:
            if isinstance(args.limit, bool) or args.limit <= 0:
                raise ValueError("--limit must be positive")
            jobs = jobs[: args.limit]
        result = run_pilot_matrix(
            contract,
            output_root,
            jobs=jobs,
            interactions=args.interactions,
            device=args.device,
            runner=_run_dynamic_pilot_job,
        )
        report.update(result)
        if result["status"] != "pass":
            raise RuntimeError("pilot matrix failed; candidate freeze is blocked")
        if args.limit is not None or result["job_count"] != len(build_pilot_matrix(contract)):
            raise RuntimeError("candidate freeze requires complete pilot coverage")
        aggregates = result.get("runtime_aggregates")
        if not isinstance(aggregates, dict) or "g30x50_d4" not in aggregates:
            raise RuntimeError("pilot runtime evidence lacks representative scale")
        runtime_rows = [
            {
                "method_id": method,
                "scale_id": "g30x50_d4",
                "interactions": 1,
                "elapsed_seconds": values["seconds_per_interaction"],
            }
            for method, values in aggregates["g30x50_d4"].items()
        ]
        decision = select_pilot_budget(runtime_rows)
        pilot_base = output_root.parent if output_root.name == "pilots" else output_root
        candidate_path = pilot_base / "manifests" / "validation-candidates.json"
        candidates = freeze_validation_candidates(contract, decision, candidate_path)
        budget_payload = {
            "schema_version": "g5.v1",
            "manifest_id": "G5-PILOT-BUDGET",
            "status": "frozen_before_validation",
            "decision": {
                "selected_budget": decision.selected_budget,
                "checkpoint_interval": decision.checkpoint_interval,
                "checkpoint_count": decision.checkpoint_count,
                "projected_slowest_hours": decision.projected_slowest_hours,
            },
            "runtime_aggregates": aggregates,
            "validation_accessed": False,
            "sealed_accessed": False,
            "battery_replenishment_enabled": False,
        }
        budget_path = pilot_base / "manifests" / "pilot-budget.json"
        atomic_write_bytes(budget_path, (json.dumps(budget_payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        audit_path = Path(str(result["audit_path"]))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["budget_decision"] = budget_payload["decision"]
        audit["candidate_manifest"] = str(candidate_path)
        atomic_write_bytes(audit_path, (json.dumps(audit, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        write_pilot_artifact_manifest(
            contract,
            result["episodes_path"],
            result["audit_path"],
            manifest_path=result["artifact_manifest_path"],
        )
        report["status"] = "pass"
        report["budget_decision"] = budget_payload["decision"]
        report["candidate_manifest"] = str(candidate_path)
        report["candidate_count"] = sum(len(value) for value in candidates["candidates"].values())
    except Exception as error:
        report["status"] = "fail"
        report["reason"] = f"{type(error).__name__}: {error}"
    print(json.dumps({key: report[key] for key in ("status", "job_count", "candidate_count", "budget_decision", "reason") if key in report}, sort_keys=True))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
