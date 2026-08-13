"""SR-MAPPO clipped policy and value objectives."""

from __future__ import annotations

from typing import Any


def ppo_policy_loss(new_log_prob: Any, old_log_prob: Any, advantages: Any, clip_epsilon: float = 0.2) -> Any:
    """Clipped surrogate objective, returned as a minimization loss."""
    import torch
    ratio = torch.exp(new_log_prob - old_log_prob)
    unclipped = ratio * advantages
    clipped = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * advantages
    return -torch.minimum(unclipped, clipped).mean()


def value_loss(new_value: Any, old_value: Any, returns: Any, clip_epsilon: float = 0.2, huber_delta: float = 1.0, clip: bool = True) -> Any:
    """Value clipping followed by Huber regression, as used by SR-MAPPO."""
    import torch
    if clip:
        clipped_value = old_value + torch.clamp(new_value - old_value, -clip_epsilon, clip_epsilon)
        errors = torch.minimum((new_value - returns).abs(), (clipped_value - returns).abs())
        # Select the prediction with smaller absolute error before Huber penalty.
        prediction = torch.where((new_value - returns).abs() <= (clipped_value - returns).abs(), new_value, clipped_value)
    else:
        prediction = new_value
        errors = (prediction - returns).abs()
    del errors
    residual = prediction - returns
    quadratic = torch.minimum(residual.abs(), torch.as_tensor(huber_delta, device=residual.device))
    linear = residual.abs() - quadratic
    return (0.5 * quadratic.square() + huber_delta * linear).mean()


def entropy_bonus(entropies: Any) -> Any:
    return entropies.mean()
