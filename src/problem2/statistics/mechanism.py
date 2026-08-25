from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from statistics import fmean
from typing import Iterable, Mapping

MECHANISM_METRICS = (
    "rendezvous_distance_m", "vehicle_service_travel_m", "waiting_steps",
    "pesticide_disabled_steps", "effective_spray_steps", "reduction_rate",
    "success_at_0_85",
)
_EXPECTED = {"rendezvous_distance_m": -1, "vehicle_service_travel_m": -1, "waiting_steps": -1,
             "pesticide_disabled_steps": -1, "effective_spray_steps": 1, "reduction_rate": 1,
             "success_at_0_85": 1}


@dataclass(frozen=True)
class MechanismSummary:
    means: dict[str, dict[str, float]]
    paired_deltas: list[dict[str, object]]
    sign_coherence: dict[str, bool]
    interpretation: str
    causal_claim: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def _value(row: Mapping[str, object], metric: str) -> float:
    value = row.get(metric)
    if isinstance(value, bool):
        return float(value)
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid mechanism metric {metric}") from exc
    if not math.isfinite(value):
        raise ValueError(f"mechanism metric {metric} must be finite")
    return value


def summarize_mechanism(rows: Iterable[Mapping[str, object]]) -> MechanismSummary:
    records = list(rows)
    if not records:
        raise ValueError("rows must not be empty")
    by_method: dict[str, list[Mapping[str, object]]] = {}
    cells: dict[tuple[object, object, object, object], dict[str, Mapping[str, object]]] = {}
    for row in records:
        for key in ("training_seed", "scenario_id", "method"):
            if key not in row:
                raise ValueError(f"missing mechanism key {key}")
        method = str(row["method"])
        by_method.setdefault(method, []).append(row)
        key = (row["training_seed"], row["scenario_id"], row.get("scale", ""), row.get("condition_id", ""))
        bucket = cells.setdefault(key, {})
        if method in bucket:
            raise ValueError("duplicate mechanism pairing cell")
        bucket[method] = row
    if len(by_method) != 2:
        raise ValueError("mechanism summary requires exactly two methods")
    names = sorted(by_method)
    mobile_name = next((name for name in by_method if "mobile" in name.lower()), None)
    fixed_name = next((name for name in by_method if "fixed" in name.lower()), None)
    if mobile_name is not None and fixed_name is not None:
        names = [mobile_name, fixed_name]
    means = {method: {metric: fmean(_value(row, metric) for row in method_rows) for metric in MECHANISM_METRICS} for method, method_rows in by_method.items()}
    deltas: list[dict[str, object]] = []
    for key in sorted(cells, key=str):
        bucket = cells[key]
        if set(bucket) != set(names):
            raise ValueError("methods do not share mechanism cells")
        delta = {metric: _value(bucket[names[0]], metric) - _value(bucket[names[1]], metric) for metric in MECHANISM_METRICS}
        deltas.append({"training_seed": key[0], "scenario_id": key[1], "scale": key[2], "condition_id": key[3], **delta})
    values_by_metric = {metric: [delta[metric] for delta in deltas] for metric in MECHANISM_METRICS}
    scenario_ok = all(all(value * _EXPECTED[metric] >= 0 for value in values_by_metric[metric]) for metric in MECHANISM_METRICS)
    seed_groups: dict[object, list[dict[str, object]]] = {}
    for delta in deltas:
        seed_groups.setdefault(delta["training_seed"], []).append(delta)
    seed_ok = all(all(fmean(d[metric] for d in group) * _EXPECTED[metric] >= 0 for metric in MECHANISM_METRICS) for group in seed_groups.values())
    aggregate_ok = all((means[names[0]][metric] - means[names[1]][metric]) * _EXPECTED[metric] >= 0 for metric in MECHANISM_METRICS)
    endpoint = all((means[names[0]][metric] - means[names[1]][metric]) * _EXPECTED[metric] >= 0 for metric in ("reduction_rate", "success_at_0_85"))
    intermediates = all((means[names[0]][metric] - means[names[1]][metric]) * _EXPECTED[metric] >= 0 for metric in MECHANISM_METRICS[:5])
    if endpoint and intermediates:
        interpretation = "mechanism_supported_in_tested_simulation_regime"
    elif endpoint:
        interpretation = "endpoint_improves_mechanism_unresolved"
    elif intermediates:
        interpretation = "operational_continuity_improves_endpoint_unresolved"
    else:
        interpretation = "mechanism_not_supported_in_tested_simulation_regime"
    return MechanismSummary(means, deltas, {"scenario": scenario_ok, "training_seed": seed_ok, "aggregate": aggregate_ok}, interpretation)
