"""Build traceable artifacts from UTF-8 JSONL episode records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from problem2.artifacts import build_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="UTF-8 JSONL episode records")
    parser.add_argument("--output", type=Path, required=True, help="artifact output directory")
    parser.add_argument("--manifest", type=Path, help="evidence manifest path")
    args = parser.parse_args(argv)
    manifest = args.manifest or (args.output / "evidence_manifest.json")
    try:
        bundle = build_artifacts(args.input, args.output, manifest=manifest)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"paths": {name: str(path) for name, path in bundle.paths.items()}}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
