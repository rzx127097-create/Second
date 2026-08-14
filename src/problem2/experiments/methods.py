"""Fair method profiles for the five Chapter 4.5 main comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Mapping


PRIMARY_METHODS = (
    "sr_mappo_mobile",
    "sr_mappo_fixed",
    "sr_mappo_astar",
    "mappo_mobile",
    "sr_mappo_two_stage",
)
STABILITY_COMPONENTS = (
    "observation_normalization",
    "return_normalization",
    "orthogonal_initialization",
    "layer_normalization",
    "value_clipping",
    "huber_value_loss",
    "learning_rate_decay",
)


@dataclass(frozen=True)
class MethodProfile:
    name: str
    environment_mode: str
    vehicle_controller: str
    stability_components: dict[str, bool]
    two_stage_fraction: float = 0.5

    def vehicle_phase(self, *, update_index: int, total_updates: int) -> str:
        if update_index < 1 or total_updates < 1 or update_index > total_updates:
            raise ValueError("update index must lie inside the declared training horizon")
        if self.vehicle_controller == "learned":
            return "joint_learning"
        if self.vehicle_controller == "fixed":
            return "fixed_support"
        if self.vehicle_controller == "rolling_astar":
            return "rolling_astar"
        if self.vehicle_controller == "two_stage":
            boundary = max(1, int(ceil(total_updates * self.two_stage_fraction)))
            return "stage_1_astar" if update_index <= boundary else "stage_2_joint"
        raise ValueError(f"unknown vehicle controller: {self.vehicle_controller}")


def _registered_components(algorithm_config: Mapping[str, Any]) -> dict[str, bool]:
    supplied = algorithm_config.get("stability_components", {})
    if not isinstance(supplied, Mapping):
        raise ValueError("stability_components must be a mapping")
    missing = set(STABILITY_COMPONENTS) - set(supplied)
    extra = set(supplied) - set(STABILITY_COMPONENTS)
    if missing or extra:
        raise ValueError(
            f"stability component registry mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return {name: bool(supplied[name]) for name in STABILITY_COMPONENTS}


def method_profile(name: str, algorithm_config: Mapping[str, Any]) -> MethodProfile:
    """Return one pre-registered comparison without altering physical budgets."""

    name = str(name)
    if name not in PRIMARY_METHODS:
        raise ValueError(f"unknown primary method: {name}")
    full = _registered_components(algorithm_config)
    if name == "mappo_mobile":
        return MethodProfile(name, "mobile", "learned", {key: False for key in STABILITY_COMPONENTS})
    if name == "sr_mappo_fixed":
        return MethodProfile(name, "fixed", "fixed", full)
    if name == "sr_mappo_astar":
        return MethodProfile(name, "mobile", "rolling_astar", full)
    if name == "sr_mappo_two_stage":
        return MethodProfile(name, "mobile", "two_stage", full)
    return MethodProfile(name, "mobile", "learned", full)


def _external_action_name(snapshot: Any, vehicle_id: str, phase: str) -> str:
    mask = snapshot.action_masks[vehicle_id]
    if phase == "fixed_support":
        return "hold"
    routes = snapshot.candidate_mapping.get(vehicle_id, ())
    for slot, _mapping_key in routes:
        if str(slot) in mask.valid_actions:
            return str(slot)
    return "hold"


def apply_vehicle_behavior_override(
    snapshot: Any,
    transition: dict[str, Any],
    profile: MethodProfile,
    *,
    update_index: int,
    total_updates: int,
) -> str:
    """Make rollout metadata describe the external vehicle behavior exactly."""

    phase = profile.vehicle_phase(update_index=update_index, total_updates=total_updates)
    if phase in {"joint_learning", "stage_2_joint"}:
        return phase
    vehicle_ids = sorted(
        agent_id
        for agent_id, observation in snapshot.role_observations.items()
        if str(observation.get("role")) == "vehicle"
    )
    actions: list[int] = []
    for vehicle_id in vehicle_ids:
        mask = snapshot.action_masks[vehicle_id]
        action_name = _external_action_name(snapshot, vehicle_id, phase)
        if action_name not in mask.valid_actions:
            raise ValueError(f"external controller selected masked action {action_name!r}")
        actions.append(mask.actions.index(action_name))
    transition["actions"]["vehicle"] = actions
    transition["log_probs"]["vehicle"] = [0.0] * len(actions)
    transition["entropies"]["vehicle"] = [0.0] * len(actions)
    transition["valid_actor_sample"]["vehicle"] = [False] * len(actions)
    return phase


__all__ = [
    "MethodProfile",
    "PRIMARY_METHODS",
    "STABILITY_COMPONENTS",
    "apply_vehicle_behavior_override",
    "method_profile",
]
