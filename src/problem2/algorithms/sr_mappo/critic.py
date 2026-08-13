"""Centralized team-value function for SR-MAPPO."""

from __future__ import annotations

from typing import Any

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


if nn is not None:

    class CentralCritic(nn.Module):
        """Critic sees the structured global state during centralized training."""

        def __init__(
            self,
            state_dim: int,
            hidden_dim: int = 128,
            *,
            orthogonal_initialization: bool = True,
            layer_normalization: bool = True,
        ) -> None:
            super().__init__()
            self.state_dim = int(state_dim)
            layers: list[nn.Module] = [nn.Linear(state_dim, hidden_dim)]
            if layer_normalization:
                layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.Tanh())
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            if layer_normalization:
                layers.append(nn.LayerNorm(hidden_dim))
            layers.extend((nn.Tanh(), nn.Linear(hidden_dim, 1)))
            self.network = nn.Sequential(*layers)
            for module in self.network:
                if isinstance(module, nn.Linear):
                    if orthogonal_initialization:
                        nn.init.orthogonal_(module.weight, gain=nn.init.calculate_gain("tanh"))
                    else:
                        nn.init.xavier_uniform_(module.weight)
                    nn.init.constant_(module.bias, 0.0)

        def forward(self, state: Any) -> Any:
            return self.network(state).squeeze(-1)

else:

    class CentralCritic:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            raise RuntimeError("SR-MAPPO neural networks require PyTorch")
