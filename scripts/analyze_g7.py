"""JSON adapter for pure G7 analysis helpers; it never opens sealed paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from problem2.statistics.convergence import summarize_convergence
from problem2.statistics.diagnosis import diagnose_result_bundle
from problem2.statistics.mechanism import summarize_mechanism


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze validated non-sealed G7-compatible rows")
    parser.add_argument("--input", type=Path, help="explicit JSON input path; stdin when omitted")
    parser.add_argument("--output", type=Path, help="explicit JSON output path; stdout when omitted")
    parser.add_argument("--analysis", choices=("convergence", "mechanism", "diagnosis"), default="mechanism")
    parser.add_argument("--budget", type=int)
    args = parser.parse_args(argv)
    try:
        source = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        payload = json.loads(source)
        if not isinstance(payload, dict) or payload.get("validated", True) is not True:
            raise ValueError("input must be a validated JSON mapping")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError("payload requires rows")
        if args.analysis == "convergence":
            budget = args.budget if args.budget is not None else payload.get("budget")
            if not isinstance(budget, int):
                raise ValueError("convergence requires integer budget")
            result = summarize_convergence(rows, budget)
        elif args.analysis == "diagnosis":
            result = diagnose_result_bundle(rows, payload.get("audit_records", []))
        else:
            result = summarize_mechanism(rows)
        encoded = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
        if args.output:
            args.output.write_text(encoded + "\n", encoding="utf-8")
        else:
            print(encoded)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
