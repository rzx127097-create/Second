"""Role-isolated PPO optimization for heterogeneous SR-MAPPO."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.masked_distribution import masked_categorical

from .losses import entropy_bonus, ppo_policy_loss, value_loss


class LinearDecayScheduler:
    def __init__(self, optimizer: torch.optim.Optimizer) -> None:
        self.optimizer = optimizer
        self.base_lrs = [float(group["lr"]) for group in optimizer.param_groups]
        self.progress = 0.0

    def step(self, progress: float) -> None:
        self.progress = min(1.0, max(0.0, float(progress)))
        for base, group in zip(self.base_lrs, self.optimizer.param_groups):
            group["lr"] = base * (1.0 - self.progress)

    def state_dict(self) -> dict[str, Any]:
        return {"base_lrs": list(self.base_lrs), "progress": self.progress}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.base_lrs = [float(value) for value in state["base_lrs"]]
        self.step(float(state["progress"]))


class SRMAPPOTrainer:
    def __init__(
        self,
        algorithm: Any,
        learning_rate: float = 3e-4,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
    ) -> None:
        self.algorithm = algorithm
        self.value_coef = float(value_coef)
        self.entropy_coef = float(entropy_coef)
        self.max_grad_norm = float(max_grad_norm)
        self.optimizers = {
            "uav": torch.optim.Adam(algorithm.uav_actor.parameters(), lr=learning_rate),
            "vehicle": torch.optim.Adam(
                algorithm.vehicle_actor.parameters(), lr=learning_rate
            ),
            "critic": torch.optim.Adam(algorithm.critic.parameters(), lr=learning_rate),
        }
        self.schedulers = {
            role: LinearDecayScheduler(optimizer)
            for role, optimizer in self.optimizers.items()
        }
        self.lr_decay = bool(
            algorithm.stability_components.get("learning_rate_decay", True)
        )
        algorithm._trainer = self

    def learning_rates(self) -> dict[str, float]:
        return {
            role: float(optimizer.param_groups[0]["lr"])
            for role, optimizer in self.optimizers.items()
        }

    def step_scheduler(self, progress: float) -> None:
        if self.lr_decay:
            for scheduler in self.schedulers.values():
                scheduler.step(progress)

    @staticmethod
    def _role_rows(batch: Any, role: str) -> dict[str, np.ndarray]:
        observations: list[np.ndarray] = []
        masks: list[np.ndarray] = []
        actions: list[int] = []
        old_log_probs: list[float] = []
        valid: list[bool] = []
        advantages: list[float] = []
        normalized_advantages = batch.normalized_advantages
        for index, record in enumerate(batch.transitions):
            obs = np.asarray(record["normalized_policy_observation"][role], dtype=np.float32)
            if obs.ndim == 1:
                obs = obs.reshape(1, -1)
            mask = np.asarray(record["action_mask"][role], dtype=bool)
            if mask.ndim == 1:
                mask = mask.reshape(1, -1)
            action = np.asarray(record["action"][role], dtype=np.int64).reshape(-1)
            old_log_prob = np.asarray(record["old_log_prob"][role], dtype=np.float32).reshape(-1)
            role_valid = np.asarray(record["valid_actor_sample"][role], dtype=bool).reshape(-1)
            if role_valid.size == 1:
                role_valid = np.repeat(role_valid, obs.shape[0])
            team_valid = bool(record.get("valid_sample", record.get("valid", True)))
            role_valid = np.logical_and(role_valid, team_valid)
            if not (
                obs.shape[0]
                == mask.shape[0]
                == action.size
                == old_log_prob.size
                == role_valid.size
            ):
                raise ValueError(f"role {role} transition widths do not match")
            observations.append(obs)
            masks.append(mask)
            actions.extend(action.tolist())
            old_log_probs.extend(old_log_prob.tolist())
            valid.extend(role_valid.tolist())
            advantages.extend([float(normalized_advantages[index])] * obs.shape[0])
        return {
            "observations": np.concatenate(observations, axis=0),
            "masks": np.concatenate(masks, axis=0),
            "actions": np.asarray(actions, dtype=np.int64),
            "old_log_probs": np.asarray(old_log_probs, dtype=np.float32),
            "valid": np.asarray(valid, dtype=bool),
            "advantages": np.asarray(advantages, dtype=np.float32),
        }

    def _update_critic(self, batch: Any) -> tuple[float, int]:
        team_valid = np.asarray(
            [
                bool(record.get("valid_sample", record.get("valid", True)))
                for record in batch.transitions
            ],
            dtype=bool,
        )
        if not team_valid.any():
            raise ValueError("at least one team-valid sample is required")
        states = torch.as_tensor(
            np.asarray(
                [record["critic_state"] for record in batch.transitions],
                dtype=np.float32,
            )[team_valid],
            dtype=torch.float32,
            device=self.algorithm.device,
        )
        returns_physical = np.asarray(batch.returns, dtype=np.float32)[team_valid]
        normalized_returns = self.algorithm.normalize_returns(
            returns_physical, update=True
        )
        returns = torch.as_tensor(
            normalized_returns, dtype=torch.float32, device=self.algorithm.device
        )
        old_values = self.algorithm.normalize_returns(
            np.asarray(
                [record["value"] for record in batch.transitions], dtype=np.float32
            )[team_valid],
            update=False,
        )
        old_values_tensor = torch.as_tensor(
            old_values, dtype=torch.float32, device=self.algorithm.device
        )
        predicted = self.algorithm.critic(states)
        loss = value_loss(
            predicted,
            old_values_tensor,
            returns,
            clip=bool(self.algorithm.stability_components["value_clipping"]),
            huber_delta=(
                1.0
                if self.algorithm.stability_components["huber_value_loss"]
                else None
            ),
        ) * self.value_coef
        optimizer = self.optimizers["critic"]
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            self.algorithm.critic.parameters(), self.max_grad_norm
        )
        optimizer.step()
        if not torch.isfinite(loss):
            raise FloatingPointError("critic loss is not finite")
        return float(loss.detach().cpu()), int(team_valid.sum())

    def _update_actor(self, batch: Any, role: str) -> tuple[float, float, int]:
        rows = self._role_rows(batch, role)
        observation = torch.as_tensor(
            rows["observations"], dtype=torch.float32, device=self.algorithm.device
        )
        masks = torch.as_tensor(
            rows["masks"], dtype=torch.bool, device=self.algorithm.device
        )
        actions = torch.as_tensor(
            rows["actions"], dtype=torch.long, device=self.algorithm.device
        )
        old_log_probs = torch.as_tensor(
            rows["old_log_probs"], dtype=torch.float32, device=self.algorithm.device
        )
        advantages = torch.as_tensor(
            rows["advantages"], dtype=torch.float32, device=self.algorithm.device
        )
        valid = torch.as_tensor(
            rows["valid"], dtype=torch.bool, device=self.algorithm.device
        )
        actor = self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor
        distribution = masked_categorical(actor(observation), masks)
        new_log_probs = distribution.log_prob(actions)
        if not valid.any():
            return 0.0, 0.0, 0
        policy_loss = ppo_policy_loss(
            new_log_probs[valid],
            old_log_probs[valid],
            advantages[valid],
        )
        entropy = entropy_bonus(distribution.entropy()[valid])
        loss = policy_loss - self.entropy_coef * entropy
        optimizer = self.optimizers[role]
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), self.max_grad_norm)
        optimizer.step()
        if not torch.isfinite(loss):
            raise FloatingPointError(f"{role} actor loss is not finite")
        return (
            float(policy_loss.detach().cpu()),
            float(entropy.detach().cpu()),
            int(valid.sum().item()),
        )

    def update(
        self,
        batch: Any,
        *,
        epochs: int = 1,
        progress: float | None = None,
    ) -> dict[str, Any]:
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        if batch.advantages.size == 0 or batch.returns.size == 0:
            raise ValueError("rollout must be finished before update")
        batch.normalize_advantages()
        metrics: dict[str, Any] = {
            "critic_updates": 0,
            "uav_actor_updates": 0,
            "vehicle_actor_updates": 0,
            "critic_valid_samples": 0,
            "uav_valid_samples": 0,
            "vehicle_valid_samples": 0,
        }
        for _ in range(int(epochs)):
            metrics["critic_loss"], metrics["critic_valid_samples"] = self._update_critic(
                batch
            )
            metrics["critic_updates"] += 1
            for role in ("uav", "vehicle"):
                policy_loss, entropy, valid_count = self._update_actor(batch, role)
                metrics[f"{role}_policy_loss"] = policy_loss
                metrics[f"{role}_entropy"] = entropy
                metrics[f"{role}_valid_samples"] = valid_count
                if valid_count:
                    metrics[f"{role}_actor_updates"] += 1
                    metrics[f"{role}_valid_samples"] = valid_count
        if progress is not None:
            self.step_scheduler(progress)
            metrics["learning_rates"] = self.learning_rates()
        return metrics

    def state_dict(self) -> dict[str, Any]:
        return {
            "optimizers": {
                role: optimizer.state_dict()
                for role, optimizer in self.optimizers.items()
            },
            "schedulers": {
                role: scheduler.state_dict()
                for role, scheduler in self.schedulers.items()
            },
            "value_coef": self.value_coef,
            "entropy_coef": self.entropy_coef,
            "max_grad_norm": self.max_grad_norm,
            "lr_decay": self.lr_decay,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.value_coef = float(state["value_coef"])
        self.entropy_coef = float(state["entropy_coef"])
        self.max_grad_norm = float(state["max_grad_norm"])
        self.lr_decay = bool(state["lr_decay"])
        for role, optimizer_state in state["optimizers"].items():
            self.optimizers[role].load_state_dict(optimizer_state)
        for role, scheduler_state in state["schedulers"].items():
            self.schedulers[role].load_state_dict(scheduler_state)


__all__ = ["LinearDecayScheduler", "SRMAPPOTrainer"]
