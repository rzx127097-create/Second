"""CLI entry point for shared-scenario evaluation."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["validation", "sealed_test"], required=True)
    parser.parse_args()
    raise SystemExit("Evaluation requires a frozen checkpoint and scenario manifest.")


if __name__ == "__main__":
    main()
