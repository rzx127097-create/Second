"""Deterministic seed-level summaries for paired evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def summarize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        groups[(str(row["method"]), str(row["scale"]), int(row["training_seed"]))].append(row)
    summaries: list[dict[str, Any]] = []
    for (method, scale, seed), rows in sorted(groups.items()):
        reductions = [float(row["reduction_rate"]) for row in rows]
        transfers = [float(row["transferred_l"]) for row in rows]
        summaries.append({
            "method": method, "scale": scale, "training_seed": seed,
            "run_id": str(rows[0]["run_id"]), "config_hash": str(rows[0]["config_hash"]),
            "git_commit": str(rows[0]["git_commit"]),
            "reduction_rate_mean": sum(reductions) / len(reductions),
            "success_rate": sum(bool(row["success"]) for row in rows) / len(rows),
            "transferred_l_mean": sum(transfers) / len(transfers),
            "scenario_count": len(rows),
        })
    return summaries
