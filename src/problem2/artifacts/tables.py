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
