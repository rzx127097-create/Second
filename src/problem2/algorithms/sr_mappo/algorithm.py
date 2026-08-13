"""Top-level SR-MAPPO policy and evaluation interface."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..common.normalization import RunningNormalizer
from ..common.masked_distribution import sample_action
from .actors import RoleActor
from .critic import CentralCritic


class SRMAPPOAlgorithm:
    """SR-MAPPO with separate UAV/vehicle actors and a centralized critic."""

    def __init__(self, uav_obs_dim: int, vehicle_obs_dim: int, state_dim: int, uav_action_dim: int, vehicle_action_dim: int, hidden_dim: int = 128, device: str = "cpu") -> None:
        try:
            import torch
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("SR-MAPPO requires PyTorch for neural policies") from exc
        self.device = torch.device(device)
        self.uav_actor = RoleActor(uav_obs_dim, uav_action_dim, hidden_dim).to(self.device)
        self.vehicle_actor = RoleActor(vehicle_obs_dim, vehicle_action_dim, hidden_dim).to(self.device)
        self.critic = CentralCritic(state_dim, hidden_dim).to(self.device)
        self.obs_normalizer = RunningNormalizer()
        self.vehicle_obs_normalizer = RunningNormalizer()
        self.return_normalizer = RunningNormalizer()
        self.training = True

    def train(self, mode: bool = True) -> "SRMAPPOAlgorithm":
        self.training = bool(mode)
        self.uav_actor.train(mode)
        self.vehicle_actor.train(mode)
        self.critic.train(mode)
        return self

    def eval(self) -> "SRMAPPOAlgorithm":
        return self.train(False)

    def _tensor(self, value: Any):
        import torch
        return torch.as_tensor(value, dtype=torch.float32, device=self.device)

    def act(self, observations: dict[str, Any], masks: dict[str, Any], deterministic: bool = False) -> dict[str, int]:
        import torch
        with torch.no_grad():
            uav_obs = self._tensor(self.obs_normalizer.normalize(observations["uav"], update=self.training))
            vehicle_obs = self._tensor(self.vehicle_obs_normalizer.normalize(observations["vehicle"], update=self.training))
            uav = sample_action(self.uav_actor(uav_obs), torch.as_tensor(masks["uav"], dtype=torch.bool, device=self.device), deterministic)[0]
            vehicle = sample_action(self.vehicle_actor(vehicle_obs), torch.as_tensor(masks["vehicle"], dtype=torch.bool, device=self.device), deterministic)[0]
            return {"uav": int(uav.reshape(-1)[0].item()), "vehicle": int(vehicle.reshape(-1)[0].item())}

    def evaluate(self, observations: dict[str, Any], masks: dict[str, Any]) -> dict[str, int]:
        was_training = self.training
        self.eval()
        try:
            return self.act(observations, masks, deterministic=True)
        finally:
            self.train(was_training)

    def value(self, state: Any):
        return self.critic(self._tensor(state))

    def normalize_returns(self, returns: Any, *, update: bool = False) -> np.ndarray:
        """Normalize value targets during training; evaluation never updates stats."""
        return self.return_normalizer.normalize(returns, update=update)

    def state_dict(self) -> dict[str, Any]:
        return {"uav_actor": self.uav_actor.state_dict(), "vehicle_actor": self.vehicle_actor.state_dict(), "critic": self.critic.state_dict(), "obs_normalizer": self.obs_normalizer.state_dict(), "vehicle_obs_normalizer": self.vehicle_obs_normalizer.state_dict(), "return_normalizer": self.return_normalizer.state_dict()}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.uav_actor.load_state_dict(state["uav_actor"])
        self.vehicle_actor.load_state_dict(state["vehicle_actor"])
        self.critic.load_state_dict(state["critic"])
        self.obs_normalizer.load_state_dict(state["obs_normalizer"])
        self.vehicle_obs_normalizer.load_state_dict(state.get("vehicle_obs_normalizer", {}))
        self.return_normalizer.load_state_dict(state["return_normalizer"])
