"""Shared, role-local interface for heterogeneous Problem 2 algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np


ROLES = ("uav", "vehicle")
ROLE_BATCH_SCHEMA_VERSION = "g5-role-batch-v1"


def _role_mapping(value: Mapping[str, Any], name: str) -> dict[str, np.ndarray]:
    if not isinstance(value, Mapping) or set(value) != set(ROLES):
        raise ValueError(f"{name} must contain exactly the roles {ROLES}")
    arrays = {role: np.asarray(value[role]).copy() for role in ROLES}
    if any(array.ndim < 1 or array.shape[0] == 0 for array in arrays.values()):
        raise ValueError(f"{name} role arrays must contain at least one row")
    return arrays


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


@dataclass(frozen=True)
class ActionResult:
    """Actions and the behavior-time masks used to select them."""

    actions: Mapping[str, Any]
    masks: Mapping[str, Any]

    def __post_init__(self) -> None:
        actions = _role_mapping(self.actions, "actions")
        masks = _role_mapping(self.masks, "masks")
        for role in ROLES:
            if masks[role].ndim != 2 or masks[role].dtype != np.bool_:
                raise ValueError(f"{role} mask must be a two-dimensional boolean array")
            if actions[role].ndim != 1 or actions[role].shape[0] != masks[role].shape[0]:
                raise ValueError(f"{role} actions must contain one value for each mask row")
            if not np.issubdtype(actions[role].dtype, np.integer):
                raise ValueError(f"{role} actions must be integers")
            if (actions[role] < 0).any() or (actions[role] >= masks[role].shape[1]).any():
                raise ValueError(f"{role} actions are outside the action space")
            if not masks[role][np.arange(len(actions[role])), actions[role]].all():
                raise ValueError(f"{role} action selects a masked behavior action")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "masks", masks)


@dataclass(frozen=True)
class RoleBatch:
    """One joint, fully replayable transition with no critic-only actor input."""

    observations: Mapping[str, Any]
    masks: Mapping[str, Any]
    actions: Mapping[str, Any]
    rewards: Mapping[str, Any]
    next_observations: Mapping[str, Any]
    next_masks: Mapping[str, Any]
    terminated: bool
    truncated: bool
    scenario_id: str
    transition_id: str
    action_result: ActionResult | None = None

    def __post_init__(self) -> None:
        observations = _role_mapping(self.observations, "observations")
        masks = _role_mapping(self.masks, "masks")
        actions = _role_mapping(self.actions, "actions")
        rewards = _role_mapping(self.rewards, "rewards")
        next_observations = _role_mapping(self.next_observations, "next_observations")
        next_masks = _role_mapping(self.next_masks, "next_masks")
        behavior = self.action_result
        if behavior is not None and not isinstance(behavior, ActionResult):
            raise TypeError("action_result must be an ActionResult")
        for role in ROLES:
            if observations[role].ndim != 2 or next_observations[role].ndim != 2:
                raise ValueError(f"{role} observations must be two-dimensional role-local arrays")
            if observations[role].shape != next_observations[role].shape:
                raise ValueError(f"{role} observation shapes must match across the transition")
            for name, mask in (("masks", masks[role]), ("next_masks", next_masks[role])):
                if mask.ndim != 2 or mask.dtype != np.bool_:
                    raise ValueError(f"{role} {name} must be two-dimensional boolean arrays")
                if mask.shape[0] != observations[role].shape[0] or not mask.any(axis=1).all():
                    raise ValueError(f"{role} {name} must have a legal action for each role row")
            if actions[role].ndim != 1 or actions[role].shape[0] != observations[role].shape[0]:
                raise ValueError(f"{role} actions must align with role observations")
            if not np.issubdtype(actions[role].dtype, np.integer):
                raise ValueError(f"{role} actions must be integers")
            if (actions[role] < 0).any() or (actions[role] >= masks[role].shape[1]).any():
                raise ValueError(f"{role} actions are outside the behavior mask")
            if not masks[role][np.arange(len(actions[role])), actions[role]].all():
                raise ValueError(f"{role} actions contain an illegal behavior action")
            if rewards[role].shape != actions[role].shape or not np.isfinite(rewards[role]).all():
                raise ValueError(f"{role} rewards must be finite and align with actions")
            if behavior is not None and (
                not np.array_equal(actions[role], behavior.actions[role])
                or not np.array_equal(masks[role], behavior.masks[role])
            ):
                raise ValueError(f"{role} actions and masks must exactly match ActionResult")
        if not isinstance(self.terminated, (bool, np.bool_)) or not isinstance(self.truncated, (bool, np.bool_)):
            raise ValueError("terminated and truncated must be booleans")
        if self.terminated and self.truncated:
            raise ValueError("a transition cannot be both terminated and truncated")
        _identifier(self.scenario_id, "scenario_id")
        _identifier(self.transition_id, "transition_id")
        for name, value in (("observations", observations), ("masks", masks), ("actions", actions), ("rewards", rewards), ("next_observations", next_observations), ("next_masks", next_masks)):
            object.__setattr__(self, name, value)
        if behavior is not None:
            object.__setattr__(self, "action_result", ActionResult(actions=actions, masks=masks))

    @classmethod
    def from_action_result(
        cls,
        action_result: ActionResult,
        *,
        observations: Mapping[str, Any],
        rewards: Mapping[str, Any],
        next_observations: Mapping[str, Any],
        next_masks: Mapping[str, Any],
        terminated: bool,
        truncated: bool,
        scenario_id: str,
        transition_id: str,
    ) -> "RoleBatch":
        """Build a transition from the exact behavior output of ``act``."""

        if not isinstance(action_result, ActionResult):
            raise TypeError("action_result must be an ActionResult")
        return cls(
            observations=observations,
            masks=action_result.masks,
            actions=action_result.actions,
            rewards=rewards,
            next_observations=next_observations,
            next_masks=next_masks,
            terminated=terminated,
            truncated=truncated,
            scenario_id=scenario_id,
            transition_id=transition_id,
            action_result=action_result,
        )

    def state_dict(self) -> dict[str, Any]:
        return {"schema_version": ROLE_BATCH_SCHEMA_VERSION, "observations": deepcopy(self.observations), "masks": deepcopy(self.masks), "actions": deepcopy(self.actions), "rewards": deepcopy(self.rewards), "next_observations": deepcopy(self.next_observations), "next_masks": deepcopy(self.next_masks), "terminated": bool(self.terminated), "truncated": bool(self.truncated), "scenario_id": self.scenario_id, "transition_id": self.transition_id, "behavior_action_result": None if self.action_result is None else {"actions": deepcopy(self.action_result.actions), "masks": deepcopy(self.action_result.masks)}}

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> "RoleBatch":
        if not isinstance(state, Mapping) or state.get("schema_version") != ROLE_BATCH_SCHEMA_VERSION:
            raise ValueError("unsupported role batch schema")
        fields = {key: state[key] for key in ("observations", "masks", "actions", "rewards", "next_observations", "next_masks", "terminated", "truncated", "scenario_id", "transition_id")}
        behavior = state.get("behavior_action_result")
        if behavior is not None:
            fields["action_result"] = ActionResult(**behavior)
        return cls(**fields)


class HeterogeneousAlgorithm(ABC):
    """Method-independent two-role learning surface used by collection and resume."""

    roles = ROLES

    @abstractmethod
    def act(self, observations: Mapping[str, Any], masks: Mapping[str, Any], deterministic: bool = False) -> ActionResult: ...

    @abstractmethod
    def observe(self, batch: RoleBatch) -> None: ...

    @abstractmethod
    def update(self) -> Mapping[str, Any]: ...

    @abstractmethod
    def set_evaluation(self, enabled: bool) -> None: ...

    @abstractmethod
    def state_dict(self) -> Mapping[str, Any]: ...

    @abstractmethod
    def load_state_dict(self, state: Mapping[str, Any]) -> None: ...

    @property
    @abstractmethod
    def diagnostics(self) -> Any: ...


__all__ = ["ActionResult", "HeterogeneousAlgorithm", "ROLE_BATCH_SCHEMA_VERSION", "ROLES", "RoleBatch"]
