"""Validate event-complete episode records before aggregation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
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
    for row in rows:
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"missing episode fields: {sorted(missing)}")
        run_id = str(row["run_id"])
        if run_id in seen:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen.add(run_id)
        if not 0.0 <= float(row["reduction_rate"]) <= 1.0:
            raise ValueError("reduction_rate must lie in [0, 1]")
        if float(row["transferred_l"]) < 0:
            raise ValueError("transferred_l must be non-negative")
    return rows
