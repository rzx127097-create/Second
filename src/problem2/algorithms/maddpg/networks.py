"""Role actors and centralized critics for discrete MADDPG."""

from __future__ import annotations

from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F


class DiscreteActor(nn.Module):
    """A role-local actor that emits one logit per discrete action."""

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
            raise TypeError("DiscreteActor accepts one torch role-local observation tensor")
        if observation.shape[-1] != self.input_dim:
            raise ValueError(f"expected role observation width {self.input_dim}, got {observation.shape[-1]}")
        return self.network(observation)


class CentralizedRoleQ(nn.Module):
    """A role-specific Q critic over structured state and joint actions."""

    def __init__(
        self,
        state_dim: int,
        uav_action_dim: int,
        vehicle_action_dim: int,
        hidden_dim: int = 128,
        *,
        uav_count: int = 2,
        vehicle_count: int = 1,
    ) -> None:
        super().__init__()
        if min(state_dim, uav_action_dim, vehicle_action_dim, hidden_dim, uav_count, vehicle_count) <= 0:
            raise ValueError("critic dimensions and role counts must be positive")
        self.state_dim = int(state_dim)
        self.uav_action_dim = int(uav_action_dim)
        self.vehicle_action_dim = int(vehicle_action_dim)
        self.uav_count = int(uav_count)
        self.vehicle_count = int(vehicle_count)
        input_dim = state_dim + uav_count * uav_action_dim + vehicle_count * vehicle_action_dim
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, state: Tensor, uav_action: Tensor, vehicle_action: Tensor) -> Tensor:
        if not isinstance(state, torch.Tensor) or state.shape[-1] != self.state_dim:
            raise ValueError(f"state must have final width {self.state_dim}")
        if not isinstance(uav_action, torch.Tensor) or uav_action.ndim != 3 or uav_action.shape[1:] != (self.uav_count, self.uav_action_dim):
            raise ValueError("uav joint action shape does not match critic")
        if not isinstance(vehicle_action, torch.Tensor) or vehicle_action.ndim != 3 or vehicle_action.shape[1:] != (self.vehicle_count, self.vehicle_action_dim):
            raise ValueError("vehicle joint action shape does not match critic")
        if state.shape[0] != uav_action.shape[0] or state.shape[0] != vehicle_action.shape[0]:
            raise ValueError("critic inputs must share a batch dimension")
        features = torch.cat((state, uav_action.flatten(1), vehicle_action.flatten(1)), dim=-1)
        return self.network(features).squeeze(-1)


def masked_straight_through_gumbel(logits: Tensor, mask: Tensor, temperature: float) -> Tensor:
    """Return a hard one-hot action with a masked differentiable backward pass."""

    if not isinstance(logits, torch.Tensor) or logits.ndim < 1:
        raise ValueError("logits must include an action dimension")
    mask = torch.as_tensor(mask, dtype=torch.bool, device=logits.device)
    if mask.shape != logits.shape:
        raise ValueError("logits and mask must have the same shape")
    if not torch.isfinite(logits).all():
        raise ValueError("logits must be finite")
    temperature = float(temperature)
    if not torch.isfinite(torch.tensor(temperature)) or temperature <= 0.0:
        raise ValueError("temperature must be positive and finite")
    if not mask.any(dim=-1).all():
        raise ValueError("each row must have at least one legal action")

    masked_logits = logits.masked_fill(~mask, float("-inf"))
    uniform = torch.rand_like(masked_logits).clamp_(min=torch.finfo(logits.dtype).tiny, max=1.0 - torch.finfo(logits.dtype).eps)
    gumbel = -torch.log(-torch.log(uniform))
    soft = F.softmax((masked_logits + gumbel) / temperature, dim=-1)
    hard = F.one_hot(soft.argmax(dim=-1), num_classes=logits.shape[-1]).to(dtype=logits.dtype)
    return hard - soft.detach() + soft


__all__ = ["CentralizedRoleQ", "DiscreteActor", "masked_straight_through_gumbel"]
