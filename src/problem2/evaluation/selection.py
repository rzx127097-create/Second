"""Frozen validation-panel checkpoint selection."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


VALIDATION_SCENARIOS = tuple(range(20000, 20050))
SELECTION_ORDER = [
    "mean_validation_reduction_rate",
    "higher_success_probability",
    "earlier_interaction_count",
    "lexicographically_smaller_checkpoint_hash",
]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _finite_rate(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be finite")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return result


def select_frozen_checkpoint(
    rows: Iterable[Mapping[str, Any]], *, expected_scenarios: Iterable[int]
) -> dict[str, Any]:
    """Select a checkpoint from complete, validation-only candidate rows.

    The returned record retains every validated input row so the selection can
    be audited without reconstructing the candidate population.
    """

    expected = tuple(expected_scenarios)
    if expected != VALIDATION_SCENARIOS:
        raise ValueError("checkpoint selection requires validation scenarios 20000-20049")

    candidate_rows: list[dict[str, Any]] = []
    by_checkpoint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    identity_values: dict[str, dict[str, object]] = defaultdict(dict)
    for index, source in enumerate(rows):
        if not isinstance(source, Mapping):
            raise ValueError(f"validation row {index} must be a mapping")
        row = dict(source)
        checkpoint_hash = row.get("checkpoint_hash")
        if not isinstance(checkpoint_hash, str) or _SHA256.fullmatch(checkpoint_hash) is None:
            raise ValueError("validation row checkpoint hash is invalid")
        scenario_id = row.get("scenario_id")
        if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
            raise ValueError("validation row scenario ID is invalid")
        if scenario_id not in expected:
            if 30000 <= scenario_id <= 30099:
                raise ValueError("sealed scenario is not allowed in checkpoint selection")
            raise ValueError("validation row scenario ID is outside the frozen panel")
        key = (checkpoint_hash, scenario_id)
        if key in seen:
            raise ValueError("duplicate validation row prevents checkpoint selection")
        seen.add(key)
        _finite_rate(row.get("reduction_rate"), "reduction_rate")
        success = row.get("success_at_0_85")
        if type(success) is not bool:
            raise ValueError("success_at_0_85 must be boolean")
        interaction_count = row.get("interaction_count")
        if isinstance(interaction_count, bool) or not isinstance(interaction_count, int) or interaction_count <= 0:
            raise ValueError("interaction_count must be a positive integer")
        for field in (
            "canonical_training_identity",
            "method",
            "condition_id",
            "scale",
            "training_seed",
            "config_hash",
            "evaluator_hash",
            "scenario_panel_hash",
        ):
            if field in row:
                prior = identity_values[checkpoint_hash].get(field)
                if prior is not None and prior != row[field]:
                    raise ValueError("mixed validation identity prevents checkpoint selection")
                identity_values[checkpoint_hash][field] = row[field]
        candidate_rows.append(row)
        by_checkpoint[checkpoint_hash].append(row)

    if not by_checkpoint:
        raise ValueError("checkpoint selection rows are empty")
    expected_set = set(expected)
    summaries: list[dict[str, Any]] = []
    for checkpoint_hash, group in by_checkpoint.items():
        observed = [int(row["scenario_id"]) for row in group]
        if len(group) != len(expected) or set(observed) != expected_set:
            raise ValueError(f"validation row coverage is incomplete for checkpoint {checkpoint_hash}")
        interactions = {int(row["interaction_count"]) for row in group}
        if len(interactions) != 1:
            raise ValueError("checkpoint interaction count is inconsistent")
        mean_reduction = sum(float(row["reduction_rate"]) for row in group) / len(group)
        success_probability = sum(bool(row["success_at_0_85"]) for row in group) / len(group)
        summaries.append(
            {
                "checkpoint_hash": checkpoint_hash,
                "mean_validation_reduction_rate": mean_reduction,
                "success_probability": success_probability,
                "interaction_count": next(iter(interactions)),
            }
        )

    selected = min(
        summaries,
        key=lambda item: (
            -item["mean_validation_reduction_rate"],
            -item["success_probability"],
            item["interaction_count"],
            item["checkpoint_hash"],
        ),
    )
    return {
        **selected,
        "selection_order": list(SELECTION_ORDER),
        "candidate_rows": candidate_rows,
    }


__all__ = ["SELECTION_ORDER", "VALIDATION_SCENARIOS", "select_frozen_checkpoint"]
