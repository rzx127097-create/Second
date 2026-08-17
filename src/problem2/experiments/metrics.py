"""Episode metrics derived from ScenarioBundle state and event ledgers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import numpy as np

from problem2.environment.rewards import reduction_rate, success


def _event_total(events: Iterable[Mapping[str, object]], event_type: str, field: str) -> float:
    return sum(
        float(event.get(field, 0.0))
        for event in events
        if event.get("event_type") == event_type
    )


def _request_metrics(
    events: list[Mapping[str, object]], *, episode_steps: int, decision_dt_s: float
) -> dict[str, float | int]:
    created: dict[str, tuple[int, float]] = {}
    started: dict[str, int] = {}
    completed: set[str] = set()
    for event in events:
        request_id = str(event.get("request_id", ""))
        if not request_id:
            continue
        event_type = event.get("event_type")
        if event_type == "request_created" and request_id not in created:
            created[request_id] = (int(event.get("step", 0)), float(event.get("amount_l", 0.0)))
        elif event_type == "service_started" and request_id not in started:
            started[request_id] = int(event.get("step", 0))
        elif event_type == "request_completed":
            completed.add(request_id)

    waits = [
        max(0, started.get(request_id, int(episode_steps)) - created_step) * decision_dt_s
        for request_id, (created_step, _amount_l) in created.items()
    ]
    return {
        "request_count": len(created),
        "request_completed_count": len(completed & created.keys()),
        "request_completion_rate": len(completed & created.keys()) / len(created) if created else 0.0,
        "requested_l": sum(amount_l for _step, amount_l in created.values()),
        "request_wait_mean_s": float(np.mean(waits)) if waits else 0.0,
        "request_wait_p90_s": float(np.percentile(waits, 90)) if waits else 0.0,
    }


def _vehicle_idle_time_s(events: list[Mapping[str, object]], *, decision_dt_s: float) -> float:
    service_keys = {
        (str(event.get("vehicle_id", "")), int(event.get("step", 0)))
        for event in events
        if event.get("event_type") == "service_active"
    }
    service_steps_without_vehicle = {
        int(event.get("step", 0))
        for event in events
        if event.get("event_type") == "service_active" and not event.get("vehicle_id")
    }
    idle_s = 0.0
    for event in events:
        if event.get("event_type") != "movement_applied":
            continue
        vehicle_id = str(event.get("vehicle_id", ""))
        step = int(event.get("step", 0))
        if (vehicle_id, step) in service_keys or step in service_steps_without_vehicle:
            continue
        if float(event.get("travelled_distance_m", 0.0)) <= 1e-12:
            idle_s += float(event.get("duration_s", decision_dt_s))
    return idle_s


@dataclass
class EpisodeRecord:
    """One actual ScenarioBundle trajectory and its derived smoke metrics."""

    episode_id: str
    scale_id: str
    parameter_status: str
    steps: int
    total_reward: float
    reward_components: dict[str, float]
    initial_pest_total: float
    final_pest_total: float
    pesticide_initial_l: float
    pesticide_remaining_l: float
    pesticide_sprayed_l: float
    vehicle_distance_m: float
    wait_s: float
    pesticide_disabled_s: float
    request_count: int
    request_completed_count: int
    request_completion_rate: float
    requested_l: float
    transferred_l: float
    request_wait_mean_s: float
    request_wait_p90_s: float
    effective_spray_s: float
    service_s: float
    rendezvous_road_distance_m: float
    uav_rendezvous_distance_m: float
    vehicle_idle_s: float
    vehicle_inventory_initial_l: float
    vehicle_inventory_final_l: float
    vehicle_inventory_utilization: float
    decision_time_mean_ms: float
    termination_reason: str
    events: list[dict[str, object]] = field(default_factory=list)
    losses: dict[str, float] = field(default_factory=dict)
    agent_ids: dict[str, list[str]] = field(default_factory=dict)
    rollout: Any | None = field(default=None, repr=False, compare=False)
    policy_name: str = ""
    split: str = ""
    scenario_id: str = ""
    success_threshold: float = 0.85
    training_phase: str = ""
    intervention_id: str = "baseline"
    intervention_hash: str = ""
    support_mode: str = "mobile"
    evidence_mode: str = "formal"
    simulation_profile_sha256: str = ""
    preflight_warnings: list[dict[str, object]] = field(default_factory=list)

    @property
    def reduction_rate(self) -> float:
        return reduction_rate(self.initial_pest_total, self.final_pest_total)

    @property
    def success(self) -> bool:
        return self.reduction_rate >= float(self.success_threshold)

    @property
    def event_count(self) -> int:
        return len(self.events)

    def to_row(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "scenario_id": self.scenario_id or self.scale_id,
            "split": self.split,
            "policy_name": self.policy_name,
            "training_phase": self.training_phase,
            "intervention_id": self.intervention_id,
            "intervention_hash": self.intervention_hash,
            "support_mode": self.support_mode,
            "evidence_mode": self.evidence_mode,
            "simulation_profile_sha256": self.simulation_profile_sha256,
            "preflight_warnings": list(self.preflight_warnings),
            "scale_id": self.scale_id,
            "parameter_status": self.parameter_status,
            "steps": self.steps,
            "total_reward": self.total_reward,
            "reward_control": self.reward_components.get("control", 0.0),
            "reward_service": self.reward_components.get("service", 0.0),
            "reward_coordination": self.reward_components.get("coordination", 0.0),
            "reward_invalid": self.reward_components.get("invalid", 0.0),
            "reduction_rate": self.reduction_rate,
            "success": self.success,
            "wait_s": self.wait_s,
            "pesticide_disabled_s": self.pesticide_disabled_s,
            "vehicle_distance_m": self.vehicle_distance_m,
            "request_count": self.request_count,
            "request_completed_count": self.request_completed_count,
            "request_completion_rate": self.request_completion_rate,
            "requested_l": self.requested_l,
            "transferred_l": self.transferred_l,
            "request_wait_mean_s": self.request_wait_mean_s,
            "request_wait_p90_s": self.request_wait_p90_s,
            "effective_spray_s": self.effective_spray_s,
            "service_s": self.service_s,
            "rendezvous_road_distance_m": self.rendezvous_road_distance_m,
            "uav_rendezvous_distance_m": self.uav_rendezvous_distance_m,
            "vehicle_idle_s": self.vehicle_idle_s,
            "vehicle_inventory_initial_l": self.vehicle_inventory_initial_l,
            "vehicle_inventory_final_l": self.vehicle_inventory_final_l,
            "vehicle_inventory_utilization": self.vehicle_inventory_utilization,
            "decision_time_mean_ms": self.decision_time_mean_ms,
            "termination_reason": self.termination_reason,
            "pesticide_initial_l": self.pesticide_initial_l,
            "pesticide_remaining_l": self.pesticide_remaining_l,
            "pesticide_sprayed_l": self.pesticide_sprayed_l,
            "event_count": self.event_count,
            "event_schema_version": 2,
            "events": list(self.events),
            "success_threshold": self.success_threshold,
            "uav_agent_ids": list(self.agent_ids.get("uav", [])),
            "vehicle_agent_ids": list(self.agent_ids.get("vehicle", [])),
            **self.losses,
        }


def episode_record_from_bundle(
    bundle: Any,
    *,
    episode_id: str,
    steps: int,
    total_reward: float,
    reward_components: Mapping[str, float],
    initial_pest_total: float,
    pesticide_initial_l: float,
    events: list[dict[str, object]],
    agent_ids: dict[str, list[str]],
    policy_name: str = "",
    split: str = "",
    scenario_id: str = "",
    decision_times_s: Iterable[float] = (),
    evidence_mode: str = "formal",
    simulation_profile_sha256: str = "",
    preflight_warnings: Iterable[Mapping[str, object]] = (),
) -> EpisodeRecord:
    """Materialize metrics solely from final physical state and emitted events."""

    ledger = [dict(event) for event in events]
    decision_dt_s = float(getattr(bundle.adapter, "decision_dt_s", 1.0))
    request_metrics = _request_metrics(
        ledger, episode_steps=int(steps), decision_dt_s=decision_dt_s,
    )
    final_pest_total = float(np.asarray(bundle.pest_density, dtype=float).sum())
    remaining = float(bundle.resources.total_pesticide_l)
    sprayed = float(getattr(bundle.resources, "_cumulative_sprayed_l", pesticide_initial_l - remaining))
    vehicle_initial = sum(
        float(value)
        for value in getattr(bundle.adapter, "_initial_vehicle_inventory", {}).values()
    )
    vehicle_final = sum(
        float(vehicle.inventory_l)
        for vehicle in getattr(bundle.resources, "vehicles", {}).values()
    )
    inventory_used = max(0.0, vehicle_initial - vehicle_final)
    decision_times = [float(value) for value in decision_times_s]
    termination_reason = str(getattr(bundle, "last_termination_reason", "") or "")
    if not termination_reason:
        max_steps = int(getattr(bundle, "max_steps", steps))
        termination_reason = "max_steps" if int(steps) >= max_steps else "rollout_horizon"
    return EpisodeRecord(
        episode_id=episode_id,
        scale_id=str(bundle.scale_id),
        parameter_status=str(bundle.parameter_status),
        steps=int(steps),
        total_reward=float(total_reward),
        reward_components={key: float(value) for key, value in reward_components.items()},
        initial_pest_total=float(initial_pest_total),
        final_pest_total=final_pest_total,
        pesticide_initial_l=float(pesticide_initial_l),
        pesticide_remaining_l=remaining,
        pesticide_sprayed_l=sprayed,
        vehicle_distance_m=_event_total(ledger, "movement_applied", "travelled_distance_m"),
        wait_s=_event_total(ledger, "wait", "duration_s"),
        pesticide_disabled_s=_event_total(ledger, "pesticide_disabled", "duration_s"),
        request_count=int(request_metrics["request_count"]),
        request_completed_count=int(request_metrics["request_completed_count"]),
        request_completion_rate=float(request_metrics["request_completion_rate"]),
        requested_l=float(request_metrics["requested_l"]),
        transferred_l=_event_total(ledger, "pesticide_transfer", "amount_l"),
        request_wait_mean_s=float(request_metrics["request_wait_mean_s"]),
        request_wait_p90_s=float(request_metrics["request_wait_p90_s"]),
        effective_spray_s=sum(
            float(event.get("duration_s", decision_dt_s))
            for event in ledger
            if event.get("event_type") in {"spray_applied", "spray"}
            and float(event.get("amount_l", 0.0)) > 0.0
        ),
        service_s=_event_total(ledger, "service_active", "duration_s"),
        rendezvous_road_distance_m=_event_total(
            ledger, "request_reserved", "rendezvous_road_distance_m",
        ),
        uav_rendezvous_distance_m=sum(
            float(event.get("distance_m", 0.0))
            for event in ledger
            if event.get("event_type") == "uav_movement_applied"
            and bool(event.get("rendezvous_committed", False))
        ),
        vehicle_idle_s=_vehicle_idle_time_s(ledger, decision_dt_s=decision_dt_s),
        vehicle_inventory_initial_l=vehicle_initial,
        vehicle_inventory_final_l=vehicle_final,
        vehicle_inventory_utilization=(inventory_used / vehicle_initial if vehicle_initial > 0 else 0.0),
        decision_time_mean_ms=(float(np.mean(decision_times)) * 1000.0 if decision_times else 0.0),
        termination_reason=termination_reason,
        events=ledger,
        agent_ids={role: list(ids) for role, ids in agent_ids.items()},
        policy_name=str(policy_name),
        split=str(split),
        scenario_id=str(scenario_id or getattr(bundle, "scenario_id", bundle.scale_id)),
        success_threshold=float(getattr(bundle, "success_reduction_threshold", 0.85)),
        intervention_id=str(getattr(bundle, "intervention_id", "baseline")),
        intervention_hash=str(getattr(bundle, "intervention_hash", "")),
        support_mode=str(getattr(bundle, "support_mode", "mobile")),
        evidence_mode=str(evidence_mode),
        simulation_profile_sha256=str(
            simulation_profile_sha256
            or getattr(bundle, "simulation_profile_sha256", "")
        ),
        preflight_warnings=[dict(item) for item in preflight_warnings],
    )


__all__ = ["EpisodeRecord", "episode_record_from_bundle"]
