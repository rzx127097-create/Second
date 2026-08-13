"""Generalized advantage estimation for team rewards."""

from __future__ import annotations

import numpy as np


def compute_gae(
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    last_value: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute reverse-time GAE; ``dones`` cuts bootstrap at episode boundaries."""

    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    dones = np.asarray(dones, dtype=np.float64)
    if not (rewards.shape == values.shape == dones.shape):
        raise ValueError("rewards, values and dones must have equal shapes")
    next_value = float(0.0 if last_value is None else last_value)
    advantage = np.zeros_like(rewards, dtype=np.float64)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        if index < len(rewards) - 1:
            next_value = values[index + 1]
        nonterminal = 1.0 - dones[index]
        delta = rewards[index] + gamma * next_value * nonterminal - values[index]
        running = delta + gamma * gae_lambda * nonterminal * running
        advantage[index] = running
    return advantage.astype(np.float32), (advantage + values).astype(np.float32)
