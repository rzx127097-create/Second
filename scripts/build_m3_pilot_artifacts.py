"""Build a traceable validation-only M3 pilot evidence package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.artifacts.m3_pilot import build_m3_pilot_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        bundle = build_m3_pilot_artifacts(
            args.manifest,
            args.readiness,
            args.output,
            config_dir=args.config_dir,
            protocol_path=args.protocol,
        )
    except Exception as exc:  # noqa: BLE001 - preserve machine-readable CLI diagnostics
        print(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True, sort_keys=True))
        return 1
    print(json.dumps({
        "status": "completed",
        "paths": {name: str(path) for name, path in bundle.paths.items()},
    }, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
