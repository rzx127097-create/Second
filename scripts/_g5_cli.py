"""Shared dry-run CLI guard; Task 8 never executes experiment rows."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from problem2.evaluation.sealed_lock import SealedAccessError, assert_no_sealed_access, assert_partition_allowed


def run_cli(name: str, *, default_partition: str = "development", blocked_reason: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{name}: G5 dry-run guard only")
    parser.add_argument("--scenario-id", type=int)
    parser.add_argument("--partition", default=default_partition)
    parser.add_argument("--sealed-accessed", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()
    try:
        if args.scenario_id is not None:
            assert_partition_allowed(gate="G5", partition=args.partition, scenario_id=args.scenario_id)
        assert_no_sealed_access(gate="G5", scenario_id=args.scenario_id, partition=args.partition, sealed_accessed=args.sealed_accessed)
    except SealedAccessError as exc:
        print(f"sealed access denied: {exc}", file=sys.stderr)
        return 2
    if blocked_reason is not None:
        print(f"sealed lock unchanged: {blocked_reason}", file=sys.stderr)
        return 2
    print(f"{name}: dry-run only; no jobs executed")
    return 0
