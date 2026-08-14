"""Deterministic seed-level summaries for paired evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import hashlib
from typing import Any

import numpy as np

from .statistics import hierarchical_paired_bootstrap



def _bootstrap_ci(values: list[float], *, seed: int = 0, draws: int = 2000) -> tuple[float | None, float | None, str, int]:
    n = len(values)
    if n < 2:
        return None, None, "n<2; bootstrap interval unavailable", n
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy is required for deterministic bootstrap confidence intervals") from exc
    rng = np.random.default_rng(seed)
    sample = np.asarray(values, dtype=float)
    means = sample[rng.integers(0, n, size=(draws, n))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), "percentile bootstrap 95%; seed=0; draws=2000", n


def summarize_records(records: Iterable[Mapping[str, Any]], *, strict: bool = False) -> list[dict[str, Any]]:
    records = [dict(record) for record in records]
    provenance: dict[tuple[str, str], tuple[str, str, str, bool | None]] = {}
    for row in records:
        key = (str(row["method"]), str(row["scale"]))
        identity = (str(row.get("config_hash", "")), str(row.get("git_commit", "")), str(row.get("split", "")), row.get("provisional"))
        if strict and key in provenance and identity != provenance[key]:
            raise ValueError(f"mixed provenance for method/scale: {key}")
        provenance.setdefault(key, identity)
    groups: dict[tuple[str, str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        groups[(str(row["method"]), str(row["scale"]), int(row["training_seed"]))].append(row)
    summaries: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for (method, scale, seed), rows in sorted(groups.items()):
        reductions = [float(row["reduction_rate"]) for row in rows]
        transfers = [float(row["transferred_l"]) for row in rows]
        seed_summaries.append({
            "method": method, "scale": scale, "training_seed": seed,
            "run_id": str(rows[0]["run_id"]), "config_hash": str(rows[0]["config_hash"]),
            "git_commit": str(rows[0]["git_commit"]),
            "split": str(rows[0].get("split", "")),
            "provisional": rows[0].get("provisional"),
            "reduction_rate_mean": sum(reductions) / len(reductions),
            "success_rate": sum(bool(row["success"]) for row in rows) / len(rows),
            "transferred_l_mean": sum(transfers) / len(transfers),
            "n_scenarios": len(rows), "scenario_count": len(rows), "reduction_rate_seed_mean": sum(reductions) / len(reductions),
        })
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in seed_summaries:
        grouped[(row["method"], row["scale"])].append(row)
    summaries: list[dict[str, Any]] = []
    for (method, scale), seed_rows in sorted(grouped.items()):
        reduction_values = [float(row["reduction_rate_seed_mean"]) for row in seed_rows]
        success_values = [float(row["success_rate"]) for row in seed_rows]
        transfer_values = [float(row["transferred_l_mean"]) for row in seed_rows]
        low, high, reason, n = _bootstrap_ci(reduction_values)
        first = seed_rows[0]
        summaries.append({
            "method": method,
            "scale": scale,
            "run_id": first["run_id"],
            "config_hash": first["config_hash"],
            "git_commit": first["git_commit"],
            "split": first.get("split", ""),
            "training_seeds": [row["training_seed"] for row in seed_rows],
            "seed_level_mean": sum(reduction_values) / len(reduction_values),
            "reduction_rate_mean": sum(reduction_values) / len(reduction_values),
            "reduction_rate_mean_ci_low": low,
            "reduction_rate_mean_ci_high": high,
            "ci_n": n,
            "interval_reason": reason,
            "success_rate": sum(success_values) / len(success_values),
            "transferred_l_mean": sum(transfer_values) / len(transfer_values),
            "n_seeds": len(seed_rows),
            "n_scenarios": sum(int(row["n_scenarios"]) for row in seed_rows),
            "seed_level": seed_rows,
            "provisional": first.get("provisional", True),
        })
    return summaries


def paired_differences(records: Iterable[Mapping[str, Any]], reference: str = "sr_mappo_mobile") -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, int], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in records:
        by_key[(str(row["scale"]), str(row["scenario_id"]), int(row["training_seed"]))][str(row["method"])] = row
    result: list[dict[str, Any]] = []
    grouped_diffs: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (scale, scenario, training_seed), methods in sorted(by_key.items()):
        ref = methods.get(reference)
        for method, row in sorted(methods.items()):
            if method == reference:
                continue
            entry: dict[str, Any] = {"method": method, "scale": scale, "scenario_id": scenario, "training_seed": training_seed, "reference_method": reference, "provisional": row.get("provisional", True)}
            if ref is None:
                entry.update({"reduction_difference": None, "pairing_available": False, "pairing_reason": "reference method missing"})
            else:
                difference = float(row["reduction_rate"]) - float(ref["reduction_rate"])
                grouped_diffs[(method, scale)].append(difference)
                entry.update({"reduction_difference": difference, "pairing_available": True, "pairing_reason": "paired shared scenario"})
            result.append(entry)
    intervals = {
        key: _bootstrap_ci(values, seed=17)
        for key, values in grouped_diffs.items()
    }
    for entry in result:
        values = intervals.get((entry["method"], entry["scale"]))
        if values is None:
            entry.update({"paired_difference_mean": None, "paired_difference_ci_low": None, "paired_difference_ci_high": None, "paired_ci_n": 0, "paired_interval_reason": "reference method missing"})
        else:
            low, high, reason, n = values
            diffs = grouped_diffs[(entry["method"], entry["scale"])]
            entry.update({"paired_difference_mean": sum(diffs) / len(diffs), "paired_difference_ci_low": low, "paired_difference_ci_high": high, "paired_ci_n": n, "paired_interval_reason": reason})
    return result


def hierarchical_paired_summary(
    records: Iterable[Mapping[str, Any]],
    *,
    reference: str = "sr_mappo_mobile",
    metric: str = "reduction_rate",
    draws: int = 5000,
    seed: int = 0,
    confidence_level: float = 0.95,
    practical_equivalence_margin: float | None = None,
    confirmatory: bool = True,
    group_field: str = "method",
) -> list[dict[str, object]]:
    """Return serialization-ready hierarchical paired estimates."""

    return [
        estimate.to_dict()
        for estimate in hierarchical_paired_bootstrap(
            records,
            reference=reference,
            metric=metric,
            draws=draws,
            seed=seed,
            confidence_level=confidence_level,
            practical_equivalence_margin=practical_equivalence_margin,
            confirmatory=confirmatory,
            group_field=group_field,
        )
    ]


def summarize_metric_groups(
    records: Iterable[Mapping[str, Any]],
    *,
    group_fields: tuple[str, ...],
    metrics: tuple[str, ...],
    draws: int = 2000,
    seed: int = 0,
    confidence_level: float = 0.95,
) -> list[dict[str, object]]:
    """Summarize scenarios within fitted-policy seed before seeds themselves."""

    if int(draws) < 1:
        raise ValueError("summary bootstrap draws must be positive")
    if not 0.0 < float(confidence_level) < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    rows = [dict(record) for record in records]
    if not rows:
        return []
    grouped_seed: dict[tuple[object, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        missing = [field for field in (*group_fields, "training_seed", "scenario_id", *metrics) if field not in row]
        if missing:
            raise ValueError(f"metric summary fields are missing: {sorted(set(missing))}")
        key = tuple(row[field] for field in group_fields) + (int(row["training_seed"]),)
        grouped_seed[key].append(row)

    seed_rows: list[dict[str, object]] = []
    for key, group in sorted(grouped_seed.items(), key=lambda item: tuple(map(str, item[0]))):
        result = {field: key[index] for index, field in enumerate(group_fields)}
        result["training_seed"] = int(key[-1])
        result["n_scenarios"] = len(group)
        result["scenario_ids"] = sorted(str(row["scenario_id"]) for row in group)
        for metric in metrics:
            values = [float(bool(row[metric])) if metric == "success" else float(row[metric]) for row in group]
            if any(not np.isfinite(value) for value in values):
                raise ValueError(f"metric summary contains non-finite {metric}")
            result[f"{metric}_seed_mean"] = sum(values) / len(values)
        seed_rows.append(result)

    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in seed_rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    alpha = (1.0 - float(confidence_level)) / 2.0
    summaries: list[dict[str, object]] = []
    for key, group in sorted(grouped.items(), key=lambda item: tuple(map(str, item[0]))):
        result = {field: key[index] for index, field in enumerate(group_fields)}
        stable_key = "|".join(map(str, key)).encode("utf-8")
        group_seed = int.from_bytes(hashlib.sha256(stable_key).digest()[:4], "big")
        rng = np.random.default_rng(int(seed) ^ group_seed)
        result["training_seeds"] = sorted(int(row["training_seed"]) for row in group)
        result["n_training_seeds"] = len(group)
        result["n_scenarios"] = sum(int(row["n_scenarios"]) for row in group)
        result["n_unique_scenarios"] = len({
            scenario for row in group for scenario in row["scenario_ids"]
        })
        for metric in metrics:
            values = np.asarray([float(row[f"{metric}_seed_mean"]) for row in group], dtype=float)
            result[f"{metric}_mean"] = float(values.mean())
            if len(values) < 2:
                low = high = None
            else:
                sampled = values[rng.integers(0, len(values), size=(int(draws), len(values)))]
                means = sampled.mean(axis=1)
                low, high = (float(value) for value in np.quantile(means, (alpha, 1.0 - alpha)))
            result[f"{metric}_ci_low"] = low
            result[f"{metric}_ci_high"] = high
        summaries.append(result)
    return summaries
