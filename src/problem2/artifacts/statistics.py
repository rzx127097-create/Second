"""Hierarchical paired inference for shared seed/scenario evaluations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import product
from math import isfinite
from typing import Iterable, Mapping

import numpy as np


@dataclass(frozen=True)
class PairedEstimate:
    method: str
    reference_method: str
    group_field: str
    scale: str
    metric: str
    difference_direction: str
    observed_difference: float
    ci_low: float
    ci_high: float
    confidence_level: float
    bootstrap_draws: int
    bootstrap_seed: int
    n_training_seeds: int
    scenarios_per_seed: dict[int, int]
    pairing_complete: bool
    analysis_role: str
    raw_p_value: float
    holm_adjusted_p_value: float
    standardized_seed_effect: float | None
    effect_measure: str
    practical_equivalence_margin: float | None
    practical_interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Return Holm step-down adjusted probabilities in original order."""

    values = [float(value) for value in p_values]
    if any(not isfinite(value) or not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("p values must be finite and lie in [0, 1]")
    if not values:
        return []
    ordered = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    adjusted = [0.0] * len(values)
    running = 0.0
    total = len(values)
    for rank, (original_index, value) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * value))
        adjusted[original_index] = running
    return adjusted


def _metric_value(row: Mapping[str, object], metric: str) -> float:
    if metric not in row:
        raise ValueError(f"paired metric is missing: {metric}")
    raw = row[metric]
    if metric == "success":
        if isinstance(raw, bool):
            return float(raw)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw in (0, 1):
            return float(raw)
        raise ValueError("success must be boolean or 0/1")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"paired metric must be numeric: {metric}") from exc
    if not isfinite(value):
        raise ValueError(f"paired metric must be finite: {metric}")
    return value


def _sign_flip_p_value(seed_differences: list[float], *, seed: int) -> float:
    values = np.asarray(seed_differences, dtype=float)
    observed = abs(float(values.mean()))
    count = len(values)
    if count <= 20:
        extreme = 0
        total = 2**count
        for signs in product((-1.0, 1.0), repeat=count):
            permuted = abs(float(np.mean(values * np.asarray(signs, dtype=float))))
            extreme += int(permuted >= observed - 1e-15)
        return extreme / total
    rng = np.random.default_rng(seed)
    draws = 100_000
    signs = rng.choice((-1.0, 1.0), size=(draws, count))
    permuted = np.abs((signs * values).mean(axis=1))
    return float((np.count_nonzero(permuted >= observed - 1e-15) + 1) / (draws + 1))


def _practical_interpretation(
    low: float, high: float, margin: float | None
) -> str:
    if margin is None:
        return "not_predefined"
    if low >= margin:
        return "comparison_better"
    if high <= -margin:
        return "reference_better"
    if low >= -margin and high <= margin:
        return "practically_equivalent"
    return "inconclusive"


