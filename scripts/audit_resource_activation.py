"""Audit resource-demand columns before interpreting mobility effects."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.resource_activation import audit_resource_activation


def _read_audit_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"blank/empty JSONL line at line {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL line {line_number} must be an object")
            rows.append(value)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_resource_activation(_read_audit_rows(args.input)).to_dict()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8",
    )
    os.replace(temporary, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
