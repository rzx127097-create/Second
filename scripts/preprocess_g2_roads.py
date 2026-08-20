from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from problem2.audit import (  # noqa: E402
    preprocess_all,
    resolve_generator_provenance,
    resolve_output_root,
)
from problem2.config import load_g2_config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the six audited G2 road caches.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    try:
        config = load_g2_config(args.config)
        output_root = resolve_output_root(config, args.output_root)
        provenance = resolve_generator_provenance()
        records = preprocess_all(config, output_root, provenance)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "scale_count": len(records),
                    "scales": [record.scale_id for record in records],
                    "generator_commit": provenance.git_commit,
                    "generator_tree_sha256": provenance.tree_sha256,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(f"G2 road preprocessing failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
