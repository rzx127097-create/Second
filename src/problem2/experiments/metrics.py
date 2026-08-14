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
    events: list[dict[str, object]] = field(default_factory=list)
    losses: dict[str, float] = field(default_factory=dict)
    agent_ids: dict[str, list[str]] = field(default_factory=dict)
    rollout: Any | None = field(default=None, repr=False, compare=False)
    policy_name: str = ""
    split: str = ""
    scenario_id: str = ""

    @property
    def reduction_rate(self) -> float:
        return reduction_rate(self.initial_pest_total, self.final_pest_total)

    @property
    def success(self) -> bool:
        return success(self.initial_pest_total, self.final_pest_total)

    @property
    def event_count(self) -> int:
        return len(self.events)

    def to_row(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "scenario_id": self.scenario_id or self.scale_id,
            "split": self.split,
            "policy_name": self.policy_name,
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
            "pesticide_initial_l": self.pesticide_initial_l,
            "pesticide_remaining_l": self.pesticide_remaining_l,
            "pesticide_sprayed_l": self.pesticide_sprayed_l,
            "event_count": self.event_count,
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
) -> EpisodeRecord:
    """Materialize metrics solely from the final bundle and emitted events.

    The current provisional adapter emits no wait or pesticide-disabled events,
    so those fields are deterministic zeros until the lower-level event model
    starts reporting them.
    """

    final_pest_total = float(np.asarray(bundle.pest_density, dtype=float).sum())
    remaining = float(bundle.resources.total_pesticide_l)
    sprayed = float(getattr(bundle.resources, "_cumulative_sprayed_l", pesticide_initial_l - remaining))
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
        vehicle_distance_m=_event_total(events, "movement_applied", "travelled_distance_m"),
        wait_s=_event_total(events, "wait", "duration_s"),
        pesticide_disabled_s=_event_total(events, "pesticide_disabled", "duration_s"),
        events=list(events),
        agent_ids={role: list(ids) for role, ids in agent_ids.items()},
        policy_name=str(policy_name),
        split=str(split),
        scenario_id=str(scenario_id or bundle.scale_id),
    )


__all__ = ["EpisodeRecord", "episode_record_from_bundle"]
