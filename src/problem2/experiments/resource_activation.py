"""Counterfactual audit for the pesticide-replenishment mechanism."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ResourceActivationReport:
    record_count: int
    activated: bool
    demand_activated: bool
    mobile_service_feasible: bool
    activation_fraction: float
    total_shortage: bool
    spatial_temporal_mismatch: bool
    mobile_gap_closure: float | None
    diagnosis: str
    condition_means: dict[str, dict[str, float]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _number(row: Mapping[str, object], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"resource activation row has invalid {field}") from exc
    if not isfinite(value) or value < 0:
        raise ValueError(f"resource activation field {field} must be finite and non-negative")
    return value


def _condition_id(row: Mapping[str, object]) -> str:
    value = str(row.get("condition_id", "")).strip()
    if not value:
        raise ValueError("resource activation row requires condition_id")
    return value


def _mean(rows: list[Mapping[str, object]], field: str) -> float:
    return sum(_number(row, field) for row in rows) / len(rows)


def audit_resource_activation(
    records: Iterable[Mapping[str, object]], *, effect_tolerance: float = 1e-12
) -> ResourceActivationReport:
    """Diagnose scarcity and spatial-temporal mismatch from matched conditions.

    This is a gate, not a significance test. Statistical inference is applied
    later to shared seed/scenario pairs; this function only checks whether the
    mechanism is present in the episode ledgers and counterfactual directions.
    """

    rows = [dict(record) for record in records]
    if not rows:
        raise ValueError("resource activation records are empty")
    if effect_tolerance < 0 or not isfinite(float(effect_tolerance)):
        raise ValueError("effect_tolerance must be finite and non-negative")

    required = (
        "reduction_rate", "request_count", "request_completion_rate",
        "pesticide_disabled_s", "wait_s", "requested_l", "transferred_l",
        "pesticide_initial_l", "pesticide_remaining_l",
    )
    grouped: dict[str, list[Mapping[str, object]]] = {}
    active_rows = 0
    finite_rows = 0
    for row in rows:
        condition = _condition_id(row)
        for field in required:
            _number(row, field)
        if _number(row, "reduction_rate") > 1.0:
            raise ValueError("reduction_rate must lie in [0, 1]")
        if _number(row, "request_completion_rate") > 1.0:
            raise ValueError("request_completion_rate must lie in [0, 1]")
        grouped.setdefault(condition, []).append(row)
        if condition != "unlimited_supply":
            finite_rows += 1
            if (
                _number(row, "request_count") > 0
                and (_number(row, "pesticide_disabled_s") > 0 or _number(row, "wait_s") > 0)
            ):
                active_rows += 1

    condition_means = {
        condition: {
            field: _mean(condition_rows, field)
            for field in (
                "reduction_rate", "request_count", "request_completion_rate",
                "pesticide_disabled_s", "wait_s", "requested_l", "transferred_l",
            )
        }
        for condition, condition_rows in grouped.items()
    }
    activation_fraction = active_rows / finite_rows if finite_rows else 0.0
    demand_activated = active_rows > 0

    def reduction(condition: str) -> float | None:
        values = condition_means.get(condition)
        return None if values is None else values["reduction_rate"]

    unlimited = reduction("unlimited_supply")
    no_support = reduction("finite_no_support")
    fixed = reduction("matched_fixed")
    teleport = reduction("teleport_diagnostic")
    mobile = reduction("sr_mappo_mobile")
    mobile_metrics = condition_means.get("sr_mappo_mobile", {})
    mobile_service_feasible = bool(
        mobile_metrics.get("transferred_l", 0.0) > effect_tolerance
    )
    activated = demand_activated and mobile_service_feasible
    total_shortage = bool(
        demand_activated and unlimited is not None and no_support is not None
        and unlimited - no_support > effect_tolerance
    )
    spatial_temporal_mismatch = bool(
        demand_activated and teleport is not None and fixed is not None
        and teleport - fixed > effect_tolerance
    )
    mobile_gap_closure = None
    if fixed is not None and teleport is not None and mobile is not None:
        denominator = teleport - fixed
        if denominator > effect_tolerance:
            mobile_gap_closure = (mobile - fixed) / denominator

    if not demand_activated:
        diagnosis = "resource_constraint_not_activated"
    elif not mobile_service_feasible:
        diagnosis = "resource_constraint_active_but_mobile_unserviceable"
    elif total_shortage and spatial_temporal_mismatch:
        diagnosis = "mixed_total_and_spatiotemporal_constraint"
    elif total_shortage:
        diagnosis = "total_resource_shortage"
    elif spatial_temporal_mismatch:
        diagnosis = "spatial_temporal_mismatch"
    else:
        diagnosis = "resource_constraint_activated_unclassified"
    return ResourceActivationReport(
        record_count=len(rows),
        activated=activated,
        demand_activated=demand_activated,
        mobile_service_feasible=mobile_service_feasible,
        activation_fraction=activation_fraction,
        total_shortage=total_shortage,
        spatial_temporal_mismatch=spatial_temporal_mismatch,
        mobile_gap_closure=mobile_gap_closure,
        diagnosis=diagnosis,
        condition_means=condition_means,
    )


__all__ = ["ResourceActivationReport", "audit_resource_activation"]