def hierarchical_paired_bootstrap(
    records: Iterable[Mapping[str, object]],
    reference: str,
    metric: str,
    draws: int,
    seed: int,
    *,
    confidence_level: float = 0.95,
    practical_equivalence_margin: float | None = None,
    confirmatory: bool = True,
    group_field: str = "method",
) -> list[PairedEstimate]:
    """Compare every method with ``reference`` using two-level resampling.

    The observed estimand is the equally weighted mean of training-seed means.
    Scenario observations are paired and resampled only within their originating
    seed, so many scenarios from one fitted policy cannot inflate replication.
    """

    if int(draws) < 1:
        raise ValueError("bootstrap draws must be positive")
    if not 0.0 < float(confidence_level) < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    if practical_equivalence_margin is not None:
        practical_equivalence_margin = float(practical_equivalence_margin)
        if not isfinite(practical_equivalence_margin) or practical_equivalence_margin < 0:
            raise ValueError("practical_equivalence_margin must be finite and non-negative")
    rows = [dict(record) for record in records]
    if not rows:
        raise ValueError("paired records are empty")
    group_field = str(group_field).strip()
    if not group_field:
        raise ValueError("group_field must be non-empty")

    observations: dict[tuple[str, str, int, str], float] = {}
    methods_by_scale: dict[str, set[str]] = {}
    for row in rows:
        method = str(row.get(group_field, "")).strip()
        scale = str(row.get("scale", "")).strip()
        scenario = str(row.get("scenario_id", "")).strip()
        if not method or not scale or not scenario:
            raise ValueError(
                f"paired records require {group_field}, scale and scenario_id"
            )
        try:
            training_seed = int(row["training_seed"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("paired records require an integer training_seed") from exc
        if isinstance(row.get("training_seed"), bool) or float(row["training_seed"]) != training_seed:
            raise ValueError("paired records require an integer training_seed")
        key = (method, scale, training_seed, scenario)
        if key in observations:
            raise ValueError(f"duplicate paired observation: {key}")
        observations[key] = _metric_value(row, metric)
        methods_by_scale.setdefault(scale, set()).add(method)

    estimates: list[PairedEstimate] = []
    rng = np.random.default_rng(int(seed))
    alpha = (1.0 - float(confidence_level)) / 2.0
    for scale in sorted(methods_by_scale):
        if reference not in methods_by_scale[scale]:
            raise ValueError(f"reference method is missing at scale {scale}: {reference}")
        reference_pairs = {
            (training_seed, scenario): value
            for (method, row_scale, training_seed, scenario), value in observations.items()
            if method == reference and row_scale == scale
        }
        for method in sorted(methods_by_scale[scale] - {reference}):
            comparison_pairs = {
                (training_seed, scenario): value
                for (row_method, row_scale, training_seed, scenario), value in observations.items()
                if row_method == method and row_scale == scale
            }
            pairing_complete = comparison_pairs.keys() == reference_pairs.keys()
            if confirmatory and not pairing_complete:
                missing_comparison = sorted(reference_pairs.keys() - comparison_pairs.keys())
                missing_reference = sorted(comparison_pairs.keys() - reference_pairs.keys())
                raise ValueError(
                    "incomplete confirmatory pairs for "
                    f"{method} vs {reference} at {scale}; "
                    f"missing comparison={missing_comparison}, missing reference={missing_reference}"
                )
            paired_keys = sorted(reference_pairs.keys() & comparison_pairs.keys())
            if not paired_keys:
                raise ValueError(f"no shared pairs for {method} vs {reference} at {scale}")
            by_seed: dict[int, list[float]] = {}
            for training_seed, scenario in paired_keys:
                by_seed.setdefault(training_seed, []).append(
                    comparison_pairs[(training_seed, scenario)]
                    - reference_pairs[(training_seed, scenario)]
                )
            ordered_seeds = sorted(by_seed)
            seed_means = [float(np.mean(by_seed[training_seed])) for training_seed in ordered_seeds]
            observed = float(np.mean(seed_means))

            bootstrap = np.empty(int(draws), dtype=float)
            for draw in range(int(draws)):
                selected = rng.integers(0, len(ordered_seeds), size=len(ordered_seeds))
                resampled_seed_means = []
                for selected_index in selected:
                    values = np.asarray(by_seed[ordered_seeds[int(selected_index)]], dtype=float)
                    scenario_sample = values[rng.integers(0, len(values), size=len(values))]
                    resampled_seed_means.append(float(scenario_sample.mean()))
                bootstrap[draw] = float(np.mean(resampled_seed_means))
            low, high = np.quantile(bootstrap, (alpha, 1.0 - alpha))
            if len(seed_means) >= 2:
                standard_deviation = float(np.std(seed_means, ddof=1))
                standardized = observed / standard_deviation if standard_deviation > 1e-15 else None
            else:
                standardized = None
            effect_measure = (
                "paired_risk_difference" if metric == "success"
                else "standardized_training_seed_mean_difference"
            )
            estimates.append(PairedEstimate(
                method=method,
                reference_method=reference,
                group_field=group_field,
                scale=scale,
                metric=metric,
                difference_direction="comparison_minus_reference",
                observed_difference=observed,
                ci_low=float(low),
                ci_high=float(high),
                confidence_level=float(confidence_level),
                bootstrap_draws=int(draws),
                bootstrap_seed=int(seed),
                n_training_seeds=len(ordered_seeds),
                scenarios_per_seed={value: len(by_seed[value]) for value in ordered_seeds},
                pairing_complete=pairing_complete,
                analysis_role="confirmatory" if confirmatory else "exploratory",
                raw_p_value=_sign_flip_p_value(seed_means, seed=int(seed)),
                holm_adjusted_p_value=0.0,
                standardized_seed_effect=standardized,
                effect_measure=effect_measure,
                practical_equivalence_margin=practical_equivalence_margin,
                practical_interpretation=_practical_interpretation(
                    float(low), float(high), practical_equivalence_margin,
                ),
            ))

    adjusted = holm_adjust(estimate.raw_p_value for estimate in estimates)
    return [
        replace(estimate, holm_adjusted_p_value=adjusted[index])
        for index, estimate in enumerate(estimates)
    ]


__all__ = ["PairedEstimate", "hierarchical_paired_bootstrap", "holm_adjust"]
