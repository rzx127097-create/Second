"""Build validated summary artifacts from a JSON episode record file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from problem2.artifacts.summarize import summarize_records
from problem2.artifacts.validate_logs import validate_episode_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    summary = summarize_records(validate_episode_records(rows))
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
