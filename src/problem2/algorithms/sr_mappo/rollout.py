"""Rollout storage preserving role masks for PPO replay."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RolloutBatch:
    observations: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    states: list[Any] = field(default_factory=list)
    actions: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    masks: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    log_probs: dict[str, list[Any]] = field(default_factory=lambda: {"uav": [], "vehicle": []})
    rewards: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    dones: list[bool] = field(default_factory=list)
    advantages: np.ndarray | None = None
    returns: np.ndarray | None = None

    def add(self, *, observations: dict[str, Any], state: Any, actions: dict[str, Any], masks: dict[str, Any], log_probs: dict[str, Any], reward: float, value: float, done: bool) -> None:
        for role in ("uav", "vehicle"):
            self.observations[role].append(observations[role])
            self.actions[role].append(actions[role])
            self.masks[role].append(masks[role])
            self.log_probs[role].append(log_probs[role])
        self.states.append(state)
        self.rewards.append(float(reward))
        self.values.append(float(value))
        self.dones.append(bool(done))

    def finish(self, gamma: float, gae_lambda: float, last_value: float = 0.0) -> None:
        from ..common.gae import compute_gae
        self.advantages, self.returns = compute_gae(np.asarray(self.rewards), np.asarray(self.values), np.asarray(self.dones, dtype=float), gamma, gae_lambda, last_value)

    def __len__(self) -> int:
        return len(self.rewards)
