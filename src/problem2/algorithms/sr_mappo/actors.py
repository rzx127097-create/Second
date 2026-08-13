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
            self.input_dim = int(input_dim)
            self.action_dim = int(action_dim)
            self.orthogonal_initialization = bool(orthogonal_initialization)
            self.layer_normalization = bool(layer_normalization)
            layers: list[nn.Module] = [nn.Linear(input_dim, hidden_dim)]
            if layer_normalization:
                layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.Tanh())
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            if layer_normalization:
                layers.append(nn.LayerNorm(hidden_dim))
            layers.extend((nn.Tanh(), nn.Linear(hidden_dim, action_dim)))
            self.network = nn.Sequential(*layers)
            self.apply(self._init if orthogonal_initialization else self._default_init)

        @staticmethod
        def _init(module: nn.Module) -> None:
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=nn.init.calculate_gain("tanh"))
                nn.init.constant_(module.bias, 0.0)

        @staticmethod
        def _default_init(module: nn.Module) -> None:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.constant_(module.bias, 0.0)

        def forward(self, observation: Any) -> Any:
            return self.network(observation)

else:

    class RoleActor:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            _torch_modules()
