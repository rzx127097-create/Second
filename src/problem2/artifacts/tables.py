"""Three-line-table data representation for thesis export."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import csv
import os
from pathlib import Path


def three_line_table(rows: Iterable[dict[str, Any]], *, columns: Sequence[str], note: str = "") -> dict[str, Any]:
    return {
        "columns": list(columns), "rows": [[row.get(column, "") for column in columns] for row in rows],
        "top_rule": True, "header_rule": True, "bottom_rule": True, "note": note,
    }


def write_table(rows: Iterable[dict[str, Any]], tsv_path: Path, markdown_path: Path, *, columns: Sequence[str], note: str = "") -> None:
    data = list(rows)
    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    tsv_tmp = tsv_path.with_suffix(tsv_path.suffix + ".tmp")
    with tsv_tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        for row in data:
            writer.writerow([row.get(column, "") for column in columns])
    os.replace(tsv_tmp, tsv_path)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in data)
    if note:
        lines.append("\n" + note)
    markdown_tmp = markdown_path.with_suffix(markdown_path.suffix + ".tmp")
    markdown_tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(markdown_tmp, markdown_path)


def _display_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    displayed: list[dict[str, Any]] = []
    for row in rows:
        converted: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, float):
                converted[key] = f"{value:.4f}"
            elif value is None:
                converted[key] = "NA"
            else:
                converted[key] = value
        displayed.append(converted)
    return displayed


def build_chapter45_tables(
    summary: dict[str, Any],
    output_root: Path,
    *,
    allow_partial: bool = False,
) -> dict[str, Path]:
    """Write five thesis-ready data tables from one locked summary."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    definitions = {
        "main_comparison": (
            ["analysis_group", "scale", "reduction_rate_mean", "reduction_rate_ci_low", "reduction_rate_ci_high", "success_mean", "decision_time_mean_ms_mean", "n_training_seeds", "n_scenarios"],
            "Mean and 95% seed-level percentile interval; decision time in ms; scenarios are paired within training seeds.",
        ),
        "mechanism": (
            ["analysis_group", "scale", "rendezvous_road_distance_m_mean", "wait_s_mean", "pesticide_disabled_s_mean", "effective_spray_s_mean", "reduction_rate_mean", "n_training_seeds", "n_scenarios"],
            "Distance in m and time in s; means first aggregate shared scenarios within each training seed.",
        ),
        "sensitivity": (
            ["factor", "level", "scale", "reduction_rate_mean", "reduction_rate_ci_low", "reduction_rate_ci_high", "success_mean", "n_training_seeds", "n_scenarios"],
            "Parameter levels follow the frozen protocol; 95% intervals use training seeds as replications.",
        ),
        "adaptation": (
            ["factor", "level", "scale", "reduction_rate_mean", "reduction_rate_ci_low", "reduction_rate_ci_high", "success_mean", "n_training_seeds", "n_scenarios"],
            "Scenario levels follow the frozen protocol; shared scenarios are paired within training seeds.",
        ),
        "ablation": (
            ["analysis_group", "scale", "reduction_rate_mean", "reduction_rate_ci_low", "reduction_rate_ci_high", "success_mean", "n_training_seeds", "n_scenarios"],
            "Full and ablated variants share evaluation scenarios; 95% intervals are seed-level percentile intervals.",
        ),
    }
    outputs: dict[str, Path] = {}
    for family, (columns, note) in definitions.items():
        rows = _display_rows(summary["families"].get(family, []))
        if not rows and allow_partial:
            continue
        if not rows:
            raise ValueError(f"Chapter 4.5 table family is empty: {family}")
        tsv = root / f"{family}.tsv"
        markdown = root / f"{family}.md"
        write_table(rows, tsv, markdown, columns=columns, note=note)
        outputs[f"{family}_table_tsv"] = tsv
        outputs[f"{family}_table_markdown"] = markdown
    return outputs
