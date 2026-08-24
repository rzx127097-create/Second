"""Role-local Q networks and legal-action bootstrap math."""

from __future__ import annotations

from typing import Any

import torch
from torch import Tensor, nn


class QNetwork(nn.Module):
    """An MLP that maps one role-local observation to action Q values."""

    def __init__(self, input_dim: int, action_dim: int, hidden_dim: int = 128, depth: int = 2) -> None:
        super().__init__()
        if min(input_dim, action_dim, hidden_dim, depth) <= 0:
            raise ValueError("network dimensions and depth must be positive")
        self.input_dim = int(input_dim)
        self.action_dim = int(action_dim)
        layers: list[nn.Module] = []
        width = self.input_dim
        for _ in range(int(depth)):
            layers.extend((nn.Linear(width, hidden_dim), nn.Tanh()))
            width = int(hidden_dim)
        layers.append(nn.Linear(width, self.action_dim))
        self.network = nn.Sequential(*layers)
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, observation: Any) -> Tensor:
        if not isinstance(observation, torch.Tensor):
            raise TypeError("QNetwork accepts one torch role-local observation tensor")
        if observation.shape[-1] != self.input_dim:
            raise ValueError(f"expected role observation width {self.input_dim}, got {observation.shape[-1]}")
        return self.network(observation)


def masked_bootstrap_max(q: Tensor, mask: Tensor) -> Tensor:
    """Return the max Q value over legal actions, rejecting empty action sets."""

    if not isinstance(q, torch.Tensor) or q.ndim < 1:
        raise ValueError("q must include an action dimension")
    mask = torch.as_tensor(mask, dtype=torch.bool, device=q.device)
    if mask.shape != q.shape:
        raise ValueError("q and mask must have the same shape")
    if not torch.isfinite(q).all():
        raise ValueError("q values must be finite")
    if not mask.any(dim=-1).all():
        raise ValueError("each bootstrap row must have at least one legal action")
    return q.masked_fill(~mask, float("-inf")).max(dim=-1).values


__all__ = ["QNetwork", "masked_bootstrap_max"]
