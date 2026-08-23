"""Collection and evaluation interface for heterogeneous SR-MAPPO."""

from __future__ import annotations

import pickle
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.common.normalization import RunningNormalizer
from problem2.algorithms.protocol import ActionResult, HeterogeneousAlgorithm, OnPolicyEnvelope

from .actors import RoleActor
from .critic import CentralCritic
from .rollout import RolloutBatch


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


class SRMAPPOAlgorithm(HeterogeneousAlgorithm):
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
        *,
        method_id: str = "sr_mappo_mobile",
        training_config: Mapping[str, Any] | None = None,
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
        self.method_id = str(method_id)
        self.training_config = dict(training_config or {})
        comparison_training_config = {
            key: value
            for key, value in self.training_config.items()
            if key != "candidate_config_hash"
        }
        self.comparison_config = {
            "uav_obs_dim": int(uav_obs_dim),
            "vehicle_obs_dim": int(vehicle_obs_dim),
            "critic_state_dim": int(state_dim),
            "uav_action_dim": int(uav_action_dim),
            "vehicle_action_dim": int(vehicle_action_dim),
            "hidden_width": int(hidden_dim),
            **comparison_training_config,
            "stability_components": dict(self.stability_components),
        }
        self._diagnostics = DiagnosticCounters()
        self._pending_envelopes: list[OnPolicyEnvelope] = []
        self._update_count = 0

    @property
    def obs_normalizer(self) -> RunningNormalizer:
        return self.uav_normalizer

    @property
    def trainer(self) -> Any:
        if self._trainer is None:
            raise RuntimeError("the on-policy trainer has not been attached")
        return self._trainer

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics

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
    ) -> ActionResult:
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
    ) -> ActionResult | dict[str, Any]:
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
            return ActionResult(
                actions={
                    role: np.asarray(values, dtype=np.int64)
                    for role, values in actions.items()
                },
                masks={
                    role: np.asarray(masks[role], dtype=bool).copy()
                    for role in self.roles
                },
            )
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

    def observe(self, batch: OnPolicyEnvelope) -> None:
        if isinstance(batch, OnPolicyEnvelope):
            if batch.value_conditioning != "centralized":
                raise ValueError("centralized SR-MAPPO requires centralized envelope values")
            expected_versions = {
                "uav": self.uav_normalizer.version,
                "vehicle": self.vehicle_normalizer.version,
                "return": self.return_normalizer.version,
            }
            if batch.normalization_versions != expected_versions:
                raise ValueError("envelope normalization versions do not match current normalizers")
            if np.asarray(batch.critic_state).shape != (self.critic.state_dim,) or np.asarray(batch.next_critic_state).shape != (self.critic.state_dim,):
                raise ValueError("centralized critic state width does not match critic.state_dim")
            replayed = self.replay_log_probs(batch.policy_observations, batch.role_batch.masks, batch.role_batch.actions)
            for role in self.roles:
                if not np.allclose(replayed[role], batch.old_log_probs[role], atol=1e-6, rtol=1e-6):
                    raise ValueError("stored behavior log probabilities do not replay")
            self._pending_envelopes.append(OnPolicyEnvelope.from_state_dict(batch.state_dict()))
            self._diagnostics.increment("observed_transitions")
            return
        raise TypeError("SR-MAPPO observes only behavior-bound on-policy envelopes")

    def _rollout_from_envelopes(self) -> RolloutBatch:
        batch = RolloutBatch()
        for envelope in self._pending_envelopes:
            transition = envelope.role_batch
            batch.add({"role": {"uav": envelope.agent_ids["uav"], "vehicle": envelope.agent_ids["vehicle"]}, "agent_id": envelope.agent_ids, "raw_observation": transition.observations, "normalized_policy_observation": envelope.policy_observations, "critic_state": envelope.critic_state, "action": transition.actions, "action_mask": transition.masks, "old_log_prob": envelope.old_log_probs, "value": float(envelope.values), "next_value": float(envelope.next_values), "reward": envelope.team_reward, "terminated": transition.terminated, "truncated": transition.truncated, "valid_sample": envelope.valid_sample, "valid_actor_sample": envelope.valid_actor_sample, "candidate_mapping": envelope.candidate_mapping, "normalization_versions": envelope.normalization_versions, "episode_id": transition.scenario_id, "config_hash": str(self.training_config.get("candidate_config_hash", "g5"))})
        batch.finish(float(self.training_config.get("discount", 0.99)), float(self.training_config.get("gae_lambda", 0.95)))
        return batch

    def update(self) -> Mapping[str, Any]:
        if not self._pending_envelopes:
            raise RuntimeError("no behavior-bound centralized envelope is pending")
        epochs = int(self.training_config.get("ppo_epochs", 1))
        total_updates = max(1, int(self.training_config.get("total_updates", 1)))
        progress = min(1.0, float(self._update_count + 1) / float(total_updates))
        metrics = dict(
            self.trainer.update(
                self._rollout_from_envelopes(),
                epochs=epochs,
                progress=progress,
            )
        )
        self._pending_envelopes = []
        self._update_count += 1
        self._diagnostics.increment("updates")
        return metrics

    def set_evaluation(self, enabled: bool) -> None:
        self.train(not bool(enabled))

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

    def normalize_return_tensor(self, values: torch.Tensor) -> torch.Tensor:
        """Map physical critic outputs into the frozen return-target domain."""

        if not isinstance(values, torch.Tensor):
            raise TypeError("return tensor normalization requires a torch tensor")
        if not self.stability_components["return_normalization"]:
            return values
        mean = torch.as_tensor(
            self.return_normalizer.mean.reshape(-1)[0],
            dtype=values.dtype,
            device=values.device,
        )
        variance = torch.as_tensor(
            self.return_normalizer.variance.reshape(-1)[0],
            dtype=values.dtype,
            device=values.device,
        )
        scale = torch.sqrt(
            torch.clamp(variance, min=0.0) + self.return_normalizer.epsilon
        )
        return (values - mean) / scale

    def normalizer_state_bytes(self) -> bytes:
        state = {
            "uav": self.uav_normalizer.state_dict(),
            "vehicle": self.vehicle_normalizer.state_dict(),
            "return": self.return_normalizer.state_dict(),
        }
        return pickle.dumps(state, protocol=5)

    def state_dict(self) -> dict[str, Any]:
        rollout_position = len(self._pending_envelopes)
        state = {
            "method_id": self.method_id,
            "uav_actor": self.uav_actor.state_dict(),
            "vehicle_actor": self.vehicle_actor.state_dict(),
            "critic": self.critic.state_dict(),
            "uav_normalizer": self.uav_normalizer.state_dict(),
            "vehicle_normalizer": self.vehicle_normalizer.state_dict(),
            "return_normalizer": self.return_normalizer.state_dict(),
            "stability_components": dict(self.stability_components),
            "training": self.training,
            "training_config": dict(self.training_config),
            "comparison_config": pickle.loads(
                pickle.dumps(self.comparison_config, protocol=5)
            ),
            "diagnostics": self._diagnostics.state_dict(),
            "pending_envelopes": [item.state_dict() for item in self._pending_envelopes],
            "rollout_position": rollout_position,
            "update_count": self._update_count,
        }
        if self._trainer is not None:
            state["trainer"] = self._trainer.state_dict()
        if self.training_config:
            state["schema_version"] = "g5-centralized-on-policy-state-v1"
        return state

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if self.training_config:
            required = {"schema_version", "method_id", "uav_actor", "vehicle_actor", "critic", "uav_normalizer", "vehicle_normalizer", "return_normalizer", "stability_components", "training", "training_config", "comparison_config", "diagnostics", "pending_envelopes", "rollout_position", "update_count", "trainer"}
            if set(state) != required or state.get("schema_version") != "g5-centralized-on-policy-state-v1":
                raise ValueError("invalid G5 centralized method state schema")
            if state["method_id"] != self.method_id or state["training_config"] != self.training_config or state["stability_components"] != self.stability_components or state["comparison_config"] != self.comparison_config:
                raise ValueError("G5 centralized frozen configuration drift")
            if not isinstance(state["training"], (bool, np.bool_)):
                raise ValueError("G5 centralized training flag must be boolean")
            if any(isinstance(state[name], (bool, np.bool_)) or not isinstance(state[name], (int, np.integer)) or state[name] < 0 for name in ("rollout_position", "update_count")):
                raise ValueError("G5 centralized counters must be nonnegative integers")
            if not isinstance(state["pending_envelopes"], list):
                raise ValueError("G5 centralized pending envelopes must be a list")
            pending = [OnPolicyEnvelope.from_state_dict(item) for item in state["pending_envelopes"]]
            if state["rollout_position"] != len(pending):
                raise ValueError("G5 centralized pending envelope position drift")
            try:
                for module, key in ((self.uav_actor, "uav_actor"), (self.vehicle_actor, "vehicle_actor"), (self.critic, "critic")):
                    deepcopy(module).load_state_dict(deepcopy(state[key]))
                for normalizer, key in ((self.uav_normalizer, "uav_normalizer"), (self.vehicle_normalizer, "vehicle_normalizer"), (self.return_normalizer, "return_normalizer")):
                    deepcopy(normalizer).load_state_dict(deepcopy(state[key]))
                diagnostics = DiagnosticCounters()
                diagnostics.load_state_dict(deepcopy(state["diagnostics"]))
                if self._trainer is None:
                    raise ValueError("G5 centralized state requires attached trainer")
                self._trainer.validate_state(state["trainer"])
            except ValueError:
                raise
            except Exception as error:
                raise ValueError("invalid nested G5 centralized method state") from error
            self.uav_actor.load_state_dict(state["uav_actor"])
            self.vehicle_actor.load_state_dict(state["vehicle_actor"])
            self.critic.load_state_dict(state["critic"])
            self.uav_normalizer.load_state_dict(state["uav_normalizer"])
            self.vehicle_normalizer.load_state_dict(state["vehicle_normalizer"])
            self.return_normalizer.load_state_dict(state["return_normalizer"])
            self.stability_components = dict(state["stability_components"])
            self.training_config = dict(state["training_config"])
            self.comparison_config = dict(state["comparison_config"])
            self._diagnostics.load_state_dict(state["diagnostics"])
            self._pending_envelopes = pending
            self._update_count = state["update_count"]
            self._trainer.load_state_dict(state["trainer"])
            self.train(bool(state["training"]))
            return
        stored_method = state.get("method_id", self.method_id)
        if stored_method != self.method_id:
            raise ValueError(
                f"checkpoint method {stored_method!r} does not match {self.method_id!r}"
            )
        self.uav_actor.load_state_dict(state["uav_actor"])
        self.vehicle_actor.load_state_dict(state["vehicle_actor"])
        self.critic.load_state_dict(state["critic"])
        self.uav_normalizer.load_state_dict(state["uav_normalizer"])
        self.vehicle_normalizer.load_state_dict(state["vehicle_normalizer"])
        self.return_normalizer.load_state_dict(state["return_normalizer"])
        self.stability_components = dict(state["stability_components"])
        self.training_config = dict(state.get("training_config", self.training_config))
        self.comparison_config = dict(
            state.get("comparison_config", self.comparison_config)
        )
        diagnostics = state.get("diagnostics")
        if diagnostics is not None:
            self._diagnostics.load_state_dict(diagnostics)
        self._pending_envelopes = [OnPolicyEnvelope.from_state_dict(item) for item in state.get("pending_envelopes", [])]
        if int(state.get("rollout_position", len(self._pending_envelopes))) != len(self._pending_envelopes):
            raise ValueError("G5 centralized pending envelope position drift")
        self._update_count = int(state.get("update_count", 0))
        trainer_state = state.get("trainer")
        if trainer_state is not None:
            if self._trainer is None:
                raise ValueError("checkpoint contains trainer state but no trainer is attached")
            self._trainer.load_state_dict(trainer_state)
        self.train(bool(state.get("training", True)))


__all__ = ["SRMAPPOAlgorithm"]
