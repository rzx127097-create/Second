"""MADDPG critics, actor updates, and target-network state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

import torch
import numpy as np
from torch import Tensor

from .networks import masked_straight_through_gumbel


class MADDPGTrainer:
    def __init__(self, algorithm: Any, *, actor_lr: float, critic_lr: float, discount: float, tau: float, batch_size: int) -> None:
        self.algorithm = algorithm
        self.discount = self._positive_float(discount, "discount")
        self.tau = self._positive_float(tau, "tau")
        if self.tau > 1.0:
            raise ValueError("tau must not exceed one")
        self.batch_size = self._positive_int(batch_size, "batch_size")
        actor_lr = self._positive_float(actor_lr, "actor_lr")
        critic_lr = self._positive_float(critic_lr, "critic_lr")
        self.actor_optimizers = {
            "uav": torch.optim.Adam(algorithm.uav_actor.parameters(), lr=actor_lr),
            "vehicle": torch.optim.Adam(algorithm.vehicle_actor.parameters(), lr=actor_lr),
        }
        self.critic_optimizers = {
            "uav": torch.optim.Adam(algorithm.uav_critic.parameters(), lr=critic_lr),
            "vehicle": torch.optim.Adam(algorithm.vehicle_critic.parameters(), lr=critic_lr),
        }
        self.gumbel_temperature = 1.0
        self.update_count = 0
        self.target_update_count = 0
        algorithm._trainer = self

    @staticmethod
    def _positive_float(value: Any, name: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be finite and positive")
        result = float(value)
        if not torch.isfinite(torch.tensor(result)) or result <= 0.0:
            raise ValueError(f"{name} must be finite and positive")
        return result

    @staticmethod
    def _positive_int(value: Any, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return int(value)

    def _tensor(self, values: Any) -> Tensor:
        return torch.as_tensor(np.asarray(values), dtype=torch.float32, device=self.algorithm.device)

    def _batch_tensors(self, rows: Sequence[Any]) -> dict[str, Tensor]:
        if not rows:
            raise ValueError("MADDPG update requires at least one replay row")
        if any(row.__class__.__name__ != "OffPolicyEnvelope" for row in rows):
            raise TypeError("MADDPG replay rows must be off-policy envelopes")
        return {
            "state": self._tensor([row.critic_state for row in rows]),
            "next_state": self._tensor([row.next_critic_state for row in rows]),
            "uav_obs": self._tensor([row.role_batch.observations["uav"] for row in rows]),
            "vehicle_obs": self._tensor([row.role_batch.observations["vehicle"] for row in rows]),
            "next_uav_obs": self._tensor([row.role_batch.next_observations["uav"] for row in rows]),
            "next_vehicle_obs": self._tensor([row.role_batch.next_observations["vehicle"] for row in rows]),
            "uav_mask": torch.as_tensor(np.asarray([row.role_batch.masks["uav"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "vehicle_mask": torch.as_tensor(np.asarray([row.role_batch.masks["vehicle"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "next_uav_mask": torch.as_tensor(np.asarray([row.role_batch.next_masks["uav"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "next_vehicle_mask": torch.as_tensor(np.asarray([row.role_batch.next_masks["vehicle"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "uav_action": torch.nn.functional.one_hot(torch.as_tensor(np.asarray([row.role_batch.actions["uav"] for row in rows]), dtype=torch.long, device=self.algorithm.device), num_classes=self.algorithm.uav_action_dim).float(),
            "vehicle_action": torch.nn.functional.one_hot(torch.as_tensor(np.asarray([row.role_batch.actions["vehicle"] for row in rows]), dtype=torch.long, device=self.algorithm.device), num_classes=self.algorithm.vehicle_action_dim).float(),
            "reward": self._tensor([row.team_reward for row in rows]),
            "done": self._tensor([row.role_batch.terminated or row.role_batch.truncated for row in rows]),
            "valid": torch.as_tensor([row.valid_sample for row in rows], dtype=torch.bool, device=self.algorithm.device),
            "uav_valid": torch.as_tensor(np.asarray([row.valid_actor_sample["uav"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "vehicle_valid": torch.as_tensor(np.asarray([row.valid_actor_sample["vehicle"] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
        }

    def _target_actions(self, tensors: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
        with torch.no_grad():
            uav_logits = self.algorithm.uav_target_actor(tensors["next_uav_obs"])
            vehicle_logits = self.algorithm.vehicle_target_actor(tensors["next_vehicle_obs"])
            uav = torch.softmax(uav_logits.masked_fill(~tensors["next_uav_mask"], float("-inf")), dim=-1)
            vehicle = torch.softmax(vehicle_logits.masked_fill(~tensors["next_vehicle_mask"], float("-inf")), dim=-1)
        return uav, vehicle

    def update_role(self, role: str, rows: Sequence[Any]) -> dict[str, float | str]:
        if role not in ("uav", "vehicle"):
            raise ValueError("MADDPG role must be uav or vehicle")
        tensors = self._batch_tensors(rows)
        valid = tensors["valid"] & tensors[f"{role}_valid"].all(dim=-1)
        if not valid.any():
            return {"role": role, "critic_loss": 0.0, "actor_loss": 0.0}
        tensors = {key: value[valid] if value.ndim > 0 and value.shape[0] == valid.shape[0] else value for key, value in tensors.items()}
        critic = self.algorithm.uav_critic if role == "uav" else self.algorithm.vehicle_critic
        critic_optimizer = self.critic_optimizers[role]
        target_actions = self._target_actions(tensors)
        target_q = (self.algorithm.uav_target_critic if role == "uav" else self.algorithm.vehicle_target_critic)(
            tensors["next_state"], target_actions[0], target_actions[1]
        )
        target = tensors["reward"] + self.discount * (1.0 - tensors["done"]) * target_q
        current_q = critic(tensors["state"], tensors["uav_action"], tensors["vehicle_action"])
        critic_loss = torch.nn.functional.mse_loss(current_q, target.detach())
        if not torch.isfinite(critic_loss):
            raise FloatingPointError("MADDPG critic loss is non-finite")
        critic_optimizer.zero_grad(set_to_none=True)
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(critic.parameters(), 10.0)
        critic_optimizer.step()

        actor = self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor
        actor_optimizer = self.actor_optimizers[role]
        uav_action = tensors["uav_action"].detach()
        vehicle_action = tensors["vehicle_action"].detach()
        if role == "uav":
            uav_action = masked_straight_through_gumbel(
                actor(tensors["uav_obs"]), tensors["uav_mask"], self.gumbel_temperature
            )
        else:
            vehicle_action = masked_straight_through_gumbel(
                actor(tensors["vehicle_obs"]), tensors["vehicle_mask"], self.gumbel_temperature
            )
        actor_loss = -critic(tensors["state"], uav_action, vehicle_action).mean()
        if not torch.isfinite(actor_loss):
            raise FloatingPointError("MADDPG actor loss is non-finite")
        actor_optimizer.zero_grad(set_to_none=True)
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), 10.0)
        actor_optimizer.step()
        self._soft_update(role)
        return {
            "role": role,
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
        }

    def _soft_update(self, role: str) -> None:
        actor = self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor
        target_actor = self.algorithm.uav_target_actor if role == "uav" else self.algorithm.vehicle_target_actor
        critic = self.algorithm.uav_critic if role == "uav" else self.algorithm.vehicle_critic
        target_critic = self.algorithm.uav_target_critic if role == "uav" else self.algorithm.vehicle_target_critic
        with torch.no_grad():
            for target, source in zip(target_actor.parameters(), actor.parameters()):
                target.mul_(1.0 - self.tau).add_(source, alpha=self.tau)
            for target, source in zip(target_critic.parameters(), critic.parameters()):
                target.mul_(1.0 - self.tau).add_(source, alpha=self.tau)
        self.target_update_count += 1

    def update(self, rows: Sequence[Any]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        for role in ("uav", "vehicle"):
            result = self.update_role(role, rows)
            metrics[f"{role}_critic_loss"] = float(result["critic_loss"])
            metrics[f"{role}_actor_loss"] = float(result["actor_loss"])
        self.update_count += 1
        metrics["updates"] = float(self.update_count)
        return metrics

    def validate_state(self, state: Mapping[str, Any]) -> None:
        expected = {"schema_version", "actor_optimizers", "critic_optimizers", "discount", "tau", "batch_size", "gumbel_temperature", "update_count", "target_update_count"}
        if not isinstance(state, Mapping) or set(state) != expected or state.get("schema_version") != "g5-maddpg-trainer-v1":
            raise ValueError("invalid MADDPG trainer state schema")
        if state["discount"] != self.discount or state["tau"] != self.tau or state["batch_size"] != self.batch_size:
            raise ValueError("MADDPG trainer frozen configuration drift")
        for name in ("update_count", "target_update_count"):
            if isinstance(state[name], bool) or not isinstance(state[name], int) or state[name] < 0:
                raise ValueError(f"MADDPG {name} must be a nonnegative integer")
        temperature = float(state["gumbel_temperature"])
        if temperature <= 0.0 or not torch.isfinite(torch.tensor(temperature)):
            raise ValueError("MADDPG Gumbel temperature must be positive and finite")
        if not isinstance(state["actor_optimizers"], Mapping) or set(state["actor_optimizers"]) != {"uav", "vehicle"}:
            raise ValueError("MADDPG actor optimizer state is incomplete")
        if not isinstance(state["critic_optimizers"], Mapping) or set(state["critic_optimizers"]) != {"uav", "vehicle"}:
            raise ValueError("MADDPG critic optimizer state is incomplete")
        try:
            for role, optimizer in self.actor_optimizers.items():
                temporary = torch.optim.Adam(
                    (self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor).parameters(),
                    lr=optimizer.param_groups[0]["lr"],
                )
                temporary.load_state_dict(deepcopy(state["actor_optimizers"][role]))
            for role, optimizer in self.critic_optimizers.items():
                temporary = torch.optim.Adam(
                    (self.algorithm.uav_critic if role == "uav" else self.algorithm.vehicle_critic).parameters(),
                    lr=optimizer.param_groups[0]["lr"],
                )
                temporary.load_state_dict(deepcopy(state["critic_optimizers"][role]))
        except (TypeError, ValueError, RuntimeError) as error:
            raise ValueError("MADDPG optimizer state is invalid") from error

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "g5-maddpg-trainer-v1",
            "actor_optimizers": {role: deepcopy(optimizer.state_dict()) for role, optimizer in self.actor_optimizers.items()},
            "critic_optimizers": {role: deepcopy(optimizer.state_dict()) for role, optimizer in self.critic_optimizers.items()},
            "discount": self.discount,
            "tau": self.tau,
            "batch_size": self.batch_size,
            "gumbel_temperature": self.gumbel_temperature,
            "update_count": self.update_count,
            "target_update_count": self.target_update_count,
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        self.validate_state(state)
        for role, optimizer in self.actor_optimizers.items():
            optimizer.load_state_dict(deepcopy(state["actor_optimizers"][role]))
        for role, optimizer in self.critic_optimizers.items():
            optimizer.load_state_dict(deepcopy(state["critic_optimizers"][role]))
        self.gumbel_temperature = float(state["gumbel_temperature"])
        self.update_count = int(state["update_count"])
        self.target_update_count = int(state["target_update_count"])


__all__ = ["MADDPGTrainer"]
