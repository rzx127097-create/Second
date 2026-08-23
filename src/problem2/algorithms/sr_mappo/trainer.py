"""Role-isolated PPO optimization for heterogeneous SR-MAPPO."""

from __future__ import annotations

import copy
from numbers import Real
from collections.abc import Mapping
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
        minibatch_size: int | None = None,
        clip_radius: float = 0.2,
    ) -> None:
        self.algorithm = algorithm
        self.value_coef = float(value_coef)
        self.entropy_coef = float(entropy_coef)
        self.max_grad_norm = float(max_grad_norm)
        self.clip_radius = float(clip_radius)
        if not np.isfinite(self.clip_radius) or self.clip_radius <= 0.0:
            raise ValueError("clip_radius must be positive and finite")
        if minibatch_size is not None and (
            isinstance(minibatch_size, bool)
            or not isinstance(minibatch_size, int)
            or minibatch_size <= 0
        ):
            raise ValueError("minibatch_size must be a positive integer")
        self.minibatch_size = minibatch_size
        self._rng = np.random.default_rng(0)
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

    def _minibatches(self, indices: np.ndarray, size: int | None) -> list[np.ndarray]:
        if indices.size == 0:
            return []
        indices = self._rng.permutation(indices)
        width = indices.size if size is None else size
        return [indices[start : start + width] for start in range(0, indices.size, width)]

    def _update_critic(
        self,
        batch: Any,
        *,
        sample_indices: np.ndarray | None = None,
        update_normalizer: bool = True,
    ) -> tuple[float, int]:
        team_valid = np.asarray(
            [
                bool(record.get("valid_sample", record.get("valid", True)))
                for record in batch.transitions
            ],
            dtype=bool,
        )
        if not team_valid.any():
            raise ValueError("at least one team-valid sample is required")
        selected = (
            np.flatnonzero(team_valid)
            if sample_indices is None
            else np.asarray(sample_indices, dtype=np.int64)
        )
        if selected.size == 0 or not team_valid[selected].all():
            raise ValueError("critic minibatch must contain team-valid samples")
        states = torch.as_tensor(
            np.asarray(
                [record["critic_state"] for record in batch.transitions],
                dtype=np.float32,
            )[selected],
            dtype=torch.float32,
            device=self.algorithm.device,
        )
        returns_physical = np.asarray(batch.returns, dtype=np.float32)[selected]
        normalized_returns = self.algorithm.normalize_returns(
            returns_physical, update=update_normalizer
        )
        returns = torch.as_tensor(
            normalized_returns, dtype=torch.float32, device=self.algorithm.device
        )
        old_values = self.algorithm.normalize_returns(
            np.asarray(
                [record["value"] for record in batch.transitions], dtype=np.float32
            )[selected],
            update=False,
        )
        old_values_tensor = torch.as_tensor(
            old_values, dtype=torch.float32, device=self.algorithm.device
        )
        predicted = self.algorithm.normalize_return_tensor(
            self.algorithm.critic(states)
        )
        loss = value_loss(
            predicted,
            old_values_tensor,
            returns,
            clip=bool(self.algorithm.stability_components["value_clipping"]),
            clip_epsilon=self.clip_radius,
            huber_delta=(
                1.0
                if self.algorithm.stability_components["huber_value_loss"]
                else None
            ),
        ) * self.value_coef
        optimizer = self.optimizers["critic"]
        if not torch.isfinite(loss):
            raise FloatingPointError("critic loss is not finite")
        optimizer.zero_grad()
        loss.backward()
        if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all() for parameter in self.algorithm.critic.parameters()):
            optimizer.zero_grad()
            raise FloatingPointError("critic gradients are not finite")
        torch.nn.utils.clip_grad_norm_(
            self.algorithm.critic.parameters(), self.max_grad_norm
        )
        optimizer.step()
        return float(loss.detach().cpu()), int(selected.size)

    def _update_actor(
        self,
        batch: Any,
        role: str,
        *,
        sample_indices: np.ndarray | None = None,
    ) -> tuple[float, float, int]:
        rows = self._role_rows(batch, role)
        valid_indices = np.flatnonzero(rows["valid"])
        selected = (
            valid_indices
            if sample_indices is None
            else np.asarray(sample_indices, dtype=np.int64)
        )
        if selected.size == 0 or not rows["valid"][selected].all():
            return 0.0, 0.0, 0
        observation = torch.as_tensor(
            rows["observations"][selected],
            dtype=torch.float32,
            device=self.algorithm.device,
        )
        masks = torch.as_tensor(
            rows["masks"][selected], dtype=torch.bool, device=self.algorithm.device
        )
        actions = torch.as_tensor(
            rows["actions"][selected], dtype=torch.long, device=self.algorithm.device
        )
        old_log_probs = torch.as_tensor(
            rows["old_log_probs"][selected],
            dtype=torch.float32,
            device=self.algorithm.device,
        )
        advantages = torch.as_tensor(
            rows["advantages"][selected],
            dtype=torch.float32,
            device=self.algorithm.device,
        )
        actor = self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor
        distribution = masked_categorical(actor(observation), masks)
        new_log_probs = distribution.log_prob(actions)
        policy_loss = ppo_policy_loss(
            new_log_probs,
            old_log_probs,
            advantages,
            clip_epsilon=self.clip_radius,
        )
        entropy = entropy_bonus(distribution.entropy())
        loss = policy_loss - self.entropy_coef * entropy
        optimizer = self.optimizers[role]
        if not torch.isfinite(loss):
            raise FloatingPointError(f"{role} actor loss is not finite")
        optimizer.zero_grad()
        loss.backward()
        if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all() for parameter in actor.parameters()):
            optimizer.zero_grad()
            raise FloatingPointError(f"{role} actor gradients are not finite")
        torch.nn.utils.clip_grad_norm_(actor.parameters(), self.max_grad_norm)
        optimizer.step()
        return (
            float(policy_loss.detach().cpu()),
            float(entropy.detach().cpu()),
            int(selected.size),
        )

    def _update_impl(
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
        totals = {"critic_loss": [0.0, 0], "uav_policy_loss": [0.0, 0], "uav_entropy": [0.0, 0], "vehicle_policy_loss": [0.0, 0], "vehicle_entropy": [0.0, 0]}
        team_valid = np.asarray(
            [
                bool(record.get("valid_sample", record.get("valid", True)))
                for record in batch.transitions
            ],
            dtype=bool,
        )
        critic_indices = np.flatnonzero(team_valid)
        if not critic_indices.size:
            raise ValueError("at least one team-valid sample is required")
        self.algorithm.normalize_returns(
            np.asarray(batch.returns, dtype=np.float32)[critic_indices],
            update=True,
        )
        role_indices = {
            role: np.flatnonzero(self._role_rows(batch, role)["valid"])
            for role in ("uav", "vehicle")
        }
        metrics["critic_valid_samples"] = int(critic_indices.size)
        for role, indices in role_indices.items():
            metrics[f"{role}_valid_samples"] = int(indices.size)
        for _ in range(int(epochs)):
            for indices in self._minibatches(critic_indices, self.minibatch_size):
                metrics["critic_loss"], _ = self._update_critic(
                    batch,
                    sample_indices=indices,
                    update_normalizer=False,
                )
                metrics["critic_updates"] += 1
                totals["critic_loss"][0] += metrics["critic_loss"] * len(indices); totals["critic_loss"][1] += len(indices)
            for role in ("uav", "vehicle"):
                for indices in self._minibatches(
                    role_indices[role], self.minibatch_size
                ):
                    policy_loss, entropy, valid_count = self._update_actor(
                        batch, role, sample_indices=indices
                    )
                    metrics[f"{role}_policy_loss"] = policy_loss
                    metrics[f"{role}_entropy"] = entropy
                    if not valid_count:
                        continue
                    metrics[f"{role}_actor_updates"] += 1
                    totals[f"{role}_policy_loss"][0] += policy_loss * valid_count; totals[f"{role}_policy_loss"][1] += valid_count
                    totals[f"{role}_entropy"][0] += entropy * valid_count; totals[f"{role}_entropy"][1] += valid_count
        for name, (total, count) in totals.items():
            if count:
                metrics[name] = total / count
        if progress is not None:
            self.step_scheduler(progress)
            metrics["learning_rates"] = self.learning_rates()
        return metrics

    def update(
        self,
        batch: Any,
        *,
        epochs: int = 1,
        progress: float | None = None,
    ) -> dict[str, Any]:
        snapshot = copy.deepcopy(self.algorithm.state_dict())
        try:
            return self._update_impl(batch, epochs=epochs, progress=progress)
        except Exception:
            self.algorithm.load_state_dict(snapshot)
            raise

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
            "clip_radius": self.clip_radius,
            "minibatch_size": self.minibatch_size,
            "lr_decay": self.lr_decay,
            "rng_state": self._rng.bit_generator.state,
        }

    def validate_state(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise ValueError("trainer state must be a mapping")
        required = {"optimizers", "schedulers", "value_coef", "entropy_coef", "max_grad_norm", "clip_radius", "minibatch_size", "lr_decay", "rng_state"}
        if self.algorithm.training_config and set(state) != required:
            raise ValueError("invalid G5 centralized trainer state schema")
        for name in ("value_coef", "entropy_coef", "max_grad_norm", "clip_radius"):
            value = state.get(name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
                raise ValueError(f"frozen trainer scalar must be finite real: {name}")
            if (name in {"value_coef", "entropy_coef"} and value < 0.0) or (name in {"max_grad_norm", "clip_radius"} and value <= 0.0):
                raise ValueError(f"frozen trainer scalar is outside its domain: {name}")
            if value != getattr(self, name):
                raise ValueError(f"frozen trainer field drift: {name}")
        minibatch_size = state.get("minibatch_size")
        if minibatch_size is not None and (type(minibatch_size) is not int or minibatch_size <= 0):
            raise ValueError("minibatch_size must be None or a positive built-in integer")
        if minibatch_size != self.minibatch_size:
            raise ValueError("frozen trainer field drift: minibatch_size")
        if type(state.get("lr_decay")) is not bool:
            raise ValueError("lr_decay must be a built-in boolean")
        if state["lr_decay"] != self.lr_decay:
            raise ValueError("frozen trainer field drift: lr_decay")
        for name, expected_roles in (("optimizers", set(self.optimizers)), ("schedulers", set(self.schedulers))):
            section = state.get(name)
            if not isinstance(section, Mapping) or set(section) != expected_roles:
                raise ValueError(f"trainer {name} must contain exact role keys")
        rng = np.random.default_rng()
        try:
            rng.bit_generator.state = copy.deepcopy(state["rng_state"])
            for role, optimizer_state in state["optimizers"].items():
                copy.deepcopy(self.optimizers[role]).load_state_dict(copy.deepcopy(optimizer_state))
            for role, scheduler_state in state["schedulers"].items():
                copy.deepcopy(self.schedulers[role]).load_state_dict(copy.deepcopy(scheduler_state))
        except Exception as error:
            raise ValueError("invalid trainer optimizer, scheduler, or RNG state") from error

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        self.validate_state(state)
        self.value_coef = float(state["value_coef"])
        self.entropy_coef = float(state["entropy_coef"])
        self.max_grad_norm = float(state["max_grad_norm"])
        self.clip_radius = float(state["clip_radius"])
        self.minibatch_size = state["minibatch_size"]
        self.lr_decay = bool(state["lr_decay"])
        self._rng.bit_generator.state = copy.deepcopy(state["rng_state"])
        for role, optimizer_state in state["optimizers"].items():
            self.optimizers[role].load_state_dict(optimizer_state)
        for role, scheduler_state in state["schedulers"].items():
            self.schedulers[role].load_state_dict(scheduler_state)


__all__ = ["LinearDecayScheduler", "SRMAPPOTrainer"]
