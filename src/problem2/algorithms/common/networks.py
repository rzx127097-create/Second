"""Small role-local neural network building blocks shared by G5 methods."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn


class RoleNetwork(nn.Module):
    """An MLP whose forward method deliberately exposes role input only."""

    def __init__(self, input_dim: int, action_dim: int, hidden_dim: int = 128, depth: int = 2) -> None:
        super().__init__()
        if min(input_dim, action_dim, hidden_dim, depth) <= 0:
            raise ValueError("network dimensions and depth must be positive")
        self.input_dim = int(input_dim)
        self.action_dim = int(action_dim)
        layers: list[nn.Module] = []
        previous = self.input_dim
        for _ in range(int(depth)):
            layers.extend((nn.Linear(previous, hidden_dim), nn.LayerNorm(hidden_dim), nn.Tanh()))
            previous = hidden_dim
        layers.append(nn.Linear(previous, self.action_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, observation: Any) -> torch.Tensor:
        if not isinstance(observation, torch.Tensor):
            raise TypeError("RoleNetwork accepts one torch role-local observation tensor")
        if observation.shape[-1] != self.input_dim:
            raise ValueError(f"expected role observation width {self.input_dim}, got {observation.shape[-1]}")
        return self.network(observation)


__all__ = ["RoleNetwork"]
