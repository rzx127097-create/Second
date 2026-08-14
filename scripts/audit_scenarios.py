"""Audit scenario split isolation and physical-scale consistency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.readiness import audit_scenario_registry


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--scales", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit_scenario_registry(
            _load(args.scenarios), _load(args.scales), _load(args.matrix)
        )
        payload = report.to_dict()
        code = 0 if report.ready or not args.strict else 2
    except Exception as exc:  # noqa: BLE001 - preserve machine-readable audit failure
        payload = {
            "name": "scenarios",
            "status": "invalid",
            "ready": False,
            "issues": [{"code": type(exc).__name__, "message": str(exc)}],
        }
        code = 2
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
