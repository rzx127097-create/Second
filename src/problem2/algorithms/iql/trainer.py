"""IQL role-local TD updates and target-network state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

import torch
import numpy as np
from torch import Tensor

from .networks import masked_bootstrap_max


class IQLTrainer:
    _STATE_SCHEMA_VERSION = "g5-iql-trainer-v1"

    def __init__(self, algorithm: Any, *, learning_rate: float, discount: float, target_update_interval: int, batch_size: int) -> None:
        self.algorithm = algorithm
        self.learning_rate = self._positive_float(learning_rate, "learning_rate")
        self.discount = self._positive_float(discount, "discount")
        self.target_update_interval = self._positive_int(target_update_interval, "target_update_interval")
        self.batch_size = self._positive_int(batch_size, "batch_size")
        self.optimizers = {
            "uav": torch.optim.Adam(algorithm.uav_q.parameters(), lr=self.learning_rate),
            "vehicle": torch.optim.Adam(algorithm.vehicle_q.parameters(), lr=self.learning_rate),
        }
        self.update_count = 0
        self.role_update_count = {"uav": 0, "vehicle": 0}
        self.target_update_count = {"uav": 0, "vehicle": 0}
        algorithm._trainer = self

    @staticmethod
    def _positive_float(value: Any, name: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be finite and positive")
        result = float(value)
        if result <= 0.0 or not torch.isfinite(torch.tensor(result)):
            raise ValueError(f"{name} must be finite and positive")
        return result

    @staticmethod
    def _positive_int(value: Any, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return int(value)

    def _tensor(self, values: Any) -> Tensor:
        return torch.as_tensor(np.asarray(values), dtype=torch.float32, device=self.algorithm.device)

    def _role_tensors(self, role: str, rows: Sequence[Any]) -> dict[str, Tensor]:
        if not rows:
            raise ValueError("IQL update requires at least one replay row")
        if any(row.__class__.__name__ != "OffPolicyEnvelope" for row in rows):
            raise TypeError("IQL replay rows must be off-policy envelopes")
        return {
            "obs": self._tensor([row.role_batch.observations[role] for row in rows]),
            "next_obs": self._tensor([row.role_batch.next_observations[role] for row in rows]),
            "mask": torch.as_tensor(np.asarray([row.role_batch.masks[role] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "next_mask": torch.as_tensor(np.asarray([row.role_batch.next_masks[role] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
            "actions": torch.as_tensor(np.asarray([row.role_batch.actions[role] for row in rows]), dtype=torch.long, device=self.algorithm.device),
            "reward": self._tensor([row.team_reward for row in rows]),
            "done": self._tensor([row.role_batch.terminated or row.role_batch.truncated for row in rows]),
            "valid": torch.as_tensor([row.valid_sample for row in rows], dtype=torch.bool, device=self.algorithm.device),
            "valid_actor": torch.as_tensor(np.asarray([row.valid_actor_sample[role] for row in rows]), dtype=torch.bool, device=self.algorithm.device),
        }

    def _soft_update(self, role: str) -> None:
        source = self.algorithm.uav_q if role == "uav" else self.algorithm.vehicle_q
        target = self.algorithm.uav_target_q if role == "uav" else self.algorithm.vehicle_target_q
        target.load_state_dict(source.state_dict())
        self.target_update_count[role] += 1

    def update_role(self, role: str, rows: Sequence[Any]) -> dict[str, float | str]:
        if role not in ("uav", "vehicle"):
            raise ValueError("IQL role must be uav or vehicle")
        tensors = self._role_tensors(role, rows)
        valid = tensors["valid"].unsqueeze(-1) & tensors["valid_actor"]
        q_network = self.algorithm.uav_q if role == "uav" else self.algorithm.vehicle_q
        target_network = self.algorithm.uav_target_q if role == "uav" else self.algorithm.vehicle_target_q
        q = q_network(tensors["obs"])
        chosen = q.gather(-1, tensors["actions"].unsqueeze(-1)).squeeze(-1)
        with torch.no_grad():
            bootstrap = masked_bootstrap_max(target_network(tensors["next_obs"]), tensors["next_mask"])
            target = tensors["reward"].unsqueeze(-1) + self.discount * (1.0 - tensors["done"].unsqueeze(-1)) * bootstrap
        if not valid.any():
            return {"role": role, "loss": 0.0}
        loss = ((chosen - target) ** 2 * valid).sum() / valid.sum()
        if not torch.isfinite(loss):
            raise FloatingPointError("IQL loss is non-finite")
        optimizer = self.optimizers[role]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(q_network.parameters(), 10.0)
        optimizer.step()
        self.update_count += 1
        self.role_update_count[role] += 1
        if self.role_update_count[role] % self.target_update_interval == 0:
            self._soft_update(role)
        return {"role": role, "loss": float(loss.detach().cpu())}

    def update(self, rows_by_role: Mapping[str, Sequence[Any]]) -> dict[str, float]:
        result: dict[str, float] = {}
        for role in ("uav", "vehicle"):
            row = self.update_role(role, rows_by_role[role])
            result[f"{role}_loss"] = float(row["loss"])
        result["updates"] = float(self.update_count)
        return result

    @classmethod
    def _migrate_legacy_state(cls, state: Mapping[str, Any]) -> Mapping[str, Any]:
        legacy_keys = {
            "schema_version",
            "optimizers",
            "learning_rate",
            "discount",
            "target_update_interval",
            "batch_size",
            "update_count",
            "target_update_count",
        }
        if (
            isinstance(state, Mapping)
            and state.get("schema_version") == cls._STATE_SCHEMA_VERSION
            and set(state) == legacy_keys
        ):
            migrated = dict(state)
            migrated["role_update_count"] = {"uav": 0, "vehicle": 0}
            return migrated
        return state

    def validate_state(self, state: Mapping[str, Any]) -> None:
        state = self._migrate_legacy_state(state)
        expected = {"schema_version", "optimizers", "learning_rate", "discount", "target_update_interval", "batch_size", "update_count", "role_update_count", "target_update_count"}
        if not isinstance(state, Mapping) or set(state) != expected or state.get("schema_version") != self._STATE_SCHEMA_VERSION:
            raise ValueError("invalid IQL trainer state schema")
        if state["learning_rate"] != self.learning_rate or state["discount"] != self.discount or state["target_update_interval"] != self.target_update_interval or state["batch_size"] != self.batch_size:
            raise ValueError("IQL trainer frozen configuration drift")
        if isinstance(state["update_count"], bool) or not isinstance(state["update_count"], int) or state["update_count"] < 0:
            raise ValueError("IQL update count must be nonnegative")
        role_updates = state["role_update_count"]
        if not isinstance(role_updates, Mapping) or set(role_updates) != {"uav", "vehicle"} or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in role_updates.values()):
            raise ValueError("IQL role update counters are invalid")
        updates = state["target_update_count"]
        if not isinstance(updates, Mapping) or set(updates) != {"uav", "vehicle"} or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in updates.values()):
            raise ValueError("IQL target update counters are invalid")
        if not isinstance(state["optimizers"], Mapping) or set(state["optimizers"]) != {"uav", "vehicle"}:
            raise ValueError("IQL optimizer state is incomplete")
        try:
            for role, optimizer in self.optimizers.items():
                temporary = torch.optim.Adam(
                    (self.algorithm.uav_q if role == "uav" else self.algorithm.vehicle_q).parameters(),
                    lr=optimizer.param_groups[0]["lr"],
                )
                temporary.load_state_dict(deepcopy(state["optimizers"][role]))
        except (TypeError, ValueError, RuntimeError) as error:
            raise ValueError("IQL optimizer state is invalid") from error

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self._STATE_SCHEMA_VERSION,
            "optimizers": {role: deepcopy(optimizer.state_dict()) for role, optimizer in self.optimizers.items()},
            "learning_rate": self.learning_rate,
            "discount": self.discount,
            "target_update_interval": self.target_update_interval,
            "batch_size": self.batch_size,
            "update_count": self.update_count,
            "role_update_count": deepcopy(self.role_update_count),
            "target_update_count": deepcopy(self.target_update_count),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        state = self._migrate_legacy_state(state)
        self.validate_state(state)
        for role, optimizer in self.optimizers.items():
            optimizer.load_state_dict(deepcopy(state["optimizers"][role]))
        self.update_count = int(state["update_count"])
        self.role_update_count = dict(state["role_update_count"])
        self.target_update_count = dict(state["target_update_count"])


__all__ = ["IQLTrainer"]
