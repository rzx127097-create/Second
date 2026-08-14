"""Run all formal-experiment readiness gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.readiness import audit_repository_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--resource-report", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    resource = None
    if args.resource_report is not None:
        resource = json.loads(args.resource_report.read_text(encoding="utf-8"))
    report = audit_repository_readiness(args.config_dir, resource_report=resource)
    payload = report.to_dict()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if report.formal_ready or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
