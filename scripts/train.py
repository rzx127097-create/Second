"""CLI placeholder for a single immutable training job."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", default="SR-MAPPO", choices=["SR-MAPPO"])
    parser.add_argument("--scale", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.parse_args()
    raise SystemExit("Training runner is configured through problem2.experiments; run only after parameter freeze.")


if __name__ == "__main__":
    main()
