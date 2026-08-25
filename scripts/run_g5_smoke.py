"""Run the bounded G5 development smoke and emit an auditable summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.preflight import run_preflight
from problem2.training.runner import ALL_CONDITION_TYPES, METHODS, run_training_job


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "problem2_sr_mappo_v1" / "g5" / "smoke"
AUDIT_PATH = ROOT / "outputs" / "problem2_sr_mappo_v1" / "g5" / "audits" / "smoke-audit.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--interactions", type=int, default=128)
    parser.add_argument("--all-methods", action="store_true")
    parser.add_argument("--all-condition-types", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    args = parser.parse_args()
    contract = load_g5_contract(ROOT)
    preflight = run_preflight(args.device, ROOT)
    report = {"schema_version": "g5-smoke-audit-v1", "status": "pass", "maturity": "M2", "preflight": preflight, "jobs": [], "validation_accessed": False, "sealed_accessed": False, "battery_replenishment_enabled": False}
    if preflight.get("status") != "pass":
        report["status"] = "fail"
        report["reason"] = preflight.get("reason", "preflight failed")
    else:
        methods = METHODS if args.all_methods or not args.method else (args.method,)
        conditions = ALL_CONDITION_TYPES if args.all_condition_types else ("sr_mappo_mobile",)
        for method in methods:
            for condition in conditions:
                job = {"method": method, "condition_id": condition, "training_seed": 51001, "scenario_id": 10000, "partition": "development", "source_root": str(ROOT)}
                try:
                    report["jobs"].append(run_training_job(job, args.device, args.interactions, OUTPUT_ROOT))
                except Exception as error:
                    report["status"] = "fail"
                    report["reason"] = f"{type(error).__name__}: {error}"
                    break
            if report["status"] != "pass":
                break
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "jobs": len(report["jobs"]), "audit": str(AUDIT_PATH)}, sort_keys=True))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
