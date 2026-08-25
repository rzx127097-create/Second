"""JSON adapter for the non-sealed G5 paired estimator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from problem2.statistics.paired import hierarchical_paired_bootstrap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze validated paired G5 rows")
    parser.add_argument("--input", type=Path, help="explicit JSON input path; stdin when omitted")
    parser.add_argument("--output", type=Path, help="explicit JSON output path; stdout when omitted")
    parser.add_argument("--metric", required=False, help="metric name (or payload metric)")
    parser.add_argument("--replicates", type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        source = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        payload = json.loads(source)
        if not isinstance(payload, dict) or payload.get("validated", True) is not True:
            raise ValueError("input must be a validated JSON mapping")
        rows = payload.get("rows")
        metric = args.metric or payload.get("metric")
        if not isinstance(rows, list) or not isinstance(metric, str):
            raise ValueError("payload requires rows and metric")
        result = hierarchical_paired_bootstrap(rows, metric, B=args.replicates)
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
