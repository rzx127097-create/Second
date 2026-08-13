"""Three-line-table data representation for thesis export."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def three_line_table(rows: Iterable[dict[str, Any]], *, columns: Sequence[str], note: str = "") -> dict[str, Any]:
    return {
        "columns": list(columns), "rows": [[row.get(column, "") for column in columns] for row in rows],
        "top_rule": True, "header_rule": True, "bottom_rule": True, "note": note,
    }
