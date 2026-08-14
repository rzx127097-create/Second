"""Nature-style figure primitives; figures consume locked summary rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import os
from pathlib import Path
import re
from typing import Any


METHOD_COLORS = {
    "sr_mappo_mobile": "#0F4D92",
    "sr_mappo_fixed": "#767676",
    "sr_mappo_astar": "#42949E",
    "mappo_mobile": "#B64342",
    "sr_mappo_two_stage": "#9A4D8E",
}

METHOD_LABELS = {
    "sr_mappo_mobile": "SR-MAPPO (mobile)",
    "sr_mappo_fixed": "SR-MAPPO (fixed)",
    "sr_mappo_astar": "SR-MAPPO + rolling A*",
    "mappo_mobile": "MAPPO (mobile)",
    "sr_mappo_two_stage": "SR-MAPPO (two-stage)",
}

CONDITION_LABELS = {
    "finite_no_support": "No support",
    "matched_fixed": "Matched fixed",
    "sr_mappo_mobile": "SR-MAPPO mobile",
    "rolling_astar_mobile": "Rolling A* mobile",
    "teleport_diagnostic": "Teleport diagnostic",
    "unlimited_supply": "Unlimited supply",
    "full_sr_mappo": "Full SR-MAPPO",
    "no_endurance_prediction": "No endurance prediction",
    "no_air_ground_observation": "No air-ground observation",
    "no_joint_demand_rendezvous": "No joint demand-rendezvous",
    "two_stage_training": "Two-stage training",
    "same_source_mappo": "Same-source MAPPO",
}


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
    fig, ax = plt.subplots(figsize=(7.1, 4.0), constrained_layout=True)
    yerr = None
    if all(item is not None for item in low + high):
        yerr = [[value - float(item) for value, item in zip(values, low)], [float(item) - value for value, item in zip(values, high)]]
    ax.errorbar(methods, values, yerr=yerr, fmt="o", linewidth=1.2, color="#2878B5", ecolor="#6B7280", capsize=3)
    ax.set_ylabel(f"{metric} (mean; 95% CI)")
    ax.set_xlabel("method")
    plt.setp(
        ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor",
    )
    fig.savefig(output_path, dpi=600, facecolor="white")
    plt.close(fig)
    return output_path


def _plotting_modules():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("plotting requires matplotlib and NumPy") from exc
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 6,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    return plt, np


def _panel_label(ax: Any, label: str) -> None:
    ax.text(-0.12, 1.04, label, transform=ax.transAxes, ha="left", va="bottom", fontweight="bold", fontsize=9)


def _condition_label(value: object) -> str:
    raw = str(value)
    if raw in CONDITION_LABELS:
        return CONDITION_LABELS[raw]
    label = raw.replace("__", " = ").replace("_", " ")
    return re.sub(r"(?<=\d)p(?=\d)", ".", label)


def _export_figure(fig: Any, base_path: Path) -> dict[str, Path]:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    for suffix, options in (
        (".svg", {}),
        (".pdf", {}),
        (".png", {"dpi": 600}),
    ):
        final = base_path.with_suffix(suffix)
        temporary = final.with_name(f"{final.stem}.tmp{suffix}")
        fig.savefig(temporary, bbox_inches="tight", facecolor="white", **options)
        os.replace(temporary, final)
        outputs[suffix.removeprefix(".")] = final
    return outputs


def _metric_errorbar(ax: Any, rows: list[Mapping[str, object]], metric: str) -> None:
    _, np = _plotting_modules()
    methods = sorted({str(row["analysis_group"]) for row in rows})
    scales = sorted({str(row["scale"]) for row in rows}, key=lambda value: int(value[1:]) if value[1:].isdigit() else value)
    x = np.arange(len(scales))
    for method in methods:
        lookup = {str(row["scale"]): row for row in rows if str(row["analysis_group"]) == method}
        values = np.asarray([float(lookup[scale][f"{metric}_mean"]) if scale in lookup else np.nan for scale in scales])
        low = np.asarray([lookup[scale].get(f"{metric}_ci_low") if scale in lookup else np.nan for scale in scales], dtype=float)
        high = np.asarray([lookup[scale].get(f"{metric}_ci_high") if scale in lookup else np.nan for scale in scales], dtype=float)
        color = METHOD_COLORS.get(method, "#484878")
        label = METHOD_LABELS.get(method, _condition_label(method))
        ax.plot(x, values, marker="o", ms=3.8, lw=1.4, color=color, label=label)
        finite = np.isfinite(values) & np.isfinite(low) & np.isfinite(high)
        if finite.any():
            ax.errorbar(
                x[finite], values[finite],
                yerr=np.vstack((values[finite] - low[finite], high[finite] - values[finite])),
                fmt="none", ecolor=color, elinewidth=0.8, capsize=2,
            )
    ax.set_xticks(x, scales)
    ax.set_xlabel("Experiment scale")


def plot_main_comparison_figure(summary: Mapping[str, object], output_base: Path) -> dict[str, Path]:
    plt, np = _plotting_modules()
    rows = list(summary["families"].get("main_comparison", []))
    if not rows:
        raise ValueError("main comparison summary is empty")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.15), gridspec_kw={"width_ratios": [1.35, 1.0]})
    _metric_errorbar(axes[0], rows, "reduction_rate")
    axes[0].set_ylabel("Pest reduction rate")
    axes[0].set_ylim(0.0, 1.0)
    axes[0].axhline(0.85, color="#B64342", ls="--", lw=0.8, alpha=0.7)
    axes[0].legend(loc="lower left", ncol=1)
    axes[0].set_title("Cross-scale treatment performance")
    _panel_label(axes[0], "a")

    paired = list(summary.get("paired", {}).get("main_reduction", []))
    if paired:
        methods = sorted({str(row["method"]) for row in paired})
        scales = sorted({str(row["scale"]) for row in paired}, key=lambda value: int(value[1:]) if value[1:].isdigit() else value)
        matrix = np.full((len(methods), len(scales)), np.nan)
        for row in paired:
            matrix[methods.index(str(row["method"])), scales.index(str(row["scale"]))] = float(row["observed_difference"])
        extent = max(float(np.nanmax(np.abs(matrix))), 1e-6)
        image = axes[1].imshow(matrix, cmap="RdBu_r", vmin=-extent, vmax=extent, aspect="auto")
        for row_index, method in enumerate(methods):
            for column_index, _scale in enumerate(scales):
                if np.isfinite(matrix[row_index, column_index]):
                    text_color = "white" if abs(matrix[row_index, column_index]) >= 0.45 * extent else "black"
                    axes[1].text(column_index, row_index, f"{matrix[row_index, column_index]:+.2f}", ha="center", va="center", fontsize=6, color=text_color)
        axes[1].set_xticks(range(len(scales)), scales)
        axes[1].set_yticks(range(len(methods)), [METHOD_LABELS.get(value, _condition_label(value)) for value in methods])
        colorbar = fig.colorbar(image, ax=axes[1], fraction=0.05, pad=0.03)
        colorbar.set_label("Comparison - SR-MAPPO")
        axes[1].set_title("Paired mean difference")
    else:
        _metric_errorbar(axes[1], rows, "success")
        axes[1].set_ylabel("Probability of reduction >= 0.85")
        axes[1].set_ylim(0.0, 1.0)
        axes[1].set_title("Treatment success")
    _panel_label(axes[1], "b")
    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.19, top=0.88, wspace=0.38)
    outputs = _export_figure(fig, output_base)
    plt.close(fig)
    return outputs


def plot_mechanism_figure(summary: Mapping[str, object], output_base: Path) -> dict[str, Path]:
    plt, np = _plotting_modules()
    rows = list(summary["families"].get("mechanism", []))
    if not rows:
        raise ValueError("mechanism summary is empty")
    metrics = (
        ("rendezvous_road_distance_m", "Rendezvous road distance (m)"),
        ("wait_s", "Waiting time (s)"),
        ("effective_spray_s", "Effective spraying time (s)"),
        ("reduction_rate", "Pest reduction rate"),
    )
    preferred = [
        "finite_no_support", "matched_fixed", "sr_mappo_mobile",
        "rolling_astar_mobile", "teleport_diagnostic", "unlimited_supply",
    ]
    available = {str(row["analysis_group"]) for row in rows}
    groups = [value for value in preferred if value in available] + sorted(available - set(preferred))
    scales = sorted({str(row["scale"]) for row in rows})
    colors = ["#0F4D92", "#42949E", "#9A4D8E", "#B64342"]
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.35))
    y = np.arange(len(groups))[::-1]
    for panel_index, (panel, (metric, ylabel), label) in enumerate(zip(axes.ravel(), metrics, "abcd")):
        for scale_index, scale in enumerate(scales):
            lookup = {
                str(row["analysis_group"]): row for row in rows if str(row["scale"]) == scale
            }
            values = np.asarray([float(lookup[group][f"{metric}_mean"]) if group in lookup else np.nan for group in groups])
            low = np.asarray([lookup[group].get(f"{metric}_ci_low") if group in lookup else np.nan for group in groups], dtype=float)
            high = np.asarray([lookup[group].get(f"{metric}_ci_high") if group in lookup else np.nan for group in groups], dtype=float)
            positions = y + (scale_index - (len(scales) - 1) / 2) * 0.12
            finite = np.isfinite(values)
            panel.plot(values[finite], positions[finite], "o", ms=3.8, color=colors[scale_index % len(colors)], label=scale)
            interval = finite & np.isfinite(low) & np.isfinite(high)
            if interval.any():
                panel.errorbar(
                    values[interval], positions[interval],
                    xerr=np.vstack((values[interval] - low[interval], high[interval] - values[interval])),
                    fmt="none", ecolor=colors[scale_index % len(colors)], elinewidth=0.8, capsize=2,
                )
        panel.set_yticks(y, [_condition_label(group) for group in groups] if panel_index % 2 == 0 else [])
        panel.set_xlabel(ylabel)
        panel.set_title(ylabel.split(" (")[0])
        _panel_label(panel, label)
    axes[0, 0].legend(title="Scale", ncol=min(3, len(scales)))
    fig.subplots_adjust(left=0.24, right=0.98, bottom=0.1, top=0.94, hspace=0.4, wspace=0.26)
    outputs = _export_figure(fig, output_base)
    plt.close(fig)
    return outputs


def _family_heatmap(ax: Any, rows: list[Mapping[str, object]], family: str, label: str) -> None:
    _, np = _plotting_modules()
    groups = sorted({str(row["analysis_group"]) for row in rows})
    scales = sorted({str(row["scale"]) for row in rows})
    matrix = np.full((len(groups), len(scales)), np.nan)
    for row in rows:
        matrix[groups.index(str(row["analysis_group"])), scales.index(str(row["scale"]))] = float(row["reduction_rate_mean"])
    image = ax.imshow(matrix, cmap="cividis", vmin=0.0, vmax=1.0, aspect="auto")
    for row_index in range(len(groups)):
        for column_index in range(len(scales)):
            if np.isfinite(matrix[row_index, column_index]):
                ax.text(column_index, row_index, f"{matrix[row_index, column_index]:.2f}", ha="center", va="center", color="white" if matrix[row_index, column_index] < 0.55 else "black", fontsize=5.5)
    ax.set_xticks(range(len(scales)), scales)
    ax.set_yticks(range(len(groups)), [_condition_label(group) for group in groups])
    ax.set_title(family.capitalize())
    ax.set_xlabel("Experiment scale")
    _panel_label(ax, label)
    return image


def plot_sensitivity_adaptation_figure(summary: Mapping[str, object], output_base: Path) -> dict[str, Path]:
    plt, _ = _plotting_modules()
    sensitivity = list(summary["families"].get("sensitivity", []))
    adaptation = list(summary["families"].get("adaptation", []))
    if not sensitivity or not adaptation:
        raise ValueError("sensitivity and adaptation summaries are required")
    fig = plt.figure(figsize=(7.1, 5.5))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 0.055], wspace=0.58)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    colorbar_axis = fig.add_subplot(grid[0, 2])
    first = _family_heatmap(axes[0], sensitivity, "sensitivity", "a")
    _family_heatmap(axes[1], adaptation, "adaptation", "b")
    colorbar = fig.colorbar(first, cax=colorbar_axis)
    colorbar.set_label("Pest reduction rate")
    fig.subplots_adjust(left=0.22, right=0.94, bottom=0.1, top=0.92)
    outputs = _export_figure(fig, output_base)
    plt.close(fig)
    return outputs


def plot_ablation_figure(summary: Mapping[str, object], output_base: Path) -> dict[str, Path]:
    plt, np = _plotting_modules()
    rows = list(summary["families"].get("ablation", []))
    if not rows:
        raise ValueError("ablation summary is empty")
    ordered = sorted(rows, key=lambda row: (str(row["scale"]), str(row["analysis_group"])))
    labels = [f"{_condition_label(row['analysis_group'])} | {row['scale']}" for row in ordered]
    y = np.arange(len(ordered))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, max(3.2, 0.28 * len(ordered) + 1.4)))
    for index, (position, row) in enumerate(zip(y, ordered)):
        value = float(row["reduction_rate_mean"])
        low = row.get("reduction_rate_ci_low")
        high = row.get("reduction_rate_ci_high")
        color = "#0F4D92" if str(row["analysis_group"]) == "full_sr_mappo" else "#7884B4"
        if low is not None and high is not None:
            axes[0].plot([float(low), float(high)], [position, position], color=color, lw=1.1)
        axes[0].plot(value, position, "o", ms=4, color=color)
    axes[0].set_yticks(y, labels)
    axes[0].set_xlim(0.0, 1.0)
    axes[0].set_xlabel("Pest reduction rate")
    axes[0].set_title("Absolute performance")
    _panel_label(axes[0], "a")

    paired = list(summary.get("paired", {}).get("ablation_reduction", []))
    if paired:
        paired = sorted(paired, key=lambda row: (str(row["scale"]), str(row["method"])))
        positions = np.arange(len(paired))[::-1]
        for position, row in zip(positions, paired):
            axes[1].plot([float(row["ci_low"]), float(row["ci_high"])], [position, position], color="#B64342", lw=1.1)
            axes[1].plot(float(row["observed_difference"]), position, "o", ms=4, color="#B64342")
        axes[1].set_yticks(positions, [f"{_condition_label(row['method'])} | {row['scale']}" for row in paired])
        axes[1].axvline(0.0, color="#767676", ls="--", lw=0.8)
        axes[1].set_xlabel("Ablation - full SR-MAPPO")
    else:
        axes[1].text(0.5, 0.5, "No paired ablation estimate", transform=axes[1].transAxes, ha="center", va="center")
        axes[1].set_xticks([])
        axes[1].set_yticks([])
    axes[1].set_title("Paired component contribution")
    _panel_label(axes[1], "b")
    fig.subplots_adjust(left=0.25, right=0.98, bottom=0.16, top=0.88, wspace=0.65)
    outputs = _export_figure(fig, output_base)
    plt.close(fig)
    return outputs


def build_chapter45_figures(
    summary: Mapping[str, object],
    output_root: Path,
    *,
    allow_partial: bool = False,
) -> dict[str, Path]:
    """Render every Chapter 4.5 figure from the same locked summary object."""

    root = Path(output_root)
    outputs: dict[str, Path] = {}
    families = summary.get("families", {})
    builders = (
        ("main_comparison", plot_main_comparison_figure, ("main_comparison",)),
        ("mechanism", plot_mechanism_figure, ("mechanism",)),
        (
            "sensitivity_adaptation",
            plot_sensitivity_adaptation_figure,
            ("sensitivity", "adaptation"),
        ),
        ("ablation", plot_ablation_figure, ("ablation",)),
    )
    for name, builder, required in builders:
        missing = [family for family in required if not families.get(family)]
        if missing and allow_partial:
            continue
        if missing:
            raise ValueError(f"Chapter 4.5 figure families are missing: {missing}")
        for suffix, path in builder(summary, root / name).items():
            outputs[f"{name}_{suffix}"] = path
    return outputs
