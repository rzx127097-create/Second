from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
from statistics import fmean
from typing import Iterable, Mapping

SUPPORTED_METRICS = {
    "reduction_rate", "success_at_0_85", "success", "rendezvous_distance_m",
    "vehicle_service_travel_m", "waiting_steps", "pesticide_disabled_steps",
    "effective_spray_steps", "return_steps", "decision_runtime_s",
}


@dataclass(frozen=True)
class PairedEstimate:
    metric: str
    observed_difference: float
    interval: tuple[float, float]
    p_value: float
    per_seed_summary: dict[object, float]
    bootstrap_replicates: int
    rng_seed: int

    @property
    def ci95(self) -> tuple[float, float]:
        return self.interval

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _pairs(rows: Iterable[Mapping[str, object]], metric: str) -> dict[object, dict[object, float]]:
    records = list(rows)
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"unsupported metric: {metric}")
    if not records:
        raise ValueError("rows must not be empty")
    grouped: dict[tuple[object, object, object, object], dict[str, float]] = {}
    explicit: dict[tuple[object, object, object, object], tuple[float, float]] = {}
    comparison_keys: set[tuple[object, object]] = set()
    declared_orders: set[tuple[str, str]] = set()
    for row in records:
        if not isinstance(row, Mapping) or "training_seed" not in row or "scenario_id" not in row:
            raise ValueError("pairing keys are required")
        key = (row["training_seed"], row["scenario_id"], row.get("condition_id", ""), row.get("scale", ""))
        comparison_keys.add((key[2], key[3]))
        if "value_a" in row or "value_b" in row:
            if "value_a" not in row or "value_b" not in row or key in explicit:
                raise ValueError("duplicate or incomplete pair")
            explicit[key] = (_finite(row["value_a"], "value_a"), _finite(row["value_b"], "value_b"))
        else:
            method = row.get("method")
            order = row.get("method_order")
            if not isinstance(order, (list, tuple)) or len(order) != 2 or any(not isinstance(item, str) or not item for item in order):
                raise ValueError("method order must be explicitly declared")
            declared_orders.add((order[0], order[1]))
            if method is None:
                method = row.get("arm", row.get("condition", "value"))
            if not isinstance(method, str) or method not in order:
                raise ValueError("method is outside declared method order")
            value = row.get("value", row.get(metric))
            if value is None:
                raise ValueError("pair value is missing")
            bucket = grouped.setdefault(key, {})
            method = str(method)
            if method in bucket:
                raise ValueError("duplicate pairing cell")
            bucket[method] = _finite(value, "value")
    if len(comparison_keys) > 1:
        raise ValueError("rows contain multiple comparison conditions or scales")
    if len(declared_orders) > 1:
        raise ValueError("method order drift")
    if explicit:
        out: dict[object, dict[object, float]] = {}
        for (seed, scenario, _condition, _scale), (a, b) in explicit.items():
            out.setdefault(seed, {})[scenario] = a - b
        scenario_sets = {tuple(sorted(scenarios)) for scenarios in out.values()}
        if len(scenario_sets) != 1:
            raise ValueError("training seeds must share scenarios")
        return out
    out: dict[object, dict[object, float]] = {}
    for (seed, scenario, _condition, _scale), methods in grouped.items():
        if len(methods) != 2:
            raise ValueError("each seed/scenario must contain exactly two paired methods")
        names = next(iter(declared_orders))
        if set(methods) != set(names):
            raise ValueError("declared method order does not match paired methods")
        out.setdefault(seed, {})[scenario] = methods[names[0]] - methods[names[1]]
    if len(out) < 1 or any(not scenarios for scenarios in out.values() for _ in [0]):
        raise ValueError("no complete pairs")
    scenario_sets = {tuple(sorted(scenarios)) for scenarios in out.values()}
    if len(scenario_sets) != 1:
        raise ValueError("training seeds must share scenarios")
    return out


def _percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    return values[low] + (values[high] - values[low]) * (pos - low)


def hierarchical_paired_bootstrap(rows: Iterable[Mapping[str, object]], metric: str, B: int = 10000, seed: int = 20260822) -> PairedEstimate:
    if isinstance(B, bool) or not isinstance(B, int) or B <= 0:
        raise ValueError("B must be a positive integer")
    pairs = _pairs(rows, metric)
    seeds = sorted(pairs, key=str)
    scenarios = sorted(next(iter(pairs.values())), key=str)
    observed_values = [pairs[s][c] for s in seeds for c in scenarios]
    observed = fmean(observed_values)
    per_seed = {s: fmean(pairs[s].values()) for s in seeds}
    rng = random.Random(seed)
    reps: list[float] = []
    for _ in range(B):
        sampled_seeds = [rng.choice(seeds) for _ in seeds]
        values = []
        for selected in sampled_seeds:
            values.extend(pairs[selected][rng.choice(scenarios)] for _ in scenarios)
        reps.append(fmean(values))
    interval = (_percentile(reps, 0.025), _percentile(reps, 0.975))
    extreme = sum(abs(value) >= abs(observed) for value in reps)
    p_value = (extreme + 1) / (B + 1)
    return PairedEstimate(metric, observed, interval, p_value, per_seed, B, seed)
