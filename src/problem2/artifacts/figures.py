"""Nature-style figure primitives; figures consume locked summary rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def plot_metric(rows: Iterable[Mapping[str, Any]], metric: str, output_path: str) -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("plotting requires matplotlib") from exc
    rows = list(rows)
    methods = [str(row.get("method", "")) for row in rows]
    if any(metric not in row for row in rows):
        raise ValueError(f"missing metric: {metric}")
    values = [float(row[metric]) for row in rows]
    low = [row.get(f"{metric}_ci_low") for row in rows]
    high = [row.get(f"{metric}_ci_high") for row in rows]
    plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    yerr = None
    if all(item is not None for item in low + high):
        yerr = [[value - float(item) for value, item in zip(values, low)], [float(item) - value for value, item in zip(values, high)]]
    ax.errorbar(methods, values, yerr=yerr, fmt="o", linewidth=1.2, color="#2878B5", ecolor="#6B7280", capsize=3)
    ax.set_ylabel(f"{metric} (mean; 95% CI)")
    ax.set_xlabel("method")
    ax.tick_params(axis="x", rotation=30)
    fig.savefig(output_path, dpi=600, facecolor="white")
    plt.close(fig)
    return output_path
