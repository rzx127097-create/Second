"""Plan and execute immutable Chapter 4.5 training jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.orchestrator import Chapter45Orchestrator
from problem2.experiments.process import run_utf8_json_child


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


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
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        orchestrator = Chapter45Orchestrator(
            args.config_dir,
            args.output_root,
            protocol_path=args.protocol,
        )
        provisional = _is_provisional(orchestrator)
        jobs = orchestrator.plan(
            args.family,
            execution_profile="smoke" if args.smoke else "formal",
        )
        if args.dry_run:
            _emit({
                "status": "dry_run",
                "family": args.family,
                "provisional": provisional,
                "protocol_hash": orchestrator.protocol_hash,
                "job_count": len(jobs),
                "jobs": [job.to_dict() for job in jobs],
            })
            return 0
        if provisional and not args.smoke:
            _emit({
                "status": "rejected",
                "error": "formal matrix execution is blocked because configuration or protocol status is provisional",
            })
            return 2
        if args.max_jobs < 1:
            raise ValueError("max-jobs must be positive")
        selected = jobs[: args.max_jobs]
        outputs: list[dict[str, Any]] = []
        for planned in selected:
            identity = planned.identity
            result = run_utf8_json_child(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "train.py"),
                    "--config-dir", str(args.config_dir),
                    "--protocol", str(orchestrator.protocol_path),
                    "--family", identity.family,
                    "--condition-id", identity.condition_id,
                    "--scale", identity.scale,
                    "--seed", str(identity.training_seed),
                    "--updates", "1" if args.smoke else str(identity.target_updates),
                    "--method", identity.method,
                    "--output-root", str(args.output_root),
                    *( ["--smoke"] if args.smoke else [] ),
                ],
                cwd=ROOT,
            )
            child = result["payload"]
            outputs.append({
                **planned.to_dict(),
                "status": child.get("status", "failed"),
                "returncode": result["returncode"],
                "output": child,
            })
        accepted = bool(outputs) and all(
            item["status"] == "completed" and item["returncode"] == 0
            for item in outputs
        )
        complete = accepted and len(selected) == len(jobs)
        status = "completed" if complete else ("partial" if accepted else "failed")
        _emit({
            "status": status,
            "family": args.family,
            "smoke": bool(args.smoke),
            "protocol_hash": orchestrator.protocol_hash,
            "selected_count": len(selected),
            "total_count": len(jobs),
            "jobs": outputs,
        })
        return 0 if status in {"completed", "partial"} else 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary preserves diagnostics
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
