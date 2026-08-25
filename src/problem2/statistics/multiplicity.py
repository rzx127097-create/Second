from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AdjustedRecord:
    family: str
    hypothesis_id: str
    raw_p_value: float
    adjusted_p_value: float
    rank: int
    reject_05: bool

    @property
    def p_value(self) -> float:
        return self.raw_p_value

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def holm_adjust(records: Iterable[Mapping[str, object]]) -> list[AdjustedRecord]:
    items = []
    for row in records:
        if not isinstance(row, Mapping) or "family" not in row or "hypothesis_id" not in row:
            raise ValueError("family and hypothesis_id are required")
        try:
            p = float(row.get("p_value", row.get("raw_p_value")))
        except (TypeError, ValueError) as exc:
            raise ValueError("p_value must be numeric") from exc
        if not math.isfinite(p) or p < 0 or p > 1:
            raise ValueError("p_value must be in [0,1]")
        family, hypothesis = str(row["family"]), str(row["hypothesis_id"])
        items.append((family, hypothesis, p))
    seen = set()
    for family, hypothesis, _ in items:
        if (family, hypothesis) in seen:
            raise ValueError("duplicate hypothesis")
        seen.add((family, hypothesis))
    output = []
    family_order = list(dict.fromkeys(item[0] for item in items))
    for family in family_order:
        ordered = sorted((item for item in items if item[0] == family), key=lambda item: (item[2], item[1]))
        running = 0.0
        m = len(ordered)
        for rank, (_, hypothesis, p) in enumerate(ordered, 1):
            running = max(running, min(1.0, (m - rank + 1) * p))
            output.append(AdjustedRecord(family, hypothesis, p, running, rank, running <= 0.05))
    return output
