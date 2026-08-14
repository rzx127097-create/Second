"""Traceable outputs from raw episode records."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import csv
import json

from .evidence_manifest import write_evidence_manifest
from .figures import plot_metric
from .summarize import paired_differences, summarize_records
from .tables import write_table
from .validate_logs import read_jsonl


@dataclass(frozen=True)
class ArtifactBundle:
    paths: dict[str, Path]


def build_artifacts(input_jsonl: Path, output_root: Path, *, manifest: Path) -> ArtifactBundle:
    records = read_jsonl(Path(input_jsonl))
    statuses = {bool(row["provisional"]) for row in records}
    if len(statuses) != 1:
        raise ValueError("inconsistent provisional status")
    provisional = statuses.pop()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    validated = root / "validated.csv"
    columns = list(records[0].keys())
    with validated.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    rows = summarize_records(records, strict=True)
    paired = paired_differences(records)
    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps({"provisional": provisional, "rows": rows, "paired_differences": paired}, ensure_ascii=False, indent=2), encoding="utf-8")
    table_columns = ["method", "scale", "reduction_rate_mean", "reduction_rate_mean_ci_low", "reduction_rate_mean_ci_high", "success_rate", "n_seeds", "n_scenarios"]
    table_tsv = root / "three_line_table.tsv"
    table_md = root / "three_line_table.md"
    status_note = "Provisional seed-level summary" if provisional else "Formal seed-level summary (verified)"
    write_table(rows, table_tsv, table_md, columns=table_columns, note=f"{status_note}; scenarios are paired observations within training seeds.")
    figure_svg = root / "reduction_rate.svg"
    figure_png = root / "reduction_rate.png"
    plot_metric(rows, "reduction_rate_mean", str(figure_svg))
    plot_metric(rows, "reduction_rate_mean", str(figure_png))
    outputs = {"validated_csv": validated, "summary_json": summary_path, "table_tsv": table_tsv, "table_markdown": table_md, "figure_svg": figure_svg, "figure_png": figure_png}
    write_evidence_manifest(Path(manifest), Path(input_jsonl), outputs, records, provisional=provisional)
    outputs["manifest_json"] = Path(manifest)
    return ArtifactBundle(paths=outputs)
