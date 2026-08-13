"""Nature-style figure primitives; figures consume locked summary rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def plot_metric(rows: Iterable[Mapping[str, Any]], metric: str, output_path: str) -> str:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("plotting requires matplotlib") from exc
    rows = list(rows)
    methods = [str(row.get("method", "")) for row in rows]
    values = [float(row.get(metric, 0.0)) for row in rows]
    plt.rcParams.update({"font.family": "Arial", "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    ax.plot(methods, values, marker="o", linewidth=1.8, color="#2878B5")
    ax.set_ylabel(metric)
    ax.tick_params(axis="x", rotation=30)
    fig.savefig(output_path, dpi=600, facecolor="white")
    plt.close(fig)
    return output_path
