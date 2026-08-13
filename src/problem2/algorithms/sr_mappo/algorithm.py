"""Top-level SR-MAPPO policy and evaluation interface."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from ..common.normalization import RunningNormalizer
from ..common.masked_distribution import sample_action
from .actors import RoleActor
from .critic import CentralCritic


class SRMAPPOAlgorithm:
    """SR-MAPPO with separate UAV/vehicle actors and a centralized critic."""

    def __init__(
        self,
        uav_obs_dim: int,
        vehicle_obs_dim: int,
        state_dim: int,
        uav_action_dim: int,
        vehicle_action_dim: int,
        hidden_dim: int = 128,
        device: str = "cpu",
        stability_components: Mapping[str, bool] | None = None,
    ) -> None:
        try:
            import torch
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("SR-MAPPO requires PyTorch for neural policies") from exc
        defaults = {
            "observation_normalization": True,
            "return_normalization": True,
            "orthogonal_initialization": True,
            "layer_normalization": True,
            "value_clipping": True,
            "huber_value_loss": True,
            "learning_rate_decay": True,
        }
        if stability_components:
            defaults.update({key: bool(value) for key, value in stability_components.items()})
        self.stability_components = defaults
        self.device = torch.device(device)
        network_options = {
            "orthogonal_initialization": defaults["orthogonal_initialization"],
            "layer_normalization": defaults["layer_normalization"],
        }
        self.uav_actor = RoleActor(uav_obs_dim, uav_action_dim, hidden_dim, **network_options).to(self.device)
        self.vehicle_actor = RoleActor(vehicle_obs_dim, vehicle_action_dim, hidden_dim, **network_options).to(self.device)
        self.critic = CentralCritic(state_dim, hidden_dim, **network_options).to(self.device)
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

    @staticmethod
    def _vector(value: Any) -> Any:
        if isinstance(value, Mapping) and "vector" in value:
            return value["vector"]
        return value

    @staticmethod
    def _single_or_list(value: Any) -> Any:
        array = value.reshape(-1) if hasattr(value, "reshape") else value
        if hasattr(array, "numel") and array.numel() == 1:
            return int(array.item())
        if hasattr(array, "tolist"):
            return array.tolist()
        return array

    @staticmethod
    def _single_float_or_list(value: Any) -> float | list[float]:
        array = value.reshape(-1) if hasattr(value, "reshape") else value
        if hasattr(array, "numel") and array.numel() == 1:
            return float(array.item())
        if hasattr(array, "tolist"):
            return [float(item) for item in array.tolist()]
        return float(array)

    def act(
        self,
        observations: dict[str, Any],
        masks: dict[str, Any],
        deterministic: bool = False,
        *,
        return_details: bool = False,
    ) -> dict[str, int] | dict[str, Any]:
        import torch
        with torch.no_grad():
            uav_input = self._vector(observations["uav"])
            vehicle_input = self._vector(observations["vehicle"])
            obs_update = self.training and self.stability_components["observation_normalization"]
            uav_normalized = self.obs_normalizer.normalize(uav_input, update=obs_update) if self.stability_components["observation_normalization"] else np.asarray(uav_input, dtype=np.float32)
            vehicle_normalized = self.vehicle_obs_normalizer.normalize(vehicle_input, update=obs_update) if self.stability_components["observation_normalization"] else np.asarray(vehicle_input, dtype=np.float32)
            uav_obs = self._tensor(uav_normalized)
            vehicle_obs = self._tensor(vehicle_normalized)
            uav_mask = torch.as_tensor(masks["uav"], dtype=torch.bool, device=self.device)
            vehicle_mask = torch.as_tensor(masks["vehicle"], dtype=torch.bool, device=self.device)
            uav_action, uav_log_prob, uav_entropy = sample_action(self.uav_actor(uav_obs), uav_mask, deterministic)
            vehicle_action, vehicle_log_prob, vehicle_entropy = sample_action(self.vehicle_actor(vehicle_obs), vehicle_mask, deterministic)
            actions = {"uav": self._single_or_list(uav_action), "vehicle": self._single_or_list(vehicle_action)}
            if not return_details:
                return actions
            return {
                "actions": actions,
                "normalized_observations": {"uav": uav_normalized, "vehicle": vehicle_normalized},
                "log_probs": {"uav": self._single_float_or_list(uav_log_prob), "vehicle": self._single_float_or_list(vehicle_log_prob)},
                "entropies": {"uav": self._single_float_or_list(uav_entropy), "vehicle": self._single_float_or_list(vehicle_entropy)},
            }

    def evaluate(self, observations: dict[str, Any], masks: dict[str, Any]) -> dict[str, int]:
        was_training = self.training
        self.eval()
        try:
            return self.act(observations, masks, deterministic=True)
        finally:
            self.train(was_training)

    def value(self, state: Any):
        state_input = self._vector(state)
        return self.critic(self._tensor(state_input))

    def value_physical(self, state: Any):
        """Return critic predictions on the physical team-return scale."""
        value = self.value(state)
        if not self.stability_components["return_normalization"]:
            return value
        import torch

        restored = self.return_normalizer.denormalize(value.detach().cpu().numpy())
        return torch.as_tensor(restored, dtype=value.dtype, device=value.device)

    def collect_transition(
        self,
        observations: dict[str, Any],
        masks: dict[str, Any],
        state: Any,
        *,
        deterministic: bool = False,
        agent_ids: dict[str, Any] | None = None,
        candidate_mapping: Any = None,
        valid_actor_sample: dict[str, bool] | None = None,
        reward_components: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Collect one joint action and all replay-critical metadata."""
        details = self.act(observations, masks, deterministic=deterministic, return_details=True)
        details["state"] = state
        details["masks"] = masks
        details["agent_ids"] = agent_ids or {"uav": None, "vehicle": None}
        details["candidate_mapping"] = candidate_mapping
        details["valid_actor_sample"] = valid_actor_sample or {"uav": True, "vehicle": True}
        details["reward_components"] = reward_components or {}
        return details

    def normalize_returns(self, returns: Any, *, update: bool = False) -> np.ndarray:
        """Normalize value targets during training; evaluation never updates stats."""
        if not self.stability_components["return_normalization"]:
            return np.asarray(returns, dtype=np.float32)
        return self.return_normalizer.normalize(returns, update=update)

    def state_dict(self) -> dict[str, Any]:
        return {
            "uav_actor": self.uav_actor.state_dict(),
            "vehicle_actor": self.vehicle_actor.state_dict(),
            "critic": self.critic.state_dict(),
            "obs_normalizer": self.obs_normalizer.state_dict(),
            "vehicle_obs_normalizer": self.vehicle_obs_normalizer.state_dict(),
            "return_normalizer": self.return_normalizer.state_dict(),
            "stability_components": dict(self.stability_components),
            "training": self.training,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.uav_actor.load_state_dict(state["uav_actor"])
        self.vehicle_actor.load_state_dict(state["vehicle_actor"])
        self.critic.load_state_dict(state["critic"])
        self.obs_normalizer.load_state_dict(state["obs_normalizer"])
        self.vehicle_obs_normalizer.load_state_dict(state.get("vehicle_obs_normalizer", {}))
        self.return_normalizer.load_state_dict(state["return_normalizer"])
        self.stability_components.update(state.get("stability_components", {}))
        self.train(bool(state.get("training", True)))
