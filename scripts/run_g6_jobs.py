from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from _g5_cli import read_only_preflight
from problem2.training.formal_g6 import load_frozen_job, run_formal_job


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exactly one immutable dynamic G6 training job")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--job-index", type=int, default=0)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--dry-run", action="store_true", help="validate the job and preflight without starting training")
    args = parser.parse_args()
    root = args.root.resolve()
    job = load_frozen_job(root, index=args.job_index)
    report = read_only_preflight(root, gate="G6")
    if args.dry_run:
        print(json.dumps({"job": job, "preflight": report}, sort_keys=True))
        return 0 if report.get("all_pass") else 2
    if report.get("all_pass") is not True:
        print(json.dumps({"status": "blocked", "preflight": report}, sort_keys=True))
        return 2
    result = run_formal_job(root, job, device=args.device, preflight=report)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
