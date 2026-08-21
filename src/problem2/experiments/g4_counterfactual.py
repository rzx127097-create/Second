from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


DELTA_METRICS = (
    "request_count",
    "reservation_count",
    "service_count",
    "waiting_time_s",
    "rendezvous_distance_m",
    "pesticide_disabled_time_s",
    "sprayed_volume_l",
    "conservation_error_l",
)
PAIR_KEYS = ("scale_id", "seed", "scarcity_level_l")


def _records(value: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        value = value.get("records", ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("counterfactual records must be a sequence")
    result = [dict(row) for row in value]
    if not result:
        raise ValueError("counterfactual records must not be empty")
    return result


def _key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    try:
        return tuple(row[name] for name in PAIR_KEYS)
    except KeyError as exc:
        raise ValueError(f"counterfactual record is missing {exc.args[0]}") from exc


def run_counterfactual_probe(
    fixed: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    mobile: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Build a descriptive, same-input fixed-versus-mobile comparison."""

    fixed_rows = _records(fixed)
    mobile_rows = _records(mobile)
    fixed_by_key = {_key(row): row for row in fixed_rows}
    mobile_by_key = {_key(row): row for row in mobile_rows}
    if len(fixed_by_key) != len(fixed_rows) or len(mobile_by_key) != len(mobile_rows):
        raise ValueError("counterfactual records contain duplicate probe inputs")
    if set(fixed_by_key) != set(mobile_by_key):
        raise ValueError("fixed and mobile probe inputs must be identical")

    pairs: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    for key in sorted(fixed_by_key, key=str):
        fixed_row = fixed_by_key[key]
        mobile_row = mobile_by_key[key]
        if fixed_row.get("input_fingerprint") != mobile_row.get("input_fingerprint"):
            raise ValueError("fixed and mobile probe inputs must have identical probe inputs")
        for row, expected in ((fixed_row, "fixed"), (mobile_row, "mobile")):
            if row.get("support_policy") != expected:
                raise ValueError(f"counterfactual arm must be {expected}")
        delta = {name: float(mobile_row[name]) - float(fixed_row[name]) for name in DELTA_METRICS}
        delta["waiting_time_reduction_s"] = float(fixed_row["waiting_time_s"]) - float(mobile_row["waiting_time_s"])
        delta["rendezvous_distance_change_m"] = delta["rendezvous_distance_m"]
        deltas.append({"scale_id": key[0], "seed": key[1], "scarcity_level_l": key[2], **delta})
        pairs.append({
            "scale_id": key[0],
            "seed": key[1],
            "scarcity_level_l": key[2],
            "input_fingerprint": fixed_row["input_fingerprint"],
            "fixed": {name: fixed_row.get(name) for name in DELTA_METRICS},
            "mobile": {name: mobile_row.get(name) for name in DELTA_METRICS},
        })

    def _sum(name: str, rows: list[dict[str, Any]]) -> float:
        return sum(float(row[name]) for row in rows)

    result: dict[str, Any] = {
        "status": "descriptive",
        "comparison": ["sr_mappo_fixed", "sr_mappo_mobile"],
        "paired_count": len(pairs),
        "activation_counts": {
            "fixed": sum(bool(row.get("scarcity_active")) for row in fixed_rows),
            "mobile": sum(bool(row.get("scarcity_active")) for row in mobile_rows),
        },
        "paired_deltas": deltas,
        "aggregate": {
            "waiting_time_reduction_s": _sum("waiting_time_s", fixed_rows) - _sum("waiting_time_s", mobile_rows),
            "rendezvous_distance_change_m": _sum("rendezvous_distance_m", mobile_rows) - _sum("rendezvous_distance_m", fixed_rows),
            "conservation_error_l": max(
                max(float(row["conservation_error_l"]) for row in fixed_rows),
                max(float(row["conservation_error_l"]) for row in mobile_rows),
            ),
        },
        "pairs": pairs,
    }
    if output_path is not None:
        import json
        from pathlib import Path

        Path(output_path).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["run_counterfactual_probe"]
