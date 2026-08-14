"""Enumerate immutable experiment-matrix jobs without hidden execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.config import config_identity, load_config_bundle
from problem2.experiments.job_identity import capture_git_commit, make_job_identity
from problem2.experiments.process import run_utf8_json_child


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _is_provisional(config: Any) -> bool:
    return any(section.get("status") != "verified" for section in (config.parameters, config.scales, config.environment, config.algorithm, config.experiments)) or config.scenario_status != "verified"


def _jobs(config: Any, *, execution_profile: str = "formal") -> list[dict[str, object]]:
    digest = config_identity(config)
    commit = capture_git_commit(str(ROOT))
    jobs: list[dict[str, object]] = []
    for scale in config.experiments["scales"]:
        for seed in config.experiments["training_seeds"]:
            for method in config.experiments["methods"]:
                identity = make_job_identity(
                    method, scale, seed, digest, config_hash=digest, git_commit=commit,
                    execution_profile=execution_profile,
                    target_updates=1 if execution_profile == "smoke" else int(config.algorithm.get("updates", 0)),
                    rollout_horizon=3 if execution_profile == "smoke" else int(config.algorithm.get("rollout_horizon", 0)),
                )
                jobs.append({**identity.to_dict(), "job_id": identity.job_id})
    return jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        config = load_config_bundle(args.config_dir)
        provisional = _is_provisional(config)
        jobs = _jobs(config, execution_profile="smoke" if args.smoke else "formal")
        if args.dry_run:
            _emit({"status": "dry_run", "provisional": provisional, "job_count": len(jobs), "jobs": jobs})
            return 0
        if provisional and not args.smoke:
            _emit({"status": "rejected", "error": "formal matrix execution is blocked because a configuration status is provisional"})
            return 2
        if not args.smoke:
            raise ValueError("matrix execution requires explicit --smoke until a formal executor is configured")
        if args.max_jobs < 1:
            raise ValueError("max-jobs must be positive")
        if not any(job["method"] == "sr_mappo_mobile" for job in jobs):
            _emit({"status": "failed", "selected_count": 0, "total_count": len(jobs), "error": "matrix has no sr_mappo_mobile jobs to execute"})
            return 1
        selected = jobs[:args.max_jobs]
        outputs = []
        for job in selected:
            if job["method"] != "sr_mappo_mobile":
                outputs.append({
                    **job,
                    "status": "rejected",
                    "error": f"smoke executor has no training worker for method {job['method']}",
                })
                continue
            result = run_utf8_json_child(
                [
                    sys.executable, str(ROOT / "scripts" / "train.py"), "--config-dir", args.config_dir,
                    "--scale", str(job["scale"]), "--seed", str(job["training_seed"]), "--updates", "1",
                    "--output-root", args.output_root, "--smoke",
                ],
                cwd=ROOT,
            )
            child = result["payload"]
            outputs.append({**job, "status": child.get("status", "failed"), "returncode": result["returncode"], "output": child})
        all_accepted = bool(outputs) and all(item["status"] == "completed" and item.get("returncode", 0) == 0 for item in outputs)
        complete = all_accepted and len(selected) == len(jobs)
        status = "completed" if complete else ("partial" if all_accepted else "failed")
        _emit({
            "status": status,
            "smoke": True,
            "selected_count": len(selected),
            "total_count": len(jobs),
            "jobs": outputs,
        })
        return 0 if status in {"completed", "partial"} else 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary must preserve diagnostics as JSON
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
