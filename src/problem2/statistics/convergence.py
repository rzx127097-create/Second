from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from statistics import fmean, pstdev
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ConvergenceSummary:
    normalized_auc: float
    threshold_interactions: int
    threshold_observed: bool
    restricted_mean_time_to_threshold: float
    final_window_sd: float
    across_seed_checkpoint_dispersion: dict[int, float]
    nonfinite_count: int = 0
    invalid_update_count: int = 0
    clipped_count: int = 0
    regression_count: int = 0
    catastrophic_regression_count: int = 0
    seed_count: int = 0
    checkpoint_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def _number(row: Mapping[str, object], key: str) -> float:
    value = row[key]
    if isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def _flag(row: Mapping[str, object], key: str) -> bool:
    value = row.get(key, False)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def summarize_convergence(
    rows: Iterable[Mapping[str, object]], budget: int, threshold: float = 0.85
) -> ConvergenceSummary:
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("budget must be a positive integer")
    if isinstance(threshold, bool) or not math.isfinite(float(threshold)):
        raise ValueError("threshold must be finite")
    records = list(rows)
    if not records:
        raise ValueError("rows must not be empty")
    grouped: dict[object, dict[int, float]] = {}
    invalid = clipped = regression = catastrophic = nonfinite = 0
    scales: set[object] = set()
    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError("each row must be a mapping")
        if "training_seed" not in row or "interaction_count" not in row or "reduction_rate" not in row:
            raise ValueError("missing convergence key")
        seed = row["training_seed"]
        if isinstance(seed, bool) or not isinstance(seed, (int, str)):
            raise ValueError("training_seed must be an identity")
        count = _number(row, "interaction_count")
        if count != int(count) or count < 0 or count > budget:
            raise ValueError("interaction_count outside budget")
        value = _number(row, "reduction_rate")
        if value < -1.0 or value > 1.0:
            raise ValueError("reduction_rate outside [0,1]")
        if "finite" in row:
            if not isinstance(row["finite"], bool):
                raise ValueError("finite must be boolean")
            if not row["finite"]:
                raise ValueError("finite=false convergence row")
        if "scale" not in row:
            raise ValueError("scale is required")
        scale = row["scale"]
        scales.add(scale)
        bucket = grouped.setdefault(seed, {})
        key = int(count)
        if key in bucket:
            raise ValueError("duplicate convergence cell")
        bucket[key] = value
        if _flag(row, "valid_update") is False and "valid_update" in row:
            invalid += 1
        clipped += int(_flag(row, "clipped"))
        regression += int(_flag(row, "regression"))
    if len(scales) > 1:
        raise ValueError("convergence rows must have one scale")
    grids = {tuple(sorted(values)) for values in grouped.values()}
    if len(grids) != 1:
        raise ValueError("all training seeds must share the checkpoint grid")
    grid = sorted(next(iter(grids)))
    if grid[0] != 0:
        raise ValueError("checkpoint grid must start at zero")
    # A curve is the across-seed mean at each frozen checkpoint.  No values are interpolated.
    means = {x: fmean(group[x] for group in grouped.values()) for x in grid}
    for values in grouped.values():
        previous = None
        for x in grid:
            current = values[x]
            if previous is not None and current < previous:
                regression += 1
                catastrophic += int(previous - current >= 0.10)
            previous = current
    auc = 0.0
    for left, right in zip(grid, grid[1:]):
        auc += (right - left) * (means[left] + means[right]) / 2.0
    # A grid ending before the budget is right-censored; extending the last
    # value would be an unregistered interpolation/extrapolation.
    threshold_hits = [x for x in grid if means[x] >= threshold]
    # A method-level crossing is observed only when every independent seed
    # crosses; otherwise the summary remains right-censored for that seed.
    observed = all(any(values[x] >= threshold for x in grid) for values in grouped.values())
    observed_hits = [min(x for x in grid if values[x] >= threshold) for values in grouped.values() if any(values[x] >= threshold for x in grid)]
    hit = max(observed_hits) if observed and observed_hits else budget
    times = []
    for values in grouped.values():
        hits = [x for x in grid if values[x] >= threshold]
        times.append(hits[0] if hits else budget)
    final_start = 0.8 * budget
    final_values = [values[x] for values in grouped.values() for x in grid if x >= final_start]
    final_sd = pstdev(final_values) if len(final_values) > 1 else 0.0
    dispersion = {x: (pstdev([values[x] for values in grouped.values()]) if len(grouped) > 1 else 0.0) for x in grid}
    return ConvergenceSummary(
        normalized_auc=auc / budget,
        threshold_interactions=hit,
        threshold_observed=observed,
        restricted_mean_time_to_threshold=fmean(times),
        final_window_sd=final_sd,
        across_seed_checkpoint_dispersion=dispersion,
        nonfinite_count=nonfinite,
        invalid_update_count=invalid,
        clipped_count=clipped,
        regression_count=regression,
        catastrophic_regression_count=catastrophic,
        seed_count=len(grouped),
        checkpoint_count=len(grid),
    )
