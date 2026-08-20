"""Role-separated PyTorch actors for heterogeneous SR-MAPPO."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn


class RoleActor(nn.Module):
    """An actor that consumes only one role-local observation tensor."""

    def __init__(
        self,
        input_dim: int,
        action_dim: int,
        hidden_dim: int = 128,
        *,
        orthogonal_initialization: bool = True,
        layer_normalization: bool = True,
    ) -> None:
        super().__init__()
        if input_dim <= 0 or action_dim <= 0 or hidden_dim <= 0:
            raise ValueError("network dimensions must be positive")
        self.input_dim = int(input_dim)
        self.action_dim = int(action_dim)
        layers: list[nn.Module] = [nn.Linear(input_dim, hidden_dim)]
        if layer_normalization:
            layers.append(nn.LayerNorm(hidden_dim))
        layers.append(nn.Tanh())
        layers.append(nn.Linear(hidden_dim, hidden_dim))
        if layer_normalization:
            layers.append(nn.LayerNorm(hidden_dim))
        layers.extend([nn.Tanh(), nn.Linear(hidden_dim, action_dim)])
        self.network = nn.Sequential(*layers)
        self._initialize(orthogonal_initialization)

    def _initialize(self, orthogonal: bool) -> None:
        linear_layers = [module for module in self.modules() if isinstance(module, nn.Linear)]
        for index, module in enumerate(linear_layers):
            if orthogonal:
                gain = 1.0 if index == len(linear_layers) - 1 else nn.init.calculate_gain("tanh")
                nn.init.orthogonal_(module.weight, gain=gain)
            else:
                nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)

    def forward(self, observation: Any) -> torch.Tensor:
        if not isinstance(observation, torch.Tensor):
            raise TypeError("RoleActor accepts one torch observation tensor")
        if observation.shape[-1] != self.input_dim:
            raise ValueError(
                f"expected role observation width {self.input_dim}, got {observation.shape[-1]}"
            )
        return self.network(observation)


__all__ = ["RoleActor"]
