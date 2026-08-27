"""Heterogeneous discrete MADDPG with a shared UAV actor."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import ActionResult, HeterogeneousAlgorithm, OffPolicyEnvelope

from .networks import CentralizedRoleQ, DiscreteActor


class MADDPGAlgorithm(HeterogeneousAlgorithm):
    """Role-isolated discrete MADDPG for the UAV/vehicle pair."""

    def __init__(
        self,
        uav_obs_dim: int,
        vehicle_obs_dim: int,
        state_dim: int,
        uav_action_dim: int,
        vehicle_action_dim: int,
        hidden_dim: int = 128,
        device: str = "cpu",
        *,
        training_config: Mapping[str, Any],
        uav_count: int = 2,
        vehicle_count: int = 1,
    ) -> None:
        self.device = torch.device(device)
        self.method_id = "maddpg_mobile"
        self.training_config = dict(training_config)
        self.uav_obs_dim = int(uav_obs_dim)
        self.vehicle_obs_dim = int(vehicle_obs_dim)
        self.state_dim = int(state_dim)
        self.uav_action_dim = int(uav_action_dim)
        self.vehicle_action_dim = int(vehicle_action_dim)
        self.hidden_dim = int(hidden_dim)
        self.uav_count = int(uav_count)
        self.vehicle_count = int(vehicle_count)
        self.uav_actor = DiscreteActor(self.uav_obs_dim, self.uav_action_dim, self.hidden_dim, int(self.training_config.get("hidden_depth", 2))).to(self.device)
        self.vehicle_actor = DiscreteActor(self.vehicle_obs_dim, self.vehicle_action_dim, self.hidden_dim, int(self.training_config.get("hidden_depth", 2))).to(self.device)
        self.uav_target_actor = deepcopy(self.uav_actor).to(self.device)
        self.vehicle_target_actor = deepcopy(self.vehicle_actor).to(self.device)
        self.uav_critic = CentralizedRoleQ(self.state_dim, self.uav_action_dim, self.vehicle_action_dim, self.hidden_dim, uav_count=self.uav_count, vehicle_count=self.vehicle_count).to(self.device)
        self.vehicle_critic = CentralizedRoleQ(self.state_dim, self.uav_action_dim, self.vehicle_action_dim, self.hidden_dim, uav_count=self.uav_count, vehicle_count=self.vehicle_count).to(self.device)
        self.uav_target_critic = deepcopy(self.uav_critic).to(self.device)
        self.vehicle_target_critic = deepcopy(self.vehicle_critic).to(self.device)
        for target in (self.uav_target_actor, self.vehicle_target_actor, self.uav_target_critic, self.vehicle_target_critic):
            for parameter in target.parameters():
                parameter.requires_grad_(False)
        self.replay = JointReplayBuffer(int(self.training_config.get("replay_capacity", 100000)), seed=0)
        self.training = True
        self.exploration = {
            "epsilon": float(self.training_config.get("exploration_initial", 1.0)),
            "initial": float(self.training_config.get("exploration_initial", 1.0)),
            "final": float(self.training_config.get("exploration_final", 0.05)),
            "step": 0,
        }
        self._diagnostics = DiagnosticCounters()
        self._trainer: Any = None
        self._update_count = 0

    @property
    def trainer(self) -> Any:
        if self._trainer is None:
            raise RuntimeError("the MADDPG trainer has not been attached")
        return self._trainer

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics

    def train(self, mode: bool = True) -> "MADDPGAlgorithm":
        self.training = bool(mode)
        for network in (self.uav_actor, self.vehicle_actor, self.uav_critic, self.vehicle_critic):
            network.train(mode)
        for network in (self.uav_target_actor, self.vehicle_target_actor, self.uav_target_critic, self.vehicle_target_critic):
            network.eval()
        return self

    def _masked_argmax(self, logits: torch.Tensor, mask: Any) -> np.ndarray:
        mask_tensor = torch.as_tensor(mask, dtype=torch.bool, device=self.device)
        if mask_tensor.shape != logits.shape or not mask_tensor.any(dim=-1).all():
            raise ValueError("each action row must have a legal masked action")
        return logits.masked_fill(~mask_tensor, float("-inf")).argmax(dim=-1).detach().cpu().numpy().astype(np.int64)

    def _role_act(self, role: str, observations: Any, masks: Any, deterministic: bool) -> np.ndarray:
        actor = self.uav_actor if role == "uav" else self.vehicle_actor
        logits = actor(torch.as_tensor(observations, dtype=torch.float32, device=self.device))
        actions = self._masked_argmax(logits, masks)
        if not deterministic and self.training:
            mask = np.asarray(masks, dtype=bool)
            random_rows = np.random.random(len(actions)) < self.exploration["epsilon"]
            for index in np.flatnonzero(random_rows):
                actions[index] = int(np.random.choice(np.flatnonzero(mask[index])))
            self.exploration["step"] += 1
            self.exploration["epsilon"] = max(self.exploration["final"], self.exploration["epsilon"] * 0.999)
        return actions

    def act(self, observations: Mapping[str, Any], masks: Mapping[str, Any], deterministic: bool = False, *, return_details: bool = False) -> ActionResult | dict[str, Any]:
        with torch.no_grad():
            actions = {
                "uav": self._role_act("uav", observations["uav"], masks["uav"], deterministic),
                "vehicle": self._role_act("vehicle", observations["vehicle"], masks["vehicle"], deterministic),
            }
        result = ActionResult(
            actions=actions,
            masks={role: np.asarray(masks[role], dtype=bool).copy() for role in self.roles},
        )
        if not return_details:
            return result
        return {
            "actions": {role: result.actions[role].tolist() for role in self.roles},
            "masks": result.masks,
            "exploration": deepcopy(self.exploration),
        }

    def observe(self, batch: OffPolicyEnvelope) -> None:
        if not isinstance(batch, OffPolicyEnvelope):
            raise TypeError("MADDPG observes only off-policy envelopes")
        if batch.critic_state.shape != (self.state_dim,) or batch.next_critic_state.shape != (self.state_dim,):
            raise ValueError("off-policy critic state width does not match MADDPG")
        self.replay.append(batch)
        self._diagnostics.increment("observed_transitions")

    def update(self) -> Mapping[str, Any]:
        if not len(self.replay):
            raise RuntimeError("no off-policy transition is pending")
        rows = self.replay.sample(min(self.trainer.batch_size, len(self.replay)))
        metrics = self.trainer.update(rows)
        self._update_count += 1
        self._diagnostics.increment("updates")
        return metrics

    def set_evaluation(self, enabled: bool) -> None:
        self.train(not bool(enabled))

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "g5-maddpg-state-v1",
            "method_id": self.method_id,
            "training_config": deepcopy(self.training_config),
            "training": self.training,
            "uav_actor": self.uav_actor.state_dict(),
            "vehicle_actor": self.vehicle_actor.state_dict(),
            "uav_target_actor": self.uav_target_actor.state_dict(),
            "vehicle_target_actor": self.vehicle_target_actor.state_dict(),
            "uav_critic": self.uav_critic.state_dict(),
            "vehicle_critic": self.vehicle_critic.state_dict(),
            "uav_target_critic": self.uav_target_critic.state_dict(),
            "vehicle_target_critic": self.vehicle_target_critic.state_dict(),
            "replay": self.replay.state_dict(),
            "exploration": deepcopy(self.exploration),
            "update_count": self._update_count,
            "diagnostics": self._diagnostics.state_dict(),
            "trainer": self.trainer.state_dict(),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        required = {"schema_version", "method_id", "training_config", "training", "uav_actor", "vehicle_actor", "uav_target_actor", "vehicle_target_actor", "uav_critic", "vehicle_critic", "uav_target_critic", "vehicle_target_critic", "replay", "exploration", "update_count", "diagnostics", "trainer"}
        if not isinstance(state, Mapping) or set(state) != required or state.get("schema_version") != "g5-maddpg-state-v1":
            raise ValueError("invalid MADDPG state schema")
        if state["method_id"] != self.method_id or state["training_config"] != self.training_config:
            raise ValueError("MADDPG frozen configuration drift")
        if not isinstance(state["training"], (bool, np.bool_)):
            raise ValueError("MADDPG training flag must be boolean")
        if isinstance(state["update_count"], bool) or not isinstance(state["update_count"], int) or state["update_count"] < 0:
            raise ValueError("MADDPG update count must be nonnegative")
        exploration = state["exploration"]
        if not isinstance(exploration, Mapping) or set(exploration) != {"epsilon", "initial", "final", "step"}:
            raise ValueError("MADDPG exploration state is incomplete")
        for name in ("epsilon", "initial", "final"):
            if not np.isfinite(float(exploration[name])):
                raise ValueError("MADDPG exploration state must be finite")
        if isinstance(exploration["step"], bool) or not isinstance(exploration["step"], int) or exploration["step"] < 0:
            raise ValueError("MADDPG exploration step must be nonnegative")

        modules = (
            (self.uav_actor, "uav_actor"), (self.vehicle_actor, "vehicle_actor"),
            (self.uav_target_actor, "uav_target_actor"), (self.vehicle_target_actor, "vehicle_target_actor"),
            (self.uav_critic, "uav_critic"), (self.vehicle_critic, "vehicle_critic"),
            (self.uav_target_critic, "uav_target_critic"), (self.vehicle_target_critic, "vehicle_target_critic"),
        )
        clones = []
        try:
            for module, key in modules:
                clone = deepcopy(module)
                clone.load_state_dict(deepcopy(state[key]))
                clones.append((module, clone))
            replay = JointReplayBuffer(self.replay.capacity, seed=0)
            replay.load_state_dict(deepcopy(state["replay"]))
            diagnostics = DiagnosticCounters()
            diagnostics.load_state_dict(deepcopy(state["diagnostics"]))
            self.trainer.validate_state(state["trainer"])
        except (TypeError, ValueError, RuntimeError) as error:
            raise ValueError("invalid nested MADDPG state") from error

        for module, clone in clones:
            module.load_state_dict(clone.state_dict())
        self.replay = replay
        self._diagnostics.load_state_dict(state["diagnostics"])
        self.trainer.load_state_dict(state["trainer"])
        self.exploration = dict(exploration)
        self._update_count = int(state["update_count"])
        self.train(bool(state["training"]))


__all__ = ["MADDPGAlgorithm"]
