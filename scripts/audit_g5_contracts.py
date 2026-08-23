"""Fail-closed summary audit for the frozen G5 experiment contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.g5_contract import (  # noqa: E402
    G5ContractError,
    load_g5_contract,
)


def _partition_summary(values: Sequence[int]) -> list[int]:
    return [values[0], values[-1], len(values)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    try:
        contract = load_g5_contract(args.root)
    except (G5ContractError, OSError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, sort_keys=True))
        return 1

    report = {
        "status": "pass",
        "methods": list(contract.methods),
        "conditions": list(contract.conditions),
        "partitions": {
            name: _partition_summary(values)
            for name, values in contract.partitions.items()
        },
        "fairness": dict(contract.fairness),
        "validation_accessed": contract.validation_accessed,
        "sealed_accessed": contract.sealed_accessed,
        "actual_unlock_count": 0,
        "contract_hashes": dict(contract.file_hashes),
    }
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
