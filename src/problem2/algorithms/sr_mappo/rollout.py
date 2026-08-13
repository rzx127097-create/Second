"""Rollout storage preserving role masks for PPO replay."""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any

import numpy as np


@dataclass
class RolloutBatch:
    observations: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    policy_observations: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    states: list[Any] = field(default_factory=list)
    actions: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    masks: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    log_probs: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    entropies: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    agent_ids: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    valid_actor_samples: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    candidate_mappings: list[Any] = field(default_factory=list)
    reward_components: list[dict[str, float]] = field(default_factory=list)
    normalization_versions: list[dict[str, int]] = field(default_factory=list)
    episode_ids: list[str | int | None] = field(default_factory=list)
    terminated: list[bool] = field(default_factory=list)
    truncated: list[bool] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    dones: list[bool] = field(default_factory=list)
    advantages: np.ndarray | None = None
    returns: np.ndarray | None = None

    def add(
        self,
        *,
        observations: dict[str, Any],
        state: Any,
        actions: dict[str, Any],
        masks: dict[str, Any],
        log_probs: dict[str, Any],
        reward: float,
        value: float,
        done: bool,
        policy_observations: dict[str, Any] | None = None,
        entropies: dict[str, Any] | None = None,
        agent_ids: dict[str, Any] | None = None,
        candidate_mapping: Any = None,
        valid_actor_sample: dict[str, bool] | None = None,
        reward_components: dict[str, float] | None = None,
        normalization_version: dict[str, int] | None = None,
        episode_id: str | int | None = None,
        terminated: bool | None = None,
        truncated: bool | None = None,
    ) -> None:
        """Append one joint transition without reconstructing masks later.

        ``policy_observations`` are the exact normalized inputs used by the
        actor during collection.  Keeping them alongside the raw observations
        makes PPO replay independent of later running-stat updates.
        """
        for role in ("uav", "vehicle"):
            self.observations[role].append(deepcopy(observations[role]))
            self.policy_observations[role].append(
                deepcopy(observations[role] if policy_observations is None else policy_observations[role])
            )
            self.actions[role].append(deepcopy(actions[role]))
            self.masks[role].append(deepcopy(masks[role]))
            self.log_probs[role].append(deepcopy(log_probs[role]))
            if entropies is not None:
                self.entropies[role].append(deepcopy(entropies[role]))
            if agent_ids is not None:
                self.agent_ids[role].append(deepcopy(agent_ids.get(role)))
            else:
                self.agent_ids[role].append(None)
            self.valid_actor_samples[role].append(
                True if valid_actor_sample is None else deepcopy(valid_actor_sample.get(role, True))
            )
        self.states.append(deepcopy(state))
        self.candidate_mappings.append(deepcopy(candidate_mapping))
        self.reward_components.append(deepcopy(dict(reward_components or {})))
        self.normalization_versions.append(deepcopy(dict(normalization_version or {})))
        self.episode_ids.append(episode_id)
        self.terminated.append(bool(done if terminated is None else terminated))
        self.truncated.append(bool(False if truncated is None else truncated))
        self.rewards.append(float(reward))
        self.values.append(float(value))
        self.dones.append(bool(done))

    def finish(self, gamma: float, gae_lambda: float, last_value: float = 0.0) -> None:
        from ..common.gae import compute_gae
        # Time-limit truncation retains the continuation value; only an actual
        # terminal state cuts the bootstrap in the team GAE recursion.
        terminated = self.terminated if len(self.terminated) == len(self.rewards) else self.dones
        truncated = self.truncated if len(self.truncated) == len(self.rewards) else [False] * len(self.rewards)
        trace_dones = np.logical_or(np.asarray(terminated, dtype=bool), np.asarray(truncated, dtype=bool)).astype(float)
        self.advantages, self.returns = compute_gae(
            np.asarray(self.rewards),
            np.asarray(self.values),
            trace_dones,
            gamma,
            gae_lambda,
            last_value,
            bootstrap_dones=np.asarray(terminated, dtype=float),
        )

    def normalize_advantages(self) -> None:
        """Normalize team advantages over the union of valid role samples."""
        if self.advantages is None:
            raise ValueError("rollout must be finished before advantage normalization")
        from ..common.gae import normalize_advantages

        valid = np.asarray(
            [
                any(
                    bool(np.asarray(self.valid_actor_samples[role][index], dtype=bool).any())
                    for role in ("uav", "vehicle")
                )
                for index in range(len(self))
            ],
            dtype=bool,
        )
        self.advantages = normalize_advantages(self.advantages, valid)

    def role_valid_mask(self, role: str) -> np.ndarray:
        if role not in self.valid_actor_samples:
            raise ValueError(f"unknown role: {role}")
        values = self.valid_actor_samples[role]
        if not values:
            return np.zeros((0,), dtype=bool)
        width = max(np.asarray(value, dtype=bool).size for value in values)
        rows = []
        for value in values:
            row = np.asarray(value, dtype=bool).reshape(-1)
            if row.size == 1 and width > 1:
                row = np.repeat(row, width)
            if row.size != width:
                raise ValueError(f"inconsistent valid actor sample width for role {role}")
            rows.append(row)
        result = np.asarray(rows, dtype=bool)
        return result[:, 0] if width == 1 else result

    def __len__(self) -> int:
        return len(self.rewards)
