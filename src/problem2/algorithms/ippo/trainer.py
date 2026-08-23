"""Role-local GAE storage and PPO updates for the IPPO comparison."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from numbers import Real
from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.gae import compute_gae
from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.sr_mappo.losses import entropy_bonus, ppo_policy_loss


ROLES = ("uav", "vehicle")


def _role_arrays(value: Mapping[str, Any], name: str) -> dict[str, np.ndarray]:
    if not isinstance(value, Mapping) or set(value) != set(ROLES):
        raise ValueError(f"{name} must contain exactly the roles {ROLES}")
    arrays = {
        role: np.asarray(value[role], dtype=np.float32).reshape(-1).copy()
        for role in ROLES
    }
    if any(array.size == 0 or not np.isfinite(array).all() for array in arrays.values()):
        raise ValueError(f"{name} must contain finite role values")
    return arrays


class RoleLocalRolloutBatch:
    """A shared-reward rollout with one value trajectory per role-local agent."""

    def __init__(self) -> None:
        self.transitions: list[dict[str, Any]] = []
        self.advantages: dict[str, np.ndarray] = {}
        self.returns: dict[str, np.ndarray] = {}
        self.normalized_advantages: dict[str, np.ndarray] = {}
        self.finished = False

    def __len__(self) -> int:
        return len(self.transitions)

    def add(
        self,
        *,
        reward: float,
        values: Mapping[str, Any],
        next_values: Mapping[str, Any],
        terminated: bool,
        truncated: bool,
        observations: Mapping[str, Any] | None = None,
        masks: Mapping[str, Any] | None = None,
        actions: Mapping[str, Any] | None = None,
        old_log_probs: Mapping[str, Any] | None = None,
        valid_actor_sample: Mapping[str, Any] | None = None,
        valid_sample: bool = True,
    ) -> None:
        reward_value = float(reward)
        if not np.isfinite(reward_value):
            raise ValueError("reward must be finite")
        role_values = _role_arrays(values, "values")
        role_next_values = _role_arrays(next_values, "next_values")
        for role in ROLES:
            if role_values[role].shape != role_next_values[role].shape:
                raise ValueError(f"{role} value widths must match")
            if self.transitions and role_values[role].shape != self.transitions[0]["values"][role].shape:
                raise ValueError(f"{role} value width changed within the rollout")
        if bool(terminated) and bool(truncated):
            raise ValueError("a transition cannot be both terminated and truncated")
        if not isinstance(valid_sample, (bool, np.bool_)):
            raise ValueError("valid_sample must be a boolean")
        policy_fields = (observations, masks, actions, old_log_probs)
        if any(item is not None for item in policy_fields) and not all(
            item is not None for item in policy_fields
        ):
            raise ValueError("policy replay fields must be supplied together")
        record: dict[str, Any] = {
            "reward": reward_value,
            "values": role_values,
            "next_values": role_next_values,
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "valid_sample": bool(valid_sample),
            "valid_actor_sample": {},
        }
        raw_validity = dict(valid_actor_sample or {})
        if raw_validity and set(raw_validity) != set(ROLES):
            raise ValueError(f"valid_actor_sample must contain exactly the roles {ROLES}")
        for role in ROLES:
            raw_value = raw_validity.get(
                role, np.ones(role_values[role].shape, dtype=bool)
            )
            validity = np.asarray(raw_value)
            if validity.dtype != np.bool_:
                raise ValueError(f"{role} valid_actor_sample must have boolean dtype")
            validity = validity.reshape(-1)
            if validity.shape != role_values[role].shape:
                raise ValueError(f"{role} validity width must match local values")
            record["valid_actor_sample"][role] = validity.copy()
        if observations is not None:
            record.update(
                {
                    "observations": copy.deepcopy(dict(observations)),
                    "masks": copy.deepcopy(dict(masks or {})),
                    "actions": copy.deepcopy(dict(actions or {})),
                    "old_log_probs": copy.deepcopy(dict(old_log_probs or {})),
                }
            )
        self.transitions.append(record)
        self.finished = False

    def finish(
        self, gamma: float, gae_lambda: float
    ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        if not self.transitions:
            raise ValueError("role-local rollout must contain transitions")
        rewards = np.asarray(
            [record["reward"] for record in self.transitions], dtype=np.float64
        )
        terminated = np.asarray(
            [record["terminated"] for record in self.transitions], dtype=bool
        )
        truncated = np.asarray(
            [record["truncated"] for record in self.transitions], dtype=bool
        )
        self.advantages = {}
        self.returns = {}
        for role in ROLES:
            values = np.stack(
                [record["values"][role] for record in self.transitions]
            ).astype(np.float64)
            next_values = np.stack(
                [record["next_values"][role] for record in self.transitions]
            ).astype(np.float64)
            role_advantages = np.empty_like(values, dtype=np.float32)
            role_returns = np.empty_like(values, dtype=np.float32)
            for agent_index in range(values.shape[1]):
                advantages, returns = compute_gae(
                    rewards,
                    values[:, agent_index],
                    terminated,
                    truncated,
                    float(next_values[-1, agent_index]),
                    next_values[:, agent_index],
                    gamma,
                    gae_lambda,
                    np.asarray(
                        [
                            record["valid_sample"]
                            and record["valid_actor_sample"][role][agent_index]
                            for record in self.transitions
                        ],
                        dtype=bool,
                    ),
                )
                role_advantages[:, agent_index] = advantages
                role_returns[:, agent_index] = returns
            self.advantages[role] = role_advantages
            self.returns[role] = role_returns
        self.finished = True
        return self.advantages, self.returns

    def normalize_advantages(self) -> dict[str, np.ndarray]:
        if not self.finished:
            raise RuntimeError("finish must be called before normalizing advantages")
        self.normalized_advantages = {}
        for role, values in self.advantages.items():
            valid = np.stack(
                [record["valid_actor_sample"][role] for record in self.transitions]
            ).astype(bool) & np.asarray(
                [record["valid_sample"] for record in self.transitions], dtype=bool
            )[:, None]
            if not valid.any():
                raise ValueError(f"at least one valid {role} sample is required")
            population = values.astype(np.float64)[valid]
            normalized = (
                (values.astype(np.float64) - population.mean())
                / max(population.std(), np.finfo(np.float64).eps)
            ).astype(np.float32)
            self.normalized_advantages[role] = normalized
        return self.normalized_advantages

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "g5-role-local-rollout-v1",
            "transitions": copy.deepcopy(self.transitions),
            "advantages": copy.deepcopy(self.advantages),
            "returns": copy.deepcopy(self.returns),
            "normalized_advantages": copy.deepcopy(self.normalized_advantages),
            "finished": self.finished,
        }

    @classmethod
    def from_state_dict(cls, state: Mapping[str, Any]) -> "RoleLocalRolloutBatch":
        if not isinstance(state, Mapping) or state.get("schema_version") != "g5-role-local-rollout-v1":
            raise ValueError("unsupported role-local rollout schema")
        batch = cls()
        batch.transitions = copy.deepcopy(list(state.get("transitions", [])))
        batch.advantages = {
            role: np.asarray(values, dtype=np.float32).copy()
            for role, values in dict(state.get("advantages", {})).items()
        }
        batch.returns = {
            role: np.asarray(values, dtype=np.float32).copy()
            for role, values in dict(state.get("returns", {})).items()
        }
        batch.normalized_advantages = {
            role: np.asarray(values, dtype=np.float32).copy()
            for role, values in dict(state.get("normalized_advantages", {})).items()
        }
        batch.finished = bool(state.get("finished", False))
        return batch


class IPPOTrainer:
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
            "uav": torch.optim.Adam(
                [
                    *algorithm.uav_actor.parameters(),
                    *algorithm.uav_value.parameters(),
                ],
                lr=learning_rate,
            ),
            "vehicle": torch.optim.Adam(
                [
                    *algorithm.vehicle_actor.parameters(),
                    *algorithm.vehicle_value.parameters(),
                ],
                lr=learning_rate,
            ),
        }
        algorithm._trainer = self

    def _update_impl(self, batch: RoleLocalRolloutBatch, *, epochs: int = 1) -> dict[str, Any]:
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        if not batch.finished:
            raise ValueError("role-local rollout must be finished before update")
        if not all("observations" in record for record in batch.transitions):
            raise ValueError("role-local rollout is missing policy replay fields")
        batch.normalize_advantages()
        metrics: dict[str, Any] = {"uav_actor_updates": 0, "vehicle_actor_updates": 0}
        totals = {
            f"{role}_{name}": [0.0, 0]
            for role in ROLES
            for name in ("policy_loss", "entropy", "value_loss")
        }
        rows: dict[str, dict[str, torch.Tensor]] = {}
        for role in ROLES:
            role_rows = {
                "observations": torch.as_tensor(
                    np.concatenate(
                        [
                            np.asarray(record["observations"][role], dtype=np.float32)
                            for record in batch.transitions
                        ],
                        axis=0,
                    ),
                    dtype=torch.float32,
                    device=self.algorithm.device,
                ),
                "masks": torch.as_tensor(
                    np.concatenate(
                        [
                            np.asarray(record["masks"][role], dtype=bool)
                            for record in batch.transitions
                        ],
                        axis=0,
                    ),
                    dtype=torch.bool,
                    device=self.algorithm.device,
                ),
                "actions": torch.as_tensor(
                    np.concatenate(
                        [
                            np.asarray(record["actions"][role], dtype=np.int64).reshape(-1)
                            for record in batch.transitions
                        ]
                    ),
                    dtype=torch.long,
                    device=self.algorithm.device,
                ),
                "old_log_probs": torch.as_tensor(
                    np.concatenate(
                        [
                            np.asarray(record["old_log_probs"][role], dtype=np.float32).reshape(-1)
                            for record in batch.transitions
                        ]
                    ),
                    dtype=torch.float32,
                    device=self.algorithm.device,
                ),
                "valid": torch.as_tensor(
                    np.concatenate(
                        [
                            np.asarray(record["valid_actor_sample"][role], dtype=bool).reshape(-1)
                            & bool(record["valid_sample"])
                            for record in batch.transitions
                        ]
                    ),
                    dtype=torch.bool,
                    device=self.algorithm.device,
                ),
                "advantages": torch.as_tensor(
                    batch.normalized_advantages[role].reshape(-1),
                    dtype=torch.float32,
                    device=self.algorithm.device,
                ),
                "returns": torch.as_tensor(
                    batch.returns[role].reshape(-1),
                    dtype=torch.float32,
                    device=self.algorithm.device,
                ),
            }
            if not role_rows["valid"].any():
                raise ValueError(f"at least one valid {role} sample is required")
            rows[role] = role_rows
            metrics[f"{role}_valid_samples"] = int(role_rows["valid"].sum().item())

        for _ in range(int(epochs)):
            for role in ROLES:
                role_rows = rows[role]
                valid_indices = torch.nonzero(
                    role_rows["valid"], as_tuple=False
                ).reshape(-1)
                valid_indices = valid_indices[torch.as_tensor(self._rng.permutation(len(valid_indices)), device=self.algorithm.device)]
                width = (
                    len(valid_indices)
                    if self.minibatch_size is None
                    else self.minibatch_size
                )
                for start in range(0, len(valid_indices), width):
                    selected = valid_indices[start : start + width]
                    actor = self.algorithm.uav_actor if role == "uav" else self.algorithm.vehicle_actor
                    value_network = self.algorithm.uav_value if role == "uav" else self.algorithm.vehicle_value
                    distribution = masked_categorical(
                        actor(role_rows["observations"][selected]),
                        role_rows["masks"][selected],
                    )
                    policy_loss = ppo_policy_loss(
                        distribution.log_prob(role_rows["actions"][selected]),
                        role_rows["old_log_probs"][selected],
                        role_rows["advantages"][selected],
                        clip_epsilon=self.clip_radius,
                    )
                    entropy = entropy_bonus(distribution.entropy())
                    predicted_values = value_network(role_rows["observations"][selected])
                    value_loss = 0.5 * torch.square(
                        predicted_values - role_rows["returns"][selected]
                    ).mean()
                    loss = policy_loss - self.entropy_coef * entropy + self.value_coef * value_loss
                    optimizer = self.optimizers[role]
                    if not torch.isfinite(loss):
                        raise FloatingPointError(f"{role} IPPO loss is not finite")
                    optimizer.zero_grad()
                    loss.backward()
                    parameters = [
                        parameter
                        for group in optimizer.param_groups
                        for parameter in group["params"]
                    ]
                    if any(parameter.grad is not None and not torch.isfinite(parameter.grad).all() for parameter in parameters):
                        optimizer.zero_grad()
                        raise FloatingPointError(f"{role} IPPO gradients are not finite")
                    torch.nn.utils.clip_grad_norm_(parameters, self.max_grad_norm)
                    optimizer.step()
                    metrics[f"{role}_actor_updates"] += 1
                    valid_count = int(selected.numel())
                    for name, value in (("policy_loss", policy_loss), ("entropy", entropy), ("value_loss", value_loss)):
                        totals[f"{role}_{name}"][0] += float(value.detach().cpu()) * valid_count
                        totals[f"{role}_{name}"][1] += valid_count
        for name, (total, count) in totals.items():
            if count:
                metrics[name] = total / count
        return metrics

    def update(self, batch: RoleLocalRolloutBatch, *, epochs: int = 1) -> dict[str, Any]:
        snapshot = copy.deepcopy(self.algorithm.state_dict())
        try:
            return self._update_impl(batch, epochs=epochs)
        except Exception:
            self.algorithm.load_state_dict(snapshot)
            raise

    def state_dict(self) -> dict[str, Any]:
        return {
            "optimizers": {
                role: optimizer.state_dict()
                for role, optimizer in self.optimizers.items()
            },
            "value_coef": self.value_coef,
            "entropy_coef": self.entropy_coef,
            "max_grad_norm": self.max_grad_norm,
            "clip_radius": self.clip_radius,
            "rng_state": self._rng.bit_generator.state,
            "minibatch_size": self.minibatch_size,
        }

    def validate_state(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise ValueError("trainer state must be a mapping")
        required = {"optimizers", "value_coef", "entropy_coef", "max_grad_norm", "clip_radius", "rng_state", "minibatch_size"}
        if self.algorithm.training_config and set(state) != required:
            raise ValueError("invalid G5 IPPO trainer state schema")
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
        optimizers = state.get("optimizers")
        if not isinstance(optimizers, Mapping) or set(optimizers) != set(self.optimizers):
            raise ValueError("trainer optimizers must contain exact role keys")
        rng = np.random.default_rng()
        try:
            rng.bit_generator.state = copy.deepcopy(state["rng_state"])
            for role, optimizer_state in optimizers.items():
                copy.deepcopy(self.optimizers[role]).load_state_dict(copy.deepcopy(optimizer_state))
        except Exception as error:
            raise ValueError("invalid trainer optimizer or RNG state") from error

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        self.validate_state(state)
        self.value_coef = float(state["value_coef"])
        self.entropy_coef = float(state["entropy_coef"])
        self.max_grad_norm = float(state["max_grad_norm"])
        self.clip_radius = float(state["clip_radius"])
        self._rng.bit_generator.state = copy.deepcopy(state["rng_state"])
        self.minibatch_size = state["minibatch_size"]
        for role, optimizer_state in state["optimizers"].items():
            self.optimizers[role].load_state_dict(optimizer_state)


__all__ = ["IPPOTrainer", "RoleLocalRolloutBatch"]
