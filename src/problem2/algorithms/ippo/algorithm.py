"""Role-local heterogeneous PPO implementation for the IPPO comparison."""

from __future__ import annotations

import pickle
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
import torch
from torch import nn

from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.common.normalization import RunningNormalizer
from problem2.algorithms.protocol import ActionResult, HeterogeneousAlgorithm, OnPolicyEnvelope
from problem2.algorithms.sr_mappo.actors import RoleActor

from .trainer import IPPOTrainer, RoleLocalRolloutBatch


class LocalValueNetwork(nn.Module):
    """A scalar value function whose only input is one role-local observation."""

    def __init__(self, input_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.input_dim = int(input_dim)
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

    def forward(self, observation: Any) -> torch.Tensor:
        if not isinstance(observation, torch.Tensor):
            raise TypeError("LocalValueNetwork accepts one torch role-local observation tensor")
        if observation.shape[-1] != self.input_dim:
            raise ValueError(
                f"expected role observation width {self.input_dim}, got {observation.shape[-1]}"
            )
        return self.network(observation).squeeze(-1)


class IPPOAlgorithm(HeterogeneousAlgorithm):
    """Shared UAV and separate vehicle actor/value pairs with no team critic."""

    def __init__(
        self,
        uav_obs_dim: int,
        vehicle_obs_dim: int,
        uav_action_dim: int,
        vehicle_action_dim: int,
        hidden_dim: int = 128,
        device: str = "cpu",
        *,
        stability_components: Mapping[str, bool],
        training_config: Mapping[str, Any] | None = None,
    ) -> None:
        flags = dict(stability_components)
        if not flags or any(flags.values()):
            raise ValueError("IPPO requires every frozen SR stability flag off")
        self.device = torch.device(device)
        self.method_id = "ippo_mobile"
        self.stability_components = flags
        self.training_config = dict(training_config or {})
        self.uav_actor = RoleActor(
            uav_obs_dim,
            uav_action_dim,
            hidden_dim,
            orthogonal_initialization=False,
            layer_normalization=False,
        ).to(self.device)
        self.vehicle_actor = RoleActor(
            vehicle_obs_dim,
            vehicle_action_dim,
            hidden_dim,
            orthogonal_initialization=False,
            layer_normalization=False,
        ).to(self.device)
        self.uav_value = LocalValueNetwork(uav_obs_dim, hidden_dim).to(self.device)
        self.vehicle_value = LocalValueNetwork(vehicle_obs_dim, hidden_dim).to(self.device)
        self.uav_normalizer = RunningNormalizer(uav_obs_dim, role="uav")
        self.vehicle_normalizer = RunningNormalizer(vehicle_obs_dim, role="vehicle")
        self.return_normalizers = {
            "uav": RunningNormalizer(1, role="uav_return"),
            "vehicle": RunningNormalizer(1, role="vehicle_return"),
        }
        self.training = True
        self._trainer: IPPOTrainer | None = None
        self._diagnostics = DiagnosticCounters()
        self._pending_envelopes: list[OnPolicyEnvelope] = []
        self._update_count = 0

    @property
    def trainer(self) -> IPPOTrainer:
        if self._trainer is None:
            raise RuntimeError("the IPPO trainer has not been attached")
        return self._trainer

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics

    def train(self, mode: bool = True) -> "IPPOAlgorithm":
        self.training = bool(mode)
        for network in (
            self.uav_actor,
            self.vehicle_actor,
            self.uav_value,
            self.vehicle_value,
        ):
            network.train(mode)
        return self

    def _tensor(self, values: Any) -> torch.Tensor:
        return torch.as_tensor(values, dtype=torch.float32, device=self.device)

    def _normalize(self, role: str, values: Any, *, update: bool) -> np.ndarray:
        array = np.asarray(values, dtype=np.float32)
        if not self.stability_components["observation_normalization"]:
            return array.copy()
        normalizer = self.uav_normalizer if role == "uav" else self.vehicle_normalizer
        return normalizer.normalize(array, update=update)

    def _role_act(
        self,
        role: str,
        observation: Any,
        mask: Any,
        *,
        deterministic: bool,
        update_normalizer: bool,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        normalized = self._normalize(role, observation, update=update_normalizer)
        actor = self.uav_actor if role == "uav" else self.vehicle_actor
        value_network = self.uav_value if role == "uav" else self.vehicle_value
        tensor = self._tensor(normalized)
        distribution = masked_categorical(
            actor(tensor),
            torch.as_tensor(mask, dtype=torch.bool, device=self.device),
        )
        actions = distribution.probs.argmax(dim=-1) if deterministic else distribution.sample()
        return (
            actions.detach().cpu().numpy().astype(np.int64),
            distribution.log_prob(actions).detach().cpu().numpy().astype(np.float32),
            distribution.entropy().detach().cpu().numpy().astype(np.float32),
            normalized,
            value_network(tensor).detach().cpu().numpy().astype(np.float32),
        )

    def act(
        self,
        observations: Mapping[str, Any],
        masks: Mapping[str, Any],
        deterministic: bool = False,
        *,
        return_details: bool = False,
    ) -> ActionResult | dict[str, Any]:
        with torch.no_grad():
            update = self.training and not deterministic
            results = {
                role: self._role_act(
                    role,
                    observations[role],
                    masks[role],
                    deterministic=deterministic,
                    update_normalizer=update,
                )
                for role in self.roles
            }
        actions = {role: results[role][0] for role in self.roles}
        behavior_masks = {
            role: np.asarray(masks[role], dtype=bool).copy() for role in self.roles
        }
        if not return_details:
            return ActionResult(actions=actions, masks=behavior_masks)
        return {
            "actions": {role: actions[role].tolist() for role in self.roles},
            "policy_observations": {role: results[role][3] for role in self.roles},
            "normalized_observations": {role: results[role][3] for role in self.roles},
            "masks": behavior_masks,
            "log_probs": {role: results[role][1].tolist() for role in self.roles},
            "entropies": {role: results[role][2].tolist() for role in self.roles},
            "values": {role: results[role][4].tolist() for role in self.roles},
            "normalization_versions": {
                "uav": self.uav_normalizer.version,
                "vehicle": self.vehicle_normalizer.version,
                "uav_return": self.return_normalizers["uav"].version,
                "vehicle_return": self.return_normalizers["vehicle"].version,
            },
        }

    def replay_log_probs(
        self,
        policy_observations: Mapping[str, Any],
        masks: Mapping[str, Any],
        actions: Mapping[str, Any],
    ) -> dict[str, np.ndarray]:
        with torch.no_grad():
            result: dict[str, np.ndarray] = {}
            for role in self.roles:
                actor = self.uav_actor if role == "uav" else self.vehicle_actor
                distribution = masked_categorical(
                    actor(self._tensor(policy_observations[role])),
                    torch.as_tensor(masks[role], dtype=torch.bool, device=self.device),
                )
                result[role] = (
                    distribution.log_prob(
                        torch.as_tensor(actions[role], dtype=torch.long, device=self.device)
                    )
                    .detach()
                    .cpu()
                    .numpy()
                    .astype(np.float32)
                )
            return result

    def local_value(self, role: str, observation: Any) -> torch.Tensor:
        if role not in self.roles:
            raise ValueError(f"unknown role: {role}")
        network = self.uav_value if role == "uav" else self.vehicle_value
        tensor = observation if isinstance(observation, torch.Tensor) else self._tensor(observation)
        return network(tensor)

    def observe(self, batch: OnPolicyEnvelope) -> None:
        if isinstance(batch, OnPolicyEnvelope):
            if batch.value_conditioning != "local":
                raise ValueError("IPPO requires local envelope values")
            expected_versions = {
                "uav": self.uav_normalizer.version,
                "vehicle": self.vehicle_normalizer.version,
                "uav_return": self.return_normalizers["uav"].version,
                "vehicle_return": self.return_normalizers["vehicle"].version,
            }
            if batch.normalization_versions != expected_versions:
                raise ValueError("envelope normalization versions do not match current normalizers")
            replayed = self.replay_log_probs(batch.policy_observations, batch.role_batch.masks, batch.role_batch.actions)
            for role in self.roles:
                if not np.allclose(replayed[role], batch.old_log_probs[role], atol=1e-6, rtol=1e-6):
                    raise ValueError("stored behavior log probabilities do not replay")
            self._pending_envelopes.append(OnPolicyEnvelope.from_state_dict(batch.state_dict()))
            self._diagnostics.increment("observed_transitions")
            return
        raise TypeError("IPPO observes only behavior-bound on-policy envelopes")

    def _rollout_from_envelopes(self) -> RoleLocalRolloutBatch:
        batch = RoleLocalRolloutBatch()
        for envelope in self._pending_envelopes:
            transition = envelope.role_batch
            batch.add(reward=envelope.team_reward, values=envelope.values, next_values=envelope.next_values, terminated=transition.terminated, truncated=transition.truncated, observations=envelope.policy_observations, masks=transition.masks, actions=transition.actions, old_log_probs=envelope.old_log_probs, valid_actor_sample=envelope.valid_actor_sample, valid_sample=envelope.valid_sample)
        batch.finish(float(self.training_config.get("discount", 0.99)), float(self.training_config.get("gae_lambda", 0.95)))
        return batch

    def update(self) -> Mapping[str, Any]:
        if not self._pending_envelopes:
            raise RuntimeError("no behavior-bound role-local envelope is pending")
        metrics = self.trainer.update(
            self._rollout_from_envelopes(),
            epochs=int(self.training_config.get("ppo_epochs", 1)),
        )
        self._pending_envelopes = []
        self._update_count += 1
        self._diagnostics.increment("updates")
        return metrics

    def set_evaluation(self, enabled: bool) -> None:
        self.train(not bool(enabled))

    def normalizer_state_bytes(self) -> bytes:
        return pickle.dumps(
            {
                "uav": self.uav_normalizer.state_dict(),
                "vehicle": self.vehicle_normalizer.state_dict(),
                "returns": {
                    role: normalizer.state_dict()
                    for role, normalizer in self.return_normalizers.items()
                },
            },
            protocol=5,
        )

    def state_dict(self) -> dict[str, Any]:
        rollout_position = len(self._pending_envelopes)
        state: dict[str, Any] = {
            "method_id": self.method_id,
            "uav_actor": self.uav_actor.state_dict(),
            "vehicle_actor": self.vehicle_actor.state_dict(),
            "uav_value": self.uav_value.state_dict(),
            "vehicle_value": self.vehicle_value.state_dict(),
            "uav_normalizer": self.uav_normalizer.state_dict(),
            "vehicle_normalizer": self.vehicle_normalizer.state_dict(),
            "return_normalizers": {
                role: normalizer.state_dict()
                for role, normalizer in self.return_normalizers.items()
            },
            "stability_components": dict(self.stability_components),
            "training_config": dict(self.training_config),
            "training": self.training,
            "diagnostics": self._diagnostics.state_dict(),
            "pending_envelopes": [item.state_dict() for item in self._pending_envelopes],
            "rollout_position": rollout_position,
            "update_count": self._update_count,
        }
        if self._trainer is not None:
            state["trainer"] = self._trainer.state_dict()
        if self.training_config:
            state["schema_version"] = "g5-local-on-policy-state-v1"
        return state

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if self.training_config:
            required = {"schema_version", "method_id", "uav_actor", "vehicle_actor", "uav_value", "vehicle_value", "uav_normalizer", "vehicle_normalizer", "return_normalizers", "stability_components", "training_config", "training", "diagnostics", "pending_envelopes", "rollout_position", "update_count", "trainer"}
            if set(state) != required or state.get("schema_version") != "g5-local-on-policy-state-v1":
                raise ValueError("invalid G5 local method state schema")
            if state["method_id"] != self.method_id or state["training_config"] != self.training_config or state["stability_components"] != self.stability_components:
                raise ValueError("G5 local frozen configuration drift")
            if not isinstance(state["training"], (bool, np.bool_)):
                raise ValueError("G5 local training flag must be boolean")
            if any(isinstance(state[name], (bool, np.bool_)) or not isinstance(state[name], (int, np.integer)) or state[name] < 0 for name in ("rollout_position", "update_count")):
                raise ValueError("G5 local counters must be nonnegative integers")
            if not isinstance(state["pending_envelopes"], list):
                raise ValueError("G5 local pending envelopes must be a list")
            pending = [OnPolicyEnvelope.from_state_dict(item) for item in state["pending_envelopes"]]
            if state["rollout_position"] != len(pending):
                raise ValueError("G5 local pending envelope position drift")
            returns = state["return_normalizers"]
            if not isinstance(returns, Mapping) or set(returns) != set(self.return_normalizers):
                raise ValueError("G5 local return normalizers must contain exact role keys")
            try:
                for module, key in ((self.uav_actor, "uav_actor"), (self.vehicle_actor, "vehicle_actor"), (self.uav_value, "uav_value"), (self.vehicle_value, "vehicle_value")):
                    deepcopy(module).load_state_dict(deepcopy(state[key]))
                for normalizer, key in ((self.uav_normalizer, "uav_normalizer"), (self.vehicle_normalizer, "vehicle_normalizer")):
                    deepcopy(normalizer).load_state_dict(deepcopy(state[key]))
                for role, normalizer in self.return_normalizers.items():
                    deepcopy(normalizer).load_state_dict(deepcopy(returns[role]))
                diagnostics = DiagnosticCounters()
                diagnostics.load_state_dict(deepcopy(state["diagnostics"]))
                if self._trainer is None:
                    raise ValueError("G5 local state requires attached trainer")
                self._trainer.validate_state(state["trainer"])
            except ValueError:
                raise
            except Exception as error:
                raise ValueError("invalid nested G5 local method state") from error
            self.uav_actor.load_state_dict(state["uav_actor"])
            self.vehicle_actor.load_state_dict(state["vehicle_actor"])
            self.uav_value.load_state_dict(state["uav_value"])
            self.vehicle_value.load_state_dict(state["vehicle_value"])
            self.uav_normalizer.load_state_dict(state["uav_normalizer"])
            self.vehicle_normalizer.load_state_dict(state["vehicle_normalizer"])
            for role, normalizer_state in state["return_normalizers"].items():
                self.return_normalizers[role].load_state_dict(normalizer_state)
            self.stability_components = dict(state["stability_components"])
            self.training_config = dict(state["training_config"])
            self._diagnostics.load_state_dict(state["diagnostics"])
            self._pending_envelopes = pending
            self._update_count = state["update_count"]
            self._trainer.load_state_dict(state["trainer"])
            self.train(bool(state["training"]))
            return
        if state.get("method_id") != self.method_id:
            raise ValueError("checkpoint method does not match ippo_mobile")
        self.uav_actor.load_state_dict(state["uav_actor"])
        self.vehicle_actor.load_state_dict(state["vehicle_actor"])
        self.uav_value.load_state_dict(state["uav_value"])
        self.vehicle_value.load_state_dict(state["vehicle_value"])
        self.uav_normalizer.load_state_dict(state["uav_normalizer"])
        self.vehicle_normalizer.load_state_dict(state["vehicle_normalizer"])
        for role, normalizer_state in state["return_normalizers"].items():
            self.return_normalizers[role].load_state_dict(normalizer_state)
        self.stability_components = dict(state["stability_components"])
        self.training_config = dict(state["training_config"])
        self._diagnostics.load_state_dict(state["diagnostics"])
        self._pending_envelopes = [OnPolicyEnvelope.from_state_dict(item) for item in state.get("pending_envelopes", [])]
        if int(state.get("rollout_position", len(self._pending_envelopes))) != len(self._pending_envelopes):
            raise ValueError("G5 local pending envelope position drift")
        self._update_count = int(state.get("update_count", 0))
        trainer_state = state.get("trainer")
        if trainer_state is not None:
            if self._trainer is None:
                raise ValueError("checkpoint contains trainer state but no trainer is attached")
            self._trainer.load_state_dict(trainer_state)
        self.train(bool(state.get("training", True)))


__all__ = ["IPPOAlgorithm", "LocalValueNetwork"]
