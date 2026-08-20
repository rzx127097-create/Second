"""Collection and evaluation interface for heterogeneous SR-MAPPO."""

from __future__ import annotations

import pickle
from collections.abc import Mapping
from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.common.normalization import RunningNormalizer

from .actors import RoleActor
from .critic import CentralCritic


_DEFAULT_STABILITY = {
    "observation_normalization": True,
    "return_normalization": True,
    "orthogonal_initialization": True,
    "layer_normalization": True,
    "value_clipping": True,
    "huber_value_loss": True,
    "learning_rate_decay": True,
}


def _vector(value: Any) -> Any:
    if isinstance(value, Mapping) and "vector" in value:
        return value["vector"]
    return value


class SRMAPPOAlgorithm:
    """One shared UAV actor, one vehicle actor, and one team critic."""

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
        self.device = torch.device(device)
        flags = dict(_DEFAULT_STABILITY)
        if stability_components is not None:
            unknown = set(stability_components) - set(flags)
            if unknown:
                raise ValueError(f"unknown stability flags: {sorted(unknown)}")
            flags.update({key: bool(value) for key, value in stability_components.items()})
        self.stability_components = flags
        network_options = {
            "orthogonal_initialization": flags["orthogonal_initialization"],
            "layer_normalization": flags["layer_normalization"],
        }
        self.uav_actor = RoleActor(
            uav_obs_dim, uav_action_dim, hidden_dim, **network_options
        ).to(self.device)
        self.vehicle_actor = RoleActor(
            vehicle_obs_dim, vehicle_action_dim, hidden_dim, **network_options
        ).to(self.device)
        self.critic = CentralCritic(state_dim, hidden_dim, **network_options).to(
            self.device
        )
        self.uav_normalizer = RunningNormalizer(uav_obs_dim, role="uav")
        self.vehicle_normalizer = RunningNormalizer(vehicle_obs_dim, role="vehicle")
        self.return_normalizer = RunningNormalizer(1, role="return")
        self.training = True
        self._trainer: Any = None

    @property
    def obs_normalizer(self) -> RunningNormalizer:
        return self.uav_normalizer

    def train(self, mode: bool = True) -> "SRMAPPOAlgorithm":
        self.training = bool(mode)
        self.uav_actor.train(mode)
        self.vehicle_actor.train(mode)
        self.critic.train(mode)
        return self

    def eval(self) -> "SRMAPPOAlgorithm":
        return self.train(False)

    def evaluate(
        self,
        observations: Mapping[str, Any],
        masks: Mapping[str, Any],
    ) -> dict[str, Any]:
        was_training = self.training
        self.eval()
        try:
            return self.act(observations, masks, deterministic=True)
        finally:
            self.train(was_training)

    def _normalize(self, role: str, values: Any, *, update: bool) -> np.ndarray:
        array = np.asarray(_vector(values), dtype=np.float32)
        if not self.stability_components["observation_normalization"]:
            return array.copy()
        normalizer = (
            self.uav_normalizer if role == "uav" else self.vehicle_normalizer
        )
        return normalizer.normalize(array, update=update)

    def _tensor(self, values: Any) -> torch.Tensor:
        return torch.as_tensor(values, dtype=torch.float32, device=self.device)

    @staticmethod
    def _actions(value: torch.Tensor) -> list[int]:
        return value.detach().cpu().reshape(-1).to(torch.int64).tolist()

    @staticmethod
    def _floats(value: torch.Tensor) -> list[float]:
        return value.detach().cpu().reshape(-1).to(torch.float32).tolist()

    def _role_act(
        self,
        role: str,
        observation: Any,
        mask: Any,
        *,
        deterministic: bool,
        update_normalizer: bool,
    ) -> tuple[list[int], list[float], list[float], np.ndarray]:
        normalized = self._normalize(
            role, observation, update=update_normalizer
        )
        actor = self.uav_actor if role == "uav" else self.vehicle_actor
        logits = actor(self._tensor(normalized))
        distribution = masked_categorical(
            logits, torch.as_tensor(mask, dtype=torch.bool, device=self.device)
        )
        actions = (
            distribution.probs.argmax(dim=-1)
            if deterministic
            else distribution.sample()
        )
        return (
            self._actions(actions),
            self._floats(distribution.log_prob(actions)),
            self._floats(distribution.entropy()),
            normalized,
        )

    def act(
        self,
        observations: Mapping[str, Any],
        masks: Mapping[str, Any],
        deterministic: bool = False,
        *,
        return_details: bool = False,
    ) -> dict[str, Any]:
        with torch.no_grad():
            update = self.training and not deterministic
            uav_actions, uav_log_probs, uav_entropies, uav_policy_obs = self._role_act(
                "uav",
                observations["uav"],
                masks["uav"],
                deterministic=deterministic,
                update_normalizer=update,
            )
            vehicle_actions, vehicle_log_probs, vehicle_entropies, vehicle_policy_obs = self._role_act(
                "vehicle",
                observations["vehicle"],
                masks["vehicle"],
                deterministic=deterministic,
                update_normalizer=update,
            )
        actions = {"uav": uav_actions, "vehicle": vehicle_actions}
        if not return_details:
            return actions
        return {
            "actions": actions,
            "policy_observations": {
                "uav": uav_policy_obs,
                "vehicle": vehicle_policy_obs,
            },
            "normalized_observations": {
                "uav": uav_policy_obs,
                "vehicle": vehicle_policy_obs,
            },
            "masks": {
                "uav": np.asarray(masks["uav"], dtype=bool).copy(),
                "vehicle": np.asarray(masks["vehicle"], dtype=bool).copy(),
            },
            "log_probs": {
                "uav": uav_log_probs,
                "vehicle": vehicle_log_probs,
            },
            "entropies": {
                "uav": uav_entropies,
                "vehicle": vehicle_entropies,
            },
            "normalization_versions": {
                "uav": self.uav_normalizer.version,
                "vehicle": self.vehicle_normalizer.version,
                "return": self.return_normalizer.version,
            },
        }

    def replay_log_probs(
        self,
        policy_observations: Mapping[str, Any],
        masks: Mapping[str, Any],
        actions: Mapping[str, Any],
    ) -> dict[str, np.ndarray]:
        with torch.no_grad():
            results: dict[str, np.ndarray] = {}
            for role, actor in (
                ("uav", self.uav_actor),
                ("vehicle", self.vehicle_actor),
            ):
                inputs = self._tensor(policy_observations[role])
                logits = actor(inputs)
                distribution = masked_categorical(
                    logits,
                    torch.as_tensor(
                        masks[role], dtype=torch.bool, device=self.device
                    ),
                )
                action_tensor = torch.as_tensor(
                    actions[role], dtype=torch.long, device=self.device
                )
                results[role] = (
                    distribution.log_prob(action_tensor)
                    .detach()
                    .cpu()
                    .numpy()
                    .astype(np.float32)
                )
            return results

    def value(self, state: Any) -> torch.Tensor:
        return self.critic(self._tensor(_vector(state)))

    def normalize_returns(self, values: Any, *, update: bool) -> np.ndarray:
        array = np.asarray(values, dtype=np.float32).reshape(-1, 1)
        if not self.stability_components["return_normalization"]:
            return array.reshape(-1)
        return self.return_normalizer.normalize(array, update=update).reshape(-1)

    def normalizer_state_bytes(self) -> bytes:
        state = {
            "uav": self.uav_normalizer.state_dict(),
            "vehicle": self.vehicle_normalizer.state_dict(),
            "return": self.return_normalizer.state_dict(),
        }
        return pickle.dumps(state, protocol=5)

    def state_dict(self) -> dict[str, Any]:
        return {
            "uav_actor": self.uav_actor.state_dict(),
            "vehicle_actor": self.vehicle_actor.state_dict(),
            "critic": self.critic.state_dict(),
            "uav_normalizer": self.uav_normalizer.state_dict(),
            "vehicle_normalizer": self.vehicle_normalizer.state_dict(),
            "return_normalizer": self.return_normalizer.state_dict(),
            "stability_components": dict(self.stability_components),
            "training": self.training,
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        self.uav_actor.load_state_dict(state["uav_actor"])
        self.vehicle_actor.load_state_dict(state["vehicle_actor"])
        self.critic.load_state_dict(state["critic"])
        self.uav_normalizer.load_state_dict(state["uav_normalizer"])
        self.vehicle_normalizer.load_state_dict(state["vehicle_normalizer"])
        self.return_normalizer.load_state_dict(state["return_normalizer"])
        self.stability_components = dict(state["stability_components"])
        self.train(bool(state.get("training", True)))


__all__ = ["SRMAPPOAlgorithm"]
