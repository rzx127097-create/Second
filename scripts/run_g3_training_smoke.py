from __future__ import annotations

import argparse
import json
from pathlib import Path

from problem2.experiments.ecology_policy import EcologyMode, resolve_output_root
from problem2.training.train_g3_smoke import run_training_smoke


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the non-sealed G3 training smoke.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--updates", type=int, required=True)
    parser.add_argument(
        "--ecology-mode",
        choices=tuple(mode.value for mode in EcologyMode),
        default=EcologyMode.DYNAMIC.value,
    )
    args = parser.parse_args()
    try:
        output_root = resolve_output_root(
            ROOT,
            "G3",
            args.output_root,
            primary=True,
            partition="development",
            ecology_mode=args.ecology_mode,
        )
    except ValueError as exc:
        parser.error(str(exc))
    result = run_training_smoke(
        args.config,
        output_root,
        seed=args.seed,
        updates=args.updates,
        allow_noncanonical_output_root=True,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
