"""Freeze the canonical controlled-simulation M3 pilot selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from problem2.experiments.m3_pilot import build_m3_manifest, write_m3_manifest
from problem2.experiments.orchestrator import Chapter45Orchestrator


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--resource-report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        orchestrator = Chapter45Orchestrator(
            args.config_dir,
            args.output_root,
            protocol_path=args.protocol,
        )
        manifest = build_m3_manifest(
            orchestrator,
            resource_report_path=args.resource_report,
        )
        path, reused = write_m3_manifest(args.manifest, manifest)
        _emit({
            "status": "completed",
            "manifest": str(path.resolve()),
            "semantic_sha256": manifest["semantic_sha256"],
            "job_count": manifest["counts"]["jobs"],
            "evaluation_count": manifest["counts"]["evaluations"],
            "reused": reused,
        })
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI preserves exact diagnostics
        _emit({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
