"""Deterministic seed-level summaries for paired evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any



def _bootstrap_ci(values: list[float], *, seed: int = 0, draws: int = 2000) -> tuple[float | None, float | None, str, int]:
    n = len(values)
    if n < 2:
        return None, None, "n<2; bootstrap interval unavailable", n
    try:
        import numpy as np
    except ImportError:
        # A deterministic analytic fallback still makes the limitation explicit.
        mean = sum(values) / n
        return mean, mean, "numpy unavailable; degenerate interval", n
    rng = np.random.default_rng(seed)
    sample = np.asarray(values, dtype=float)
    means = sample[rng.integers(0, n, size=(draws, n))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), "percentile bootstrap 95%; seed=0; draws=2000", n


def summarize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
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
            "provisional": True,
        })
    return summaries


def paired_differences(records: Iterable[Mapping[str, Any]], reference: str = "sr_mappo_mobile") -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in records:
        by_key[(str(row["scale"]), str(row["scenario_id"]))][str(row["method"])] = row
    result: list[dict[str, Any]] = []
    for (scale, scenario), methods in sorted(by_key.items()):
        ref = methods.get(reference)
        for method, row in sorted(methods.items()):
            if method == reference:
                continue
            entry: dict[str, Any] = {"method": method, "scale": scale, "scenario_id": scenario, "reference_method": reference, "provisional": True}
            if ref is None:
                entry.update({"reduction_difference": None, "pairing_available": False, "pairing_reason": "reference method missing"})
            elif int(ref["training_seed"]) != int(row["training_seed"]):
                entry.update({"reduction_difference": None, "pairing_available": False, "pairing_reason": "training seed mismatch"})
            else:
                entry.update({"reduction_difference": float(row["reduction_rate"]) - float(ref["reduction_rate"]), "pairing_available": True, "pairing_reason": "paired shared scenario"})
            result.append(entry)
    return result
