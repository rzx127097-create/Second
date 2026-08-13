"""Role-separated SR-MAPPO policy networks."""

from __future__ import annotations

from typing import Any


def _torch_modules():
    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("SR-MAPPO neural networks require PyTorch") from exc
    return torch, nn


try:
    import torch
    from torch import nn
except ImportError:  # allow pure-NumPy utilities to import without torch
    torch = None
    nn = None


if nn is not None:

    class RoleActor(nn.Module):
        """Independent actor for one physical role (UAV or vehicle)."""

        def __init__(self, input_dim: int, action_dim: int, hidden_dim: int = 128) -> None:
            super().__init__()
            self.input_dim = int(input_dim)
            self.action_dim = int(action_dim)
            self.network = nn.Sequential(
                nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.Tanh(),
                nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.Tanh(),
                nn.Linear(hidden_dim, action_dim),
            )
            self.apply(self._init)

        @staticmethod
        def _init(module: nn.Module) -> None:
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=nn.init.calculate_gain("tanh"))
                nn.init.constant_(module.bias, 0.0)

        def forward(self, observation: Any) -> Any:
            return self.network(observation)

else:

    class RoleActor:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            _torch_modules()
