"""Executable condition semantics for the Problem 2 training matrix."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ConditionExecution:
    """The physical controller and learning mode bound to one condition."""

    condition_id: str
    vehicle_controller: str
    vehicle_trainable: bool
    training_mode: str


_CONDITION_EXECUTIONS = MappingProxyType(
    {
        "sr_mappo_mobile": ConditionExecution(
            "sr_mappo_mobile", "learned", True, "joint"
        ),
        "sr_mappo_fixed": ConditionExecution(
            "sr_mappo_fixed", "fixed_support", False, "uav_only"
        ),
        "sr_mappo_astar": ConditionExecution(
            "sr_mappo_astar", "rolling_astar", False, "uav_only"
        ),
        "sr_mappo_nearest": ConditionExecution(
            "sr_mappo_nearest", "nearest_feasible", False, "uav_only"
        ),
        "sr_mappo_urgency": ConditionExecution(
            "sr_mappo_urgency", "urgency_priority", False, "uav_only"
        ),
        "sr_mappo_two_stage": ConditionExecution(
            "sr_mappo_two_stage", "learned_two_stage", True, "two_stage"
        ),
        **{
            condition_id: ConditionExecution(condition_id, "learned", True, "joint")
            for condition_id in (
                "mappo_mobile",
                "ippo_mobile",
                "maddpg_mobile",
                "iql_mobile",
                "no_observation_normalization",
                "no_return_normalization",
                "no_network_stabilization",
                "no_robust_value_update",
                "no_learning_rate_decay",
                "learning_rate",
                "clip_range",
                "entropy_coef",
                "gamma",
                "gae_lambda",
            )
        },
    }
)


def resolve_condition_execution(condition_id: str) -> ConditionExecution:
    """Resolve one frozen condition ID to its executable semantics."""

    if not isinstance(condition_id, str) or not condition_id:
        raise ValueError("condition_id must be a non-empty string")
    try:
        return _CONDITION_EXECUTIONS[condition_id]
    except KeyError as exc:
        raise ValueError(f"unknown Problem 2 condition: {condition_id}") from exc


__all__ = ["ConditionExecution", "resolve_condition_execution"]
