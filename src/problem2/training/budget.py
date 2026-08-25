"""Conservative G5 development-pilot runtime aggregation and budget selection."""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Iterable, Mapping, Sequence

from problem2.experiments.g5_contract import (
    BudgetDecision,
    FROZEN_CANDIDATE_BUDGETS,
    LEARNING_METHODS,
    REPRESENTATIVE_SCALE,
    select_formal_budget,
)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a finite positive number")
    return result


def aggregate_runtime(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, float | int]]]:
    """Aggregate runtime conservatively by scale and learning method.

    The maximum observed elapsed-seconds-per-interaction is retained for each
    method/scale pair.  No row is discarded or averaged across methods.
    """

    maxima: dict[tuple[str, str], list[float]] = defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"runtime row {index} must be a mapping")
        method = row.get("method_id", row.get("method"))
        scale = row.get("scale_id", row.get("scale"))
        if method not in LEARNING_METHODS:
            raise ValueError(f"runtime row {index} has unknown method")
        if not isinstance(scale, str) or not scale:
            raise ValueError(f"runtime row {index} has invalid scale")
        interactions = _positive_int(row.get("interactions"), f"runtime row {index} interactions")
        elapsed = _positive_number(row.get("elapsed_seconds"), f"runtime row {index} elapsed_seconds")
        maxima[(scale, method)].append(elapsed / interactions)
    if not maxima:
        raise ValueError("runtime rows cannot be empty")
    result: dict[str, dict[str, dict[str, float | int]]] = defaultdict(dict)
    for (scale, method), values in sorted(maxima.items()):
        result[scale][method] = {
            "seconds_per_interaction": max(values),
            "observations": len(values),
        }
    return {scale: dict(methods) for scale, methods in result.items()}


def _budget_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    aggregate = aggregate_runtime(rows)
    representative = aggregate.get(REPRESENTATIVE_SCALE, {})
    if set(representative) != set(LEARNING_METHODS):
        raise ValueError("runtime evidence must cover every method at g30x50_d4")
    return [
        {
            "method_id": method,
            "scale_id": REPRESENTATIVE_SCALE,
            "interactions": 1,
            "elapsed_seconds": float(representative[method]["seconds_per_interaction"]),
        }
        for method in LEARNING_METHODS
    ]


def select_pilot_budget(
    rows: Iterable[Mapping[str, Any]],
    candidate_budgets: Sequence[int] = FROZEN_CANDIDATE_BUDGETS,
) -> BudgetDecision:
    """Select the largest feasible budget under the frozen Task-2 rule."""

    return select_formal_budget(_budget_rows(rows), tuple(candidate_budgets))


__all__ = ["aggregate_runtime", "select_pilot_budget"]
