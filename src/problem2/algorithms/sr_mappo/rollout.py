from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import copy
from typing import Any, Mapping

import numpy as np

from problem2.algorithms.common.gae import compute_gae
from problem2.environment.action_masks import validate_candidate_slot_mapping


@dataclass(frozen=True)
class RolloutTransition:
    """One joint transition with all replay-critical G3 metadata."""

    role: Any
    agent_id: Any
    raw_observation: Any
    normalized_policy_observation: Any
    critic_state: Any
    action: Any
    action_mask: Any
    old_log_prob: Any
    value: float
    reward: float
    terminated: bool
    truncated: bool
    valid_actor_sample: Any
    candidate_mapping: Any
    normalization_versions: Any
    episode_id: str
    config_hash: str
    next_value: float | None = None
    reward_components: Mapping[str, Any] = field(default_factory=dict)
    valid: bool = True


_ALIASES: dict[str, tuple[str, ...]] = {
    "role": ("role", "roles"),
    "agent_id": ("agent_id", "agent_ids"),
    "raw_observation": ("raw_observation", "observation", "observations"),
    "normalized_policy_observation": (
        "normalized_policy_observation",
        "normalized_policy_observations",
        "policy_observation",
    ),
    "critic_state": ("critic_state", "state"),
    "action": ("action", "actions"),
    "action_mask": ("action_mask", "mask", "masks"),
    "old_log_prob": ("old_log_prob", "old_log_probs"),
    "valid_actor_sample": ("valid_actor_sample", "valid_actor_samples"),
    "candidate_mapping": (
        "candidate_mapping",
        "candidate_slot_mapping",
        "mapping",
    ),
    "normalization_versions": (
        "normalization_versions",
        "normalizer_versions",
    ),
    "episode_id": ("episode_id", "episode_identity"),
    "config_hash": ("config_hash", "config_id", "configuration_id"),
    "next_value": ("next_value", "next_values"),
}

_REQUIRED = (
    "role",
    "agent_id",
    "raw_observation",
    "normalized_policy_observation",
    "critic_state",
    "action",
    "action_mask",
    "old_log_prob",
    "value",
    "reward",
    "terminated",
    "truncated",
    "valid_actor_sample",
    "candidate_mapping",
    "normalization_versions",
    "episode_id",
    "config_hash",
)


def _record_from_transition(transition: RolloutTransition | Mapping[str, Any]) -> dict[str, Any]:
    if is_dataclass(transition):
        record = asdict(transition)
    elif isinstance(transition, Mapping):
        record = dict(transition)
    else:
        raise TypeError("transition must be a mapping or RolloutTransition")

    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in record:
                record.setdefault(canonical, record[alias])
                break
    missing = [name for name in _REQUIRED if name not in record]
    if missing:
        raise ValueError(f"transition is missing required fields: {', '.join(missing)}")
    record.setdefault("valid", record.get("valid_sample", True))
    record.setdefault("valid_sample", record["valid"])
    record.setdefault("reward_components", {})
    _validate_g3_candidate_mapping(record)
    return copy.deepcopy(record)


def _validate_g3_candidate_mapping(record: Mapping[str, Any]) -> None:
    masks = record.get("action_mask")
    mapping = record.get("candidate_mapping")
    if not isinstance(masks, Mapping) or "vehicle" not in masks:
        return
    vehicle_mask = np.asarray(masks["vehicle"], dtype=bool)
    if vehicle_mask.ndim != 2 or vehicle_mask.shape[1] != 5:
        return
    if vehicle_mask.shape[0] != 1:
        raise ValueError("G3 vehicle action mask must contain exactly one vehicle row")
    if not isinstance(mapping, Mapping) or "vehicle" not in mapping:
        raise ValueError("G3 transition must store a vehicle candidate mapping")
    validate_candidate_slot_mapping(mapping["vehicle"], vehicle_mask[0, 1:])


def _scalar(value: Any, name: str) -> float:
    array = np.asarray(value, dtype=np.float64)
    if array.size != 1 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be one finite scalar")
    return float(array.reshape(-1)[0])


