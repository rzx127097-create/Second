"""Structured centralized team critic for heterogeneous SR-MAPPO."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn


class CentralCritic(nn.Module):
    """A scalar team-value function that receives only structured state."""

    def __init__(
        self,
        state_dim: int,
        hidden_dim: int = 128,
        *,
        orthogonal_initialization: bool = True,
        layer_normalization: bool = True,
    ) -> None:
        super().__init__()
        if state_dim <= 0 or hidden_dim <= 0:
            raise ValueError("critic dimensions must be positive")
        self.state_dim = int(state_dim)
        layers: list[nn.Module] = [nn.Linear(state_dim, hidden_dim)]
        if layer_normalization:
            layers.append(nn.LayerNorm(hidden_dim))
        layers.append(nn.Tanh())
        layers.append(nn.Linear(hidden_dim, hidden_dim))
        if layer_normalization:
            layers.append(nn.LayerNorm(hidden_dim))
        layers.extend([nn.Tanh(), nn.Linear(hidden_dim, 1)])
        self.network = nn.Sequential(*layers)
        linear_layers = [module for module in self.modules() if isinstance(module, nn.Linear)]
        for index, module in enumerate(linear_layers):
            if orthogonal_initialization:
                gain = 1.0 if index == len(linear_layers) - 1 else nn.init.calculate_gain("tanh")
                nn.init.orthogonal_(module.weight, gain=gain)
            else:
                nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)

    def forward(self, state: Any) -> torch.Tensor:
        if not isinstance(state, torch.Tensor):
            raise TypeError("CentralCritic accepts one torch state tensor")
        if state.shape[-1] != self.state_dim:
            raise ValueError(
                f"expected structured state width {self.state_dim}, got {state.shape[-1]}"
            )
        return self.network(state).squeeze(-1)


__all__ = ["CentralCritic"]
