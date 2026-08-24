"""Direct, event-grounded G5 episode metrics."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterable, Mapping

from problem2.domain import Action, EpisodeState, Event, RequestStatus
from problem2.experiments.g5_contract import load_g5_contract


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class EpisodeRecord:
    scenario_id: int | None = None
    reduction_rate: float | None = None
    success_at_0_85: bool | None = None
    primary_outcomes_available: bool = False
    rendezvous_distance_m: float = 0.0
    vehicle_service_travel_m: float = 0.0
    waiting_steps: int = 0
    completed_request_waiting_steps: int = 0
    unresolved_terminal_requests: int = 0
    pesticide_disabled_steps: int = 0
    return_steps: int = 0
    effective_spray_steps: int = 0
    request_count: int = 0
    service_started_count: int = 0
    service_completed_count: int = 0
    partial_service_count: int = 0
    zero_transfer_count: int = 0
    requested_pesticide_l: float = 0.0
    transferred_pesticide_l: float = 0.0
    final_vehicle_inventory_l: float = 0.0
    resource_residual_l: float = 0.0
    decision_runtime_s: float = 0.0
    evaluation_state_before: str | None = None
    evaluation_state_after: str | None = None
    evaluation_state_byte_identical: bool | None = None


def _payload(event: Event) -> dict:
    return dict(event.payload)


def _finite_nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


class EpisodeMetrics:
    def __init__(
        self,
        initial_state: EpisodeState,
        *,
        tolerance: float = 1e-9,
    ) -> None:
        if not isinstance(initial_state, EpisodeState):
            raise TypeError("initial_state must be an EpisodeState")
        self.tolerance = _finite_nonnegative(tolerance, "tolerance")
        self._created = {
            request.request_id: request.created_step for request in initial_state.requests
        }
        self._requested = {
            request.request_id: request.requested_l for request in initial_state.requests
        }
        self._started: dict[str, int] = {}
        self._rendezvous_distance_m = 0.0
        self._vehicle_service_travel_m = 0.0
        self._pesticide_disabled_steps = 0
        self._return_steps = 0
        self._effective_spray_steps = 0
        self._service_completed_count = 0
        self._partial_service_count = 0
        self._zero_transfer_count = 0
        self._transferred_pesticide_l = 0.0
        self._decision_runtime_s = 0.0
        self._initial_total_l = initial_state.ledger.initial_total_l

    def record_events(self, events: Iterable[Event]) -> None:
        for event in events:
            values = _payload(event)
            if event.kind == "request_created":
                request_id = str(values["request_id"])
                if request_id in self._created:
                    raise ValueError(f"duplicate request event {request_id}")
                self._created[request_id] = event.step
                self._requested[request_id] = _finite_nonnegative(
                    values["requested_l"], "requested_l"
                )
            elif event.kind == "dispatch_reserved":
                self._rendezvous_distance_m += _finite_nonnegative(
                    values["route_length_m"], "route_length_m"
                )
            elif event.kind == "vehicle_service_motion":
                self._vehicle_service_travel_m += _finite_nonnegative(
                    values["actual_distance_m"], "actual_distance_m"
                )
            elif event.kind == "service_started":
                request_id = event.entity_id
                if request_id not in self._created:
                    raise ValueError(f"service start lacks request creation for {request_id}")
                if request_id in self._started:
                    raise ValueError(f"duplicate service start for {request_id}")
                self._started[request_id] = event.step
            elif event.kind == "spray":
                if _finite_nonnegative(values["delta_l"], "spray delta_l") > self.tolerance:
                    self._effective_spray_steps += 1
            elif event.kind == "transfer":
                actual = _finite_nonnegative(values["delta_l"], "transfer delta_l")
                self._transferred_pesticide_l += actual
                if actual <= self.tolerance:
                    self._zero_transfer_count += 1
            elif event.kind == "service_outcome":
                requested = _finite_nonnegative(values["requested_l"], "requested_l")
                transferred = _finite_nonnegative(
                    values["transferred_l"], "transferred_l"
                )
                self._service_completed_count += 1
                if self.tolerance < transferred < requested - self.tolerance:
                    self._partial_service_count += 1

    def record_step(
        self,
        before_state: EpisodeState,
        after_state: EpisodeState,
        *,
        events: Iterable[Event],
        uav_actions: Mapping[str, Action],
        returning_uav_ids: Iterable[str] = (),
        decision_runtime_s: float = 0.0,
    ) -> None:
        del after_state
        known = {uav.uav_id for uav in before_state.uavs}
        if set(uav_actions) != known:
            raise ValueError("metric UAV actions must cover the exact fleet")
        returning = tuple(returning_uav_ids)
        if len(returning) != len(set(returning)) or not set(returning).issubset(known):
            raise ValueError("returning UAV identities must be unique fleet members")
        self._pesticide_disabled_steps += sum(
            uav.pesticide_l <= self.tolerance and not uav.service_locked
            for uav in before_state.uavs
        )
        self._return_steps += len(returning)
        self._decision_runtime_s += _finite_nonnegative(
            decision_runtime_s, "decision_runtime_s"
        )
        self.record_events(events)

    def finalize(
        self,
        final_state: EpisodeState,
        *,
        terminal_boundary_step: int | None = None,
        initial_total_pest: float | None = None,
        final_total_pest: float | None = None,
        scenario_id: int | None = None,
    ) -> EpisodeRecord:
        boundary = final_state.step if terminal_boundary_step is None else terminal_boundary_step
        if isinstance(boundary, bool) or not isinstance(boundary, int) or boundary < 0:
            raise ValueError("terminal boundary step must be a nonnegative integer")
        if (initial_total_pest is None) != (final_total_pest is None):
            raise ValueError("initial and final pest totals must both be supplied or both omitted")
        reduction_rate: float | None = None
        success: bool | None = None
        available = initial_total_pest is not None
        if available:
            initial_pest = _finite_nonnegative(initial_total_pest, "initial_total_pest")
            final_pest = _finite_nonnegative(final_total_pest, "final_total_pest")
            if initial_pest <= 0.0:
                raise ValueError("initial_total_pest must be positive")
            epsilon = load_g5_contract(REPOSITORY_ROOT).metrics[
                "reduction_rate"
            ].epsilon
            if epsilon is None:
                raise ValueError("frozen reduction_rate epsilon is unavailable")
            reduction_rate = 1.0 - final_pest / (initial_pest + epsilon)
            if not math.isfinite(reduction_rate):
                raise ValueError("reduction_rate must be finite")
            success = reduction_rate >= 0.85

        waiting = 0
        completed_waiting = 0
        for request_id, start in self._started.items():
            elapsed = start - self._created[request_id]
            if elapsed < 0:
                raise ValueError("service start precedes request creation")
            waiting += elapsed
            completed_waiting += elapsed
        unresolved_ids = {
            request.request_id
            for request in final_state.requests
            if request.request_id not in self._started
            and request.status
            in (RequestStatus.PENDING, RequestStatus.RESERVED, RequestStatus.CANCELLED)
        }
        for request_id in unresolved_ids:
            if request_id not in self._created:
                raise ValueError(f"terminal request lacks creation record for {request_id}")
            elapsed = boundary - self._created[request_id]
            if elapsed < 0:
                raise ValueError("terminal boundary precedes request creation")
            waiting += elapsed

        observed = math.fsum(uav.pesticide_l for uav in final_state.uavs) + final_state.vehicle.inventory_l
        expected = self._initial_total_l - final_state.ledger.cumulative_sprayed_l
        residual = abs(observed - expected)
        return EpisodeRecord(
            scenario_id=scenario_id,
            reduction_rate=reduction_rate,
            success_at_0_85=success,
            primary_outcomes_available=available,
            rendezvous_distance_m=self._rendezvous_distance_m,
            vehicle_service_travel_m=self._vehicle_service_travel_m,
            waiting_steps=waiting,
            completed_request_waiting_steps=completed_waiting,
            unresolved_terminal_requests=len(unresolved_ids),
            pesticide_disabled_steps=self._pesticide_disabled_steps,
            return_steps=self._return_steps,
            effective_spray_steps=self._effective_spray_steps,
            request_count=len(self._created),
            service_started_count=len(self._started),
            service_completed_count=self._service_completed_count,
            partial_service_count=self._partial_service_count,
            zero_transfer_count=self._zero_transfer_count,
            requested_pesticide_l=math.fsum(self._requested.values()),
            transferred_pesticide_l=self._transferred_pesticide_l,
            final_vehicle_inventory_l=final_state.vehicle.inventory_l,
            resource_residual_l=residual,
            decision_runtime_s=self._decision_runtime_s,
        )


__all__ = ["EpisodeMetrics", "EpisodeRecord"]
