from __future__ import annotations

from typing import Sequence

import numpy as np


def _vector(values: Sequence[float] | np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array


def compute_gae(
    rewards: Sequence[float] | np.ndarray,
    values: Sequence[float] | np.ndarray,
    terminated: Sequence[bool] | np.ndarray,
    truncated: Sequence[bool] | np.ndarray,
    last_value: float,
    next_values: Sequence[float] | np.ndarray | None,
    gamma: float,
    gae_lambda: float,
    valid_sample: Sequence[bool] | np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute team GAE using explicit per-transition next-state values.

    ``next_values`` normally contains one value for each transition.  A
    length ``T - 1`` sequence is also accepted and is completed with
    ``last_value``.  Termination cuts the bootstrap; truncation keeps the
    bootstrap but cuts the backward GAE trace.
    """

    rewards_array = _vector(rewards, "rewards")
    values_array = _vector(values, "values")
    terminated_array = np.asarray(terminated, dtype=bool)
    truncated_array = np.asarray(truncated, dtype=bool)
    if terminated_array.ndim != 1 or truncated_array.ndim != 1:
        raise ValueError("terminated and truncated must be one-dimensional")
    if len(values_array) != len(rewards_array):
        raise ValueError("rewards and values must have the same length")
    if len(terminated_array) != len(rewards_array):
        raise ValueError("terminated must match rewards length")
    if len(truncated_array) != len(rewards_array):
        raise ValueError("truncated must match rewards length")
    if valid_sample is None:
        valid_array = np.ones(len(rewards_array), dtype=bool)
    else:
        valid_array = np.asarray(valid_sample)
        if valid_array.dtype != np.bool_ or valid_array.ndim != 1 or len(valid_array) != len(rewards_array):
            raise ValueError("valid_sample must be a one-dimensional boolean vector matching rewards")

    gamma = float(gamma)
    gae_lambda = float(gae_lambda)
    last_value = float(last_value)
    if not np.isfinite(last_value):
        raise ValueError("last_value must be finite")
    if not np.isfinite(gamma) or not 0.0 <= gamma <= 1.0:
        raise ValueError("gamma must be in [0, 1]")
    if not np.isfinite(gae_lambda) or not 0.0 <= gae_lambda <= 1.0:
        raise ValueError("gae_lambda must be in [0, 1]")

    steps = len(rewards_array)
    if next_values is None:
        next_array = np.empty(steps, dtype=np.float64)
        if steps:
            next_array[:-1] = values_array[1:]
            next_array[-1] = last_value
    else:
        supplied = _vector(next_values, "next_values")
        if len(supplied) == steps:
            next_array = supplied
        elif len(supplied) == max(steps - 1, 0):
            next_array = np.concatenate(
                (supplied, np.asarray([last_value], dtype=np.float64))
            )
        else:
            raise ValueError("next_values must have length T or T - 1")

    advantages = np.zeros(steps, dtype=np.float64)
    gae = 0.0
    trace_done = terminated_array | truncated_array
    for index in range(steps - 1, -1, -1):
        if not valid_array[index]:
            gae = 0.0
            continue
        bootstrap = 0.0 if terminated_array[index] else 1.0
        delta = (
            rewards_array[index]
            + gamma * bootstrap * next_array[index]
            - values_array[index]
        )
        trace = 0.0 if trace_done[index] else 1.0
        gae = delta + gamma * gae_lambda * trace * gae
        advantages[index] = gae

    returns = advantages + values_array
    returns[~valid_array] = 0.0
    return advantages.astype(np.float32), returns.astype(np.float32)
