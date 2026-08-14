"""Audit an offline GraphML road source and write its immutable metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.road.graphml import load_graphml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--origin-lon", type=float)
    parser.add_argument("--origin-lat", type=float)
    parser.add_argument("--coordinate-mode", choices=["lonlat", "metric"], default="lonlat")
    args = parser.parse_args(argv)
    try:
        origin = None
        if args.origin_lon is not None or args.origin_lat is not None:
            if args.origin_lon is None or args.origin_lat is None:
                raise ValueError("both --origin-lon and --origin-lat are required")
            origin = (args.origin_lon, args.origin_lat)
        _graph, metadata = load_graphml(
            args.source,
            coordinate_mode=args.coordinate_mode,
            origin_lonlat=origin,
        )
        payload = {
            "name": "road_source",
            "status": "observed",
            "ready": True,
            "issues": [],
            "metadata": metadata,
        }
        code = 0
    except Exception as exc:  # noqa: BLE001 - CLI emits machine-readable diagnostics
        payload = {
            "name": "road_source",
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
