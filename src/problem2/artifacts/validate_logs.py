"""Validate event-complete episode records before aggregation."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "run_id", "method", "scale", "training_seed", "scenario_id", "config_hash", "git_commit",
    "reduction_rate", "success", "transferred_l",
}


def validate_episode_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(record) for record in records]
    if not rows:
        raise ValueError("episode records are empty")
    seen: set[str] = set()
    seen_observations: set[tuple[str, str, int, str]] = set()
    for row in rows:
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"missing episode fields: {sorted(missing)}")
        run_id = str(row["run_id"])
        if not run_id:
            raise ValueError("run_id must be non-empty")
        if run_id in seen:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen.add(run_id)
        try:
            seed = int(row["training_seed"])
            reduction = float(row["reduction_rate"])
            transferred = float(row["transferred_l"])
        except (TypeError, ValueError) as exc:
            raise ValueError("training_seed and numeric metrics must be valid numbers") from exc
        if not math.isfinite(reduction) or not math.isfinite(transferred):
            raise ValueError("numeric metrics must be finite")
        if not 0.0 <= reduction <= 1.0:
            raise ValueError("reduction_rate must lie in [0, 1]")
        if transferred < 0:
            raise ValueError("transferred_l must be non-negative")
        observation = (str(row["method"]), str(row["scale"]), seed, str(row["scenario_id"]))
        if observation in seen_observations:
            raise ValueError("duplicate method/scale/training_seed/scenario_id")
        seen_observations.add(observation)
        row["training_seed"] = seed
        row["reduction_rate"] = reduction
        row["transferred_l"] = transferred
    return rows


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one UTF-8 JSON object per non-empty input line."""
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}") from exc
            if not isinstance(value, Mapping):
                raise ValueError(f"JSONL line {line_number} must be an object")
            if "split" not in value:
                raise ValueError("missing episode fields: ['split']")
            records.append(dict(value))
    return validate_episode_records(records)
