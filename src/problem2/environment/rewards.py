"""Auditable team reward components and outcome metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class RewardWeights:
    control_per_density: float = 1.0
    service_per_l: float = 1.0
    completion_bonus: float = 0.0
    coordination_per_wait_s: float = 0.0
    coordination_per_disabled_s: float = 0.0
    coordination_per_detour_m: float = 0.0
    coordination_per_vehicle_m: float = 0.0
    coordination_per_repeat: float = 0.0
    invalid_cost: float = 1.0
    terminal_success_bonus: float = 0.0


@dataclass(frozen=True)
class RewardResult:
    components: dict[str, float]
    total: float
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def control(self) -> float:
        return self.components["control"]

    @property
    def service(self) -> float:
        return self.components["service"]

    @property
    def coordination(self) -> float:
        return self.components["coordination"]

    @property
    def invalid(self) -> float:
        return self.components["invalid"]

    def as_dict(self) -> dict[str, Any]:
        return {**self.components, "total": self.total, **self.metrics}


def _event_amounts(events: Iterable[Mapping[str, Any]] | None) -> tuple[float, bool]:
    transferred = 0.0
    completed = False
    for event in events or ():
        event_type = str(event.get("event_type", ""))
        if event_type in {"pesticide_transfer", "transfer"}:
            transferred += max(0.0, float(event.get("amount_l", 0.0)))
        if event_type in {"request_completed", "service_completed"}:
            completed = True
    return transferred, completed


def compute_reward(
    previous_density: float,
    current_density: float,
    *,
    transferred_l: float | None = None,
    request_completed: bool = False,
    waiting_s: float = 0.0,
    disabled_s: float = 0.0,
    detour_m: float = 0.0,
    vehicle_distance_m: float = 0.0,
    repeated_spray: float = 0.0,
    invalid_count: int = 0,
    terminal_success: bool = False,
    weights: RewardWeights | None = None,
    events: Iterable[Mapping[str, Any]] | None = None,
    **_: Any,
) -> RewardResult:
    """Compute ``control + service - coordination - invalid``.

    ``transferred_l`` is the physical amount from the conservation ledger.  If
    omitted, it is derived from transfer events; no reward is paid merely for
    selecting a refill action.
    """

    weights = weights or RewardWeights()
    event_transfer, event_completed = _event_amounts(events)
    actual_transfer = event_transfer if transferred_l is None else max(0.0, float(transferred_l))
    completed = bool(request_completed or event_completed)
    density_drop = max(0.0, float(previous_density) - float(current_density))
    control = density_drop * weights.control_per_density
    service = actual_transfer * weights.service_per_l
    if completed and actual_transfer > 1e-12:
        service += weights.completion_bonus
    coordination = (
        max(0.0, float(waiting_s)) * weights.coordination_per_wait_s
        + max(0.0, float(disabled_s)) * weights.coordination_per_disabled_s
        + max(0.0, float(detour_m)) * weights.coordination_per_detour_m
        + max(0.0, float(vehicle_distance_m)) * weights.coordination_per_vehicle_m
        + max(0.0, float(repeated_spray)) * weights.coordination_per_repeat
    )
    invalid = max(0, int(invalid_count)) * weights.invalid_cost
    if terminal_success:
        control += weights.terminal_success_bonus
    components = {"control": control, "service": service, "coordination": coordination, "invalid": invalid}
    metrics = {"transferred_l": actual_transfer, "density_drop": density_drop}
    return RewardResult(components, control + service - coordination - invalid, metrics)


def reduction_rate(initial_total_pest: float, final_total_pest: float, *, epsilon: float = 1e-12) -> float:
    """Return non-negative treatment reduction relative to the initial load."""

    initial = float(initial_total_pest)
    final = float(final_total_pest)
    if initial <= epsilon:
        return 0.0
    return max(0.0, 1.0 - final / (initial + epsilon))


def success(initial_total_pest: float, final_total_pest: float, *, threshold: float = 0.85) -> bool:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("success threshold must lie in [0, 1]")
    return reduction_rate(initial_total_pest, final_total_pest) >= threshold - 1e-12


def success_rate(reductions: Iterable[float], *, threshold: float = 0.85) -> float:
    values = list(reductions)
    return 0.0 if not values else sum(float(value) >= threshold for value in values) / len(values)


__all__ = ["RewardWeights", "RewardResult", "compute_reward", "reduction_rate", "success", "success_rate"]