class RolloutBatch:
    """Append-only joint rollout with immutable replay inputs after insertion."""

    def __init__(self, *, last_value: float | None = None) -> None:
        self.transitions: list[dict[str, Any]] = []
        self.last_value = last_value
        self.advantages = np.empty(0, dtype=np.float32)
        self.returns = np.empty(0, dtype=np.float32)
        self.normalized_advantages = np.empty(0, dtype=np.float32)
        self._finished = False

    @property
    def records(self) -> list[dict[str, Any]]:
        return self.transitions

    def __len__(self) -> int:
        return len(self.transitions)

    def add(self, transition: RolloutTransition | Mapping[str, Any]) -> None:
        self.transitions.append(_record_from_transition(transition))
        self._finished = False

    def _next_values(self) -> tuple[np.ndarray, float]:
        next_values: list[float] = []
        for index, record in enumerate(self.transitions):
            if "next_value" not in record:
                if index == len(self.transitions) - 1 and "last_value" in record:
                    next_values.append(_scalar(record["last_value"], "last_value"))
                    continue
                raise ValueError(
                    "every transition must store an explicit next_value for GAE"
                )
            next_values.append(_scalar(record["next_value"], "next_value"))

        if self.last_value is not None:
            final_value = _scalar(self.last_value, "last_value")
        elif self.transitions and "last_value" in self.transitions[-1]:
            final_value = _scalar(self.transitions[-1]["last_value"], "last_value")
        else:
            final_value = next_values[-1]
        return np.asarray(next_values, dtype=np.float64), final_value

    def finish(self, gamma: float, gae_lambda: float) -> tuple[np.ndarray, np.ndarray]:
        if not self.transitions:
            self.advantages = np.empty(0, dtype=np.float32)
            self.returns = np.empty(0, dtype=np.float32)
            self.normalized_advantages = np.empty(0, dtype=np.float32)
            self._finished = True
            return self.advantages, self.returns

        rewards = np.asarray(
            [_scalar(record["reward"], "reward") for record in self.transitions],
            dtype=np.float64,
        )
        values = np.asarray(
            [_scalar(record["value"], "value") for record in self.transitions],
            dtype=np.float64,
        )
        terminated = np.asarray(
            [bool(record["terminated"]) for record in self.transitions], dtype=bool
        )
        truncated = np.asarray(
            [bool(record["truncated"]) for record in self.transitions], dtype=bool
        )
        next_values, last_value = self._next_values()
        self.advantages, self.returns = compute_gae(
            rewards,
            values,
            terminated,
            truncated,
            last_value,
            next_values,
            gamma,
            gae_lambda,
        )
        for index, record in enumerate(self.transitions):
            record["advantage"] = np.float32(self.advantages[index])
            record["return"] = np.float32(self.returns[index])
        self._finished = True
        return self.advantages, self.returns

    def normalize_advantages(self) -> np.ndarray:
        if not self._finished:
            raise RuntimeError("finish must be called before normalizing advantages")
        if not len(self.transitions):
            self.normalized_advantages = np.empty(0, dtype=np.float32)
            return self.normalized_advantages

        valid = np.asarray(
            [bool(record.get("valid_sample", record.get("valid", True))) for record in self.transitions],
            dtype=bool,
        )
        if not valid.any():
            raise ValueError("at least one valid sample is required")
        population = self.advantages[valid].astype(np.float64)
        mean = population.mean()
        standard_deviation = population.std()
        self.normalized_advantages = (
            (self.advantages.astype(np.float64) - mean)
            / max(standard_deviation, np.finfo(np.float64).eps)
        ).astype(np.float32)
        for index, record in enumerate(self.transitions):
            record["normalized_advantage"] = np.float32(
                self.normalized_advantages[index]
            )
        return self.normalized_advantages

    def role_valid_mask(self, role: str) -> np.ndarray:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be non-empty text")
        result: list[bool] = []
        for record in self.transitions:
            role_validity = record["valid_actor_sample"]
            if isinstance(role_validity, Mapping):
                if role not in role_validity:
                    raise KeyError(f"no actor-validity entry for role {role!r}")
                role_value = np.asarray(role_validity[role], dtype=bool)
                actor_valid = bool(role_value.all())
            else:
                actor_valid = bool(np.asarray(role_validity, dtype=bool).all())
            team_valid = bool(record.get("valid_sample", record.get("valid", True)))
            result.append(actor_valid and team_valid)
        return np.asarray(result, dtype=bool)
