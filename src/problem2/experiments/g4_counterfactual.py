from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any


DELTA_METRICS = (
    "request_count",
    "reservation_count",
    "service_count",
    "total_requested_l",
    "total_transferred_l",
    "final_vehicle_inventory_l",
    "vehicle_inventory_used_l",
    "started_service_waiting_time_s",
    "euclidean_service_start_distance_m",
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


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"counterfactual {name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"counterfactual {name} must be finite and non-negative")
    return result


def _nonnegative_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"counterfactual {name} must be a non-negative integer")
    return value


def _validate_record(row: Mapping[str, Any]) -> None:
    scale_id = row.get("scale_id")
    if not isinstance(scale_id, str) or not scale_id.strip():
        raise ValueError("counterfactual scale_id must be non-empty text")
    _nonnegative_count(row.get("seed"), "seed")
    _finite_nonnegative(row.get("scarcity_level_l"), "scarcity_level_l")
    fingerprint = row.get("input_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.strip():
        raise ValueError("counterfactual input_fingerprint must be non-empty text")
    if not isinstance(row.get("scarcity_active"), bool):
        raise ValueError("counterfactual scarcity_active must be boolean")
    for name in ("request_count", "reservation_count", "service_count"):
        _nonnegative_count(row.get(name), name)
    for name in (
        "total_requested_l",
        "total_transferred_l",
        "final_vehicle_inventory_l",
        "vehicle_inventory_used_l",
        "started_service_waiting_time_s",
        "euclidean_service_start_distance_m",
        "pesticide_disabled_time_s",
        "sprayed_volume_l",
        "conservation_error_l",
    ):
        _finite_nonnegative(row.get(name), name)


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
        _validate_record(fixed_row)
        _validate_record(mobile_row)
        if fixed_row["input_fingerprint"] != mobile_row["input_fingerprint"]:
            raise ValueError("fixed and mobile probe inputs must have identical probe inputs")
        for row, expected in (
            (fixed_row, "fixed_support_probe"),
            (mobile_row, "mobile_support_probe"),
        ):
            if row.get("support_policy") != expected:
                raise ValueError(f"counterfactual arm must be {expected}")
        delta = {name: float(mobile_row[name]) - float(fixed_row[name]) for name in DELTA_METRICS}
        delta["started_service_waiting_time_reduction_s"] = (
            float(fixed_row["started_service_waiting_time_s"])
            - float(mobile_row["started_service_waiting_time_s"])
        )
        delta["euclidean_service_start_distance_change_m"] = (
            delta["euclidean_service_start_distance_m"]
        )
        for name, value in delta.items():
            if name not in ("scale_id", "seed", "scarcity_level_l") and not math.isfinite(float(value)):
                raise ValueError(f"counterfactual {name} must be finite")
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
        "comparison": ["fixed_support_probe", "mobile_support_probe"],
        "paired_count": len(pairs),
        "activation_counts": {
            "fixed": sum(bool(row.get("scarcity_active")) for row in fixed_rows),
            "mobile": sum(bool(row.get("scarcity_active")) for row in mobile_rows),
        },
        "paired_deltas": deltas,
        "aggregate": {
            "started_service_waiting_time_reduction_s": (
                _sum("started_service_waiting_time_s", fixed_rows)
                - _sum("started_service_waiting_time_s", mobile_rows)
            ),
            "euclidean_service_start_distance_change_m": (
                _sum("euclidean_service_start_distance_m", mobile_rows)
                - _sum("euclidean_service_start_distance_m", fixed_rows)
            ),
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
