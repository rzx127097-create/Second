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
    bootstrap_dones: np.ndarray | None = None,
    next_values: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute reverse-time GAE; ``dones`` cuts bootstrap at episode boundaries."""

    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    dones = np.asarray(dones, dtype=np.float64)
    bootstrap = dones if bootstrap_dones is None else np.asarray(bootstrap_dones, dtype=np.float64)
    explicit_next = None if next_values is None else np.asarray(next_values, dtype=np.float64)
    if not (rewards.shape == values.shape == dones.shape == bootstrap.shape):
        raise ValueError("rewards, values, dones and bootstrap_dones must have equal shapes")
    if explicit_next is not None and explicit_next.shape != rewards.shape:
        raise ValueError("next_values must have equal shape to rewards")
    next_value = float(0.0 if last_value is None else last_value)
    advantage = np.zeros_like(rewards, dtype=np.float64)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        if explicit_next is not None and np.isfinite(explicit_next[index]):
            next_value = explicit_next[index]
        elif index < len(rewards) - 1:
            next_value = values[index + 1]
        nonterminal_bootstrap = 1.0 - bootstrap[index]
        nonterminal_trace = 1.0 - dones[index]
        delta = rewards[index] + gamma * next_value * nonterminal_bootstrap - values[index]
        running = delta + gamma * gae_lambda * nonterminal_trace * running
        advantage[index] = running
    return advantage.astype(np.float32), (advantage + values).astype(np.float32)


def normalize_advantages(advantages: np.ndarray, valid_mask: np.ndarray | None = None, epsilon: float = 1e-8) -> np.ndarray:
    """Normalize only the declared actor-valid samples and preserve padding."""
    values = np.asarray(advantages, dtype=np.float32)
    mask = np.ones(values.shape, dtype=bool) if valid_mask is None else np.asarray(valid_mask, dtype=bool)
    if values.shape != mask.shape:
        raise ValueError("advantages and valid_mask must have equal shapes")
    if not mask.any():
        return values.copy()
    selected = values[mask]
    mean = float(selected.mean())
    std = float(selected.std())
    result = values.copy()
    result[mask] = (selected - mean) / max(std, float(epsilon))
    return result
