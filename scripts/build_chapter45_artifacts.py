"""Build the locked Chapter 4.5 figure/table/evidence package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.artifacts.chapter45 import build_chapter45_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="+", type=Path, help="validated UTF-8 episode JSONL files")
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--freeze-manifest", type=Path)
    parser.add_argument("--sealed-unlock", type=Path)
    args = parser.parse_args(argv)
    protocol = args.protocol or (args.config_dir / "experiments" / "chapter4_5.yaml")
    try:
        bundle = build_chapter45_artifacts(
            args.input,
            args.output,
            config_dir=args.config_dir,
            protocol_path=protocol,
            allow_partial=args.allow_partial,
            freeze_path=args.freeze_manifest,
            unlock_path=args.sealed_unlock,
        )
    except Exception as exc:  # noqa: BLE001 - preserve CLI diagnostic boundary
        print(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True))
        return 1
    print(json.dumps({
        "status": "completed",
        "paths": {name: str(path) for name, path in bundle.paths.items()},
        "allow_partial": bool(args.allow_partial),
    }, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
