"""Pure tensor objectives used by the G3 SR-MAPPO trainer."""

from __future__ import annotations

from typing import Any

import torch


def ppo_policy_loss(
    new_log_prob: Any,
    old_log_prob: Any,
    advantages: Any,
    clip_epsilon: float = 0.2,
) -> torch.Tensor:
    if clip_epsilon <= 0.0:
        raise ValueError("clip_epsilon must be positive")
    ratio = torch.exp(new_log_prob - old_log_prob)
    unclipped = ratio * advantages
    clipped = torch.clamp(
        ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon
    ) * advantages
    return -torch.minimum(unclipped, clipped).mean()


def _huber(residual: torch.Tensor, delta: float | None) -> torch.Tensor:
    if delta is None:
        return 0.5 * residual.square()
    threshold = torch.as_tensor(delta, dtype=residual.dtype, device=residual.device)
    absolute = residual.abs()
    quadratic = torch.minimum(absolute, threshold)
    linear = absolute - quadratic
    return 0.5 * quadratic.square() + threshold * linear


def value_loss(
    new_value: Any,
    old_value: Any,
    returns: Any,
    clip_epsilon: float = 0.2,
    huber_delta: float | None = 1.0,
    clip: bool = True,
) -> torch.Tensor:
    predictions = [new_value]
    if clip:
        predictions.append(
            old_value + torch.clamp(
                new_value - old_value, -clip_epsilon, clip_epsilon
            )
        )
    losses = torch.stack(
        [_huber(prediction - returns, huber_delta) for prediction in predictions],
        dim=0,
    )
    return losses.amax(dim=0).mean()


def entropy_bonus(entropies: Any) -> torch.Tensor:
    return entropies.mean()


__all__ = ["entropy_bonus", "ppo_policy_loss", "value_loss"]
