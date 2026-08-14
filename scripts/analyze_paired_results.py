"""Build a hierarchical paired comparison report from validated episode logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.artifacts.statistics import hierarchical_paired_bootstrap
from problem2.artifacts.validate_logs import read_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--method-a", required=True)
    parser.add_argument("--method-b", required=True)
    parser.add_argument("--group-field", default="method")
    parser.add_argument("--metric", default="reduction_rate")
    parser.add_argument("--draws", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--practical-equivalence-margin", type=float)
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.method_a == args.method_b:
        raise ValueError("method-a and method-b must differ")

    rows = read_jsonl(args.input)
    selected = [
        row for row in rows
        if str(row.get(args.group_field, "")) in {args.method_a, args.method_b}
    ]
    present = {str(row.get(args.group_field, "")) for row in selected}
    if present != {args.method_a, args.method_b}:
        raise ValueError("input does not contain both requested methods")
    estimates = hierarchical_paired_bootstrap(
        selected,
        reference=args.method_a,
        metric=args.metric,
        draws=args.draws,
        seed=args.seed,
        confidence_level=args.confidence_level,
        practical_equivalence_margin=args.practical_equivalence_margin,
        confirmatory=not args.exploratory,
        group_field=args.group_field,
    )
    payload = {
        "input_path": str(args.input.resolve()),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "record_count": len(selected),
        "method_a": args.method_a,
        "method_b": args.method_b,
        "metric": args.metric,
        "group_field": args.group_field,
        "difference_direction": "method_b_minus_method_a",
        "analysis_role": "exploratory" if args.exploratory else "confirmatory",
        "estimates": [estimate.to_dict() for estimate in estimates],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
