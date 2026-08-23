"""Shared, role-local interface for heterogeneous Problem 2 algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np

from problem2.environment.action_masks import validate_candidate_slot_mapping


ROLES = ("uav", "vehicle")
ROLE_BATCH_SCHEMA_VERSION = "g5-role-batch-v1"
ON_POLICY_ENVELOPE_SCHEMA_VERSION = "g5-on-policy-envelope-v1"


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


def _finite_numeric(array: np.ndarray, name: str) -> None:
    if not np.issubdtype(array.dtype, np.number) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite numeric arrays")


def _finite_scalar(value: Any, name: str) -> float:
    array = np.asarray(value, dtype=np.float64)
    if array.size != 1 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be one finite scalar")
    return float(array.reshape(-1)[0])


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
    action_result: ActionResult

    def __post_init__(self) -> None:
        observations = _role_mapping(self.observations, "observations")
        masks = _role_mapping(self.masks, "masks")
        actions = _role_mapping(self.actions, "actions")
        rewards = _role_mapping(self.rewards, "rewards")
        next_observations = _role_mapping(self.next_observations, "next_observations")
        next_masks = _role_mapping(self.next_masks, "next_masks")
        behavior = self.action_result
        if not isinstance(behavior, ActionResult):
            raise TypeError("action_result must be an ActionResult")
        for role in ROLES:
            if observations[role].ndim != 2 or next_observations[role].ndim != 2:
                raise ValueError(f"{role} observations must be two-dimensional role-local arrays")
            if observations[role].shape != next_observations[role].shape:
                raise ValueError(f"{role} observation shapes must match across the transition")
            _finite_numeric(observations[role], f"{role} observations")
            _finite_numeric(next_observations[role], f"{role} next_observations")
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
        return {"schema_version": ROLE_BATCH_SCHEMA_VERSION, "observations": deepcopy(self.observations), "masks": deepcopy(self.masks), "actions": deepcopy(self.actions), "rewards": deepcopy(self.rewards), "next_observations": deepcopy(self.next_observations), "next_masks": deepcopy(self.next_masks), "terminated": bool(self.terminated), "truncated": bool(self.truncated), "scenario_id": self.scenario_id, "transition_id": self.transition_id, "behavior_action_result": {"actions": deepcopy(self.action_result.actions), "masks": deepcopy(self.action_result.masks)}}

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> "RoleBatch":
        if not isinstance(state, Mapping) or state.get("schema_version") != ROLE_BATCH_SCHEMA_VERSION:
            raise ValueError("unsupported role batch schema")
        fields = {key: state[key] for key in ("observations", "masks", "actions", "rewards", "next_observations", "next_masks", "terminated", "truncated", "scenario_id", "transition_id")}
        behavior = state.get("behavior_action_result")
        if not isinstance(behavior, Mapping):
            raise ValueError("role batch state must include behavior_action_result")
        fields["action_result"] = ActionResult(**behavior)
        return cls(**fields)


@dataclass(frozen=True)
class OnPolicyEnvelope:
    """Behavior-bound, fully replayable on-policy training transition."""

    role_batch: RoleBatch
    policy_observations: Mapping[str, Any]
    old_log_probs: Mapping[str, Any]
    values: Any
    next_values: Any
    value_conditioning: str
    valid_actor_sample: Mapping[str, Any]
    agent_ids: Mapping[str, Any]
    candidate_mapping: Mapping[str, Any]
    normalization_versions: Mapping[str, Any]
    team_reward: Any
    valid_sample: bool
    critic_state: Any | None = None
    next_critic_state: Any | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role_batch, RoleBatch):
            raise TypeError("role_batch must be behavior-bound RoleBatch")
        observations = _role_mapping(self.policy_observations, "policy_observations")
        log_probs = _role_mapping(self.old_log_probs, "old_log_probs")
        validity = _role_mapping(self.valid_actor_sample, "valid_actor_sample")
        agent_ids = self.agent_ids
        if not isinstance(agent_ids, Mapping) or set(agent_ids) != set(ROLES):
            raise ValueError("agent_ids must contain exactly both roles")
        if self.value_conditioning not in {"centralized", "local"}:
            raise ValueError("value_conditioning must be centralized or local")
        team_reward = _finite_scalar(self.team_reward, "team_reward")
        if not isinstance(self.valid_sample, (bool, np.bool_)):
            raise ValueError("valid_sample must be a boolean")
        for role in ROLES:
            count = self.role_batch.actions[role].size
            if observations[role].shape != self.role_batch.observations[role].shape:
                raise ValueError(f"{role} policy observations must match role batch")
            if log_probs[role].reshape(-1).size != count or not np.isfinite(log_probs[role]).all():
                raise ValueError(f"{role} old log probabilities must be finite and aligned")
            if validity[role].reshape(-1).size != count:
                raise ValueError(f"{role} valid samples must align with actions")
            if validity[role].dtype != np.bool_:
                raise ValueError(f"{role} valid samples must have boolean dtype")
            ids = list(agent_ids[role])
            if len(ids) != count or any(not isinstance(item, str) or not item.strip() for item in ids) or len(set(ids)) != len(ids):
                raise ValueError(f"{role} agent identities must be non-empty and unique")
            _finite_numeric(observations[role], f"{role} policy observations")
            if not np.allclose(self.role_batch.rewards[role], team_reward, rtol=0.0, atol=0.0):
                raise ValueError(f"{role} rewards must equal the declared team_reward")
        if not isinstance(self.candidate_mapping, Mapping) or set(self.candidate_mapping) != {"vehicle"}:
            raise ValueError("candidate_mapping must contain vehicle slots only")
        mapping = list(self.candidate_mapping["vehicle"])
        vehicle_mask = self.role_batch.masks["vehicle"][0, 1:]
        try:
            mapping = list(validate_candidate_slot_mapping(mapping, vehicle_mask))
        except ValueError as error:
            raise ValueError("vehicle candidate mapping must match exact candidate mask") from error
        expected_normalizers = (
            {"uav", "vehicle", "return"}
            if self.value_conditioning == "centralized"
            else {"uav", "vehicle", "uav_return", "vehicle_return"}
        )
        if not isinstance(self.normalization_versions, Mapping) or set(self.normalization_versions) != expected_normalizers:
            raise ValueError("normalization_versions do not match the envelope conditioning")
        for name, version in self.normalization_versions.items():
            if isinstance(version, (bool, np.bool_)) or not isinstance(version, (int, np.integer)) or version < 0:
                raise ValueError(f"normalization_versions.{name} must be a nonnegative integer")
        if self.value_conditioning == "centralized":
            if self.critic_state is None or self.next_critic_state is None:
                raise ValueError("centralized envelopes require critic state inputs")
            _finite_scalar(self.values, "values")
            _finite_scalar(self.next_values, "next_values")
            critic_state = np.asarray(self.critic_state)
            next_critic_state = np.asarray(self.next_critic_state)
            if critic_state.ndim != 1 or next_critic_state.ndim != 1 or not critic_state.size or critic_state.shape != next_critic_state.shape:
                raise ValueError("critic_state and next_critic_state must be equally shaped nonempty vectors")
            _finite_numeric(critic_state, "critic_state")
            _finite_numeric(next_critic_state, "next_critic_state")
        else:
            if self.critic_state is not None or self.next_critic_state is not None:
                raise ValueError("local envelopes cannot contain critic-only state")
            for name, value in (("values", self.values), ("next_values", self.next_values)):
                arrays = _role_mapping(value, name)
                if any(array.shape != self.role_batch.actions[role].shape or not np.issubdtype(array.dtype, np.number) or not np.isfinite(array).all() for role, array in arrays.items()):
                    raise ValueError(f"{name} must contain finite role-local values")
        object.__setattr__(self, "policy_observations", observations)
        object.__setattr__(self, "old_log_probs", {role: log_probs[role].reshape(-1).astype(np.float32) for role in ROLES})
        object.__setattr__(self, "valid_actor_sample", {role: validity[role].reshape(-1).astype(bool) for role in ROLES})
        object.__setattr__(self, "agent_ids", {role: list(agent_ids[role]) for role in ROLES})
        object.__setattr__(self, "candidate_mapping", {"vehicle": mapping})
        object.__setattr__(self, "normalization_versions", {name: int(version) for name, version in self.normalization_versions.items()})
        object.__setattr__(self, "team_reward", team_reward)
        object.__setattr__(self, "valid_sample", bool(self.valid_sample))

    def state_dict(self) -> dict[str, Any]:
        return {"schema_version": ON_POLICY_ENVELOPE_SCHEMA_VERSION, "role_batch": self.role_batch.state_dict(), "policy_observations": deepcopy(self.policy_observations), "old_log_probs": deepcopy(self.old_log_probs), "values": deepcopy(self.values), "next_values": deepcopy(self.next_values), "value_conditioning": self.value_conditioning, "valid_actor_sample": deepcopy(self.valid_actor_sample), "agent_ids": deepcopy(self.agent_ids), "candidate_mapping": deepcopy(self.candidate_mapping), "normalization_versions": deepcopy(self.normalization_versions), "team_reward": self.team_reward, "valid_sample": self.valid_sample, "critic_state": deepcopy(self.critic_state), "next_critic_state": deepcopy(self.next_critic_state)}

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> "OnPolicyEnvelope":
        expected = {"schema_version", "role_batch", "policy_observations", "old_log_probs", "values", "next_values", "value_conditioning", "valid_actor_sample", "agent_ids", "candidate_mapping", "normalization_versions", "team_reward", "valid_sample", "critic_state", "next_critic_state"}
        if not isinstance(state, Mapping) or set(state) != expected or state.get("schema_version") != ON_POLICY_ENVELOPE_SCHEMA_VERSION:
            raise ValueError("unsupported or incomplete on-policy envelope schema")
        values = {key: state[key] for key in expected - {"schema_version", "role_batch"}}
        return cls(role_batch=RoleBatch.from_state_dict(state["role_batch"]), **values)


class HeterogeneousAlgorithm(ABC):
    """Method-independent two-role learning surface used by collection and resume."""

    roles = ROLES

    @abstractmethod
    def act(self, observations: Mapping[str, Any], masks: Mapping[str, Any], deterministic: bool = False) -> ActionResult: ...

    @abstractmethod
    def observe(self, batch: OnPolicyEnvelope) -> None: ...

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


__all__ = ["ActionResult", "HeterogeneousAlgorithm", "ON_POLICY_ENVELOPE_SCHEMA_VERSION", "OnPolicyEnvelope", "ROLE_BATCH_SCHEMA_VERSION", "ROLES", "RoleBatch"]
