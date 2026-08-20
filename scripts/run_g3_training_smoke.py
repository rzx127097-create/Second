from __future__ import annotations

import argparse
import json
from pathlib import Path

from problem2.training.train_g3_smoke import run_training_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the non-sealed G3 training smoke.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--updates", type=int, required=True)
    args = parser.parse_args()
    result = run_training_smoke(
        args.config,
        args.output_root,
        seed=args.seed,
        updates=args.updates,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
