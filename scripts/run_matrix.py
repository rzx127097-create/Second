"""Enumerate immutable formal jobs without executing them implicitly."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True)
    parser.parse_args()
    raise SystemExit("Matrix execution is gated until engineering parameters are verified.")


if __name__ == "__main__":
    main()
