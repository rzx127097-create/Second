from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from _g5_cli import read_only_preflight


def preflight_g6(root=None):
    return read_only_preflight(root, gate="G6") if root is not None else read_only_preflight(gate="G6")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only dynamic G6 entry preflight")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = read_only_preflight(args.root.resolve(), gate="G6")
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("all_pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
