from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from problem2.audit import (  # noqa: E402
    resolve_generator_provenance,
    resolve_output_root,
    run_g2_audit,
)
from problem2.config import load_g2_config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fail-closed Problem 2 G2 audit.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = load_g2_config(args.config)
        output_root = resolve_output_root(config, args.output_root)
        provenance = resolve_generator_provenance()
        report = run_g2_audit(
            config,
            args.config.resolve(),
            output_root,
            args.report,
            provenance,
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "scale_count": len(report["scales"]),
                    "replay_match": report["cross_process_replay"]["match"],
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(f"G2 deterministic audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
