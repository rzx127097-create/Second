"""Role-local heterogeneous IQL with masked epsilon-greedy behavior."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
import torch

from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import ActionResult, HeterogeneousAlgorithm, OffPolicyEnvelope

from .networks import QNetwork


class IQLAlgorithm(HeterogeneousAlgorithm):
    """Independent role-local Q learners with shared team reward."""

    def __init__(
        self,
        uav_obs_dim: int,
        vehicle_obs_dim: int,
        uav_action_dim: int,
        vehicle_action_dim: int,
        hidden_dim: int = 128,
        device: str = "cpu",
        *,
        training_config: Mapping[str, Any],
    ) -> None:
        self.device = torch.device(device)
        self.method_id = "iql_mobile"
        self.training_config = dict(training_config)
        self.uav_obs_dim = int(uav_obs_dim)
        self.vehicle_obs_dim = int(vehicle_obs_dim)
        self.uav_action_dim = int(uav_action_dim)
        self.vehicle_action_dim = int(vehicle_action_dim)
        self.hidden_dim = int(hidden_dim)
        depth = int(self.training_config.get("hidden_depth", 2))
        self.uav_q = QNetwork(self.uav_obs_dim, self.uav_action_dim, self.hidden_dim, depth).to(self.device)
        self.vehicle_q = QNetwork(self.vehicle_obs_dim, self.vehicle_action_dim, self.hidden_dim, depth).to(self.device)
        self.uav_target_q = deepcopy(self.uav_q).to(self.device)
        self.vehicle_target_q = deepcopy(self.vehicle_q).to(self.device)
        for target in (self.uav_target_q, self.vehicle_target_q):
            for parameter in target.parameters():
                parameter.requires_grad_(False)
            target.eval()
        capacity = int(self.training_config.get("replay_capacity", 100000))
        self.uav_replay = JointReplayBuffer(capacity, seed=0)
        self.vehicle_replay = JointReplayBuffer(capacity, seed=1)
        initial = float(self.training_config.get("epsilon_initial", 1.0))
        final = float(self.training_config.get("epsilon_final", 0.05))
        self.training = True
        self.exploration = {
            role: {"epsilon": initial, "initial": initial, "final": final, "step": 0}
            for role in self.roles
        }
        self._trainer: Any = None
        self._diagnostics = DiagnosticCounters()

    @property
    def trainer(self) -> Any:
        if self._trainer is None:
            raise RuntimeError("the IQL trainer has not been attached")
        return self._trainer

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics

    def train(self, mode: bool = True) -> "IQLAlgorithm":
        self.training = bool(mode)
        self.uav_q.train(mode)
        self.vehicle_q.train(mode)
        self.uav_target_q.eval()
        self.vehicle_target_q.eval()
        return self

    def _masked_argmax(self, q: torch.Tensor, mask: Any) -> np.ndarray:
        mask_tensor = torch.as_tensor(mask, dtype=torch.bool, device=self.device)
        if mask_tensor.shape != q.shape or not mask_tensor.any(dim=-1).all():
            raise ValueError("each action row must have a legal masked action")
        return q.masked_fill(~mask_tensor, float("-inf")).argmax(dim=-1).detach().cpu().numpy().astype(np.int64)

    def _role_act(self, role: str, observations: Any, masks: Any, deterministic: bool) -> np.ndarray:
        network = self.uav_q if role == "uav" else self.vehicle_q
        q = network(torch.as_tensor(observations, dtype=torch.float32, device=self.device))
        actions = self._masked_argmax(q, masks)
        if not deterministic and self.training:
            state = self.exploration[role]
            legal = np.asarray(masks, dtype=bool)
            random_rows = np.random.random(len(actions)) < state["epsilon"]
            for index in np.flatnonzero(random_rows):
                actions[index] = int(np.random.choice(np.flatnonzero(legal[index])))
            state["step"] += 1
            state["epsilon"] = max(state["final"], state["epsilon"] * float(self.training_config.get("epsilon_decay", 0.999)))
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
        return {"actions": {role: result.actions[role].tolist() for role in self.roles}, "masks": result.masks, "exploration": deepcopy(self.exploration)}

    def observe(self, batch: OffPolicyEnvelope) -> None:
        if not isinstance(batch, OffPolicyEnvelope):
            raise TypeError("IQL observes only off-policy envelopes")
        self.uav_replay.append(batch)
        self.vehicle_replay.append(batch)
        self._diagnostics.increment("observed_transitions")

    def update(self) -> Mapping[str, Any]:
        if not len(self.uav_replay) or not len(self.vehicle_replay):
            raise RuntimeError("no off-policy transition is pending")
        rows = {
            "uav": self.uav_replay.sample(min(self.trainer.batch_size, len(self.uav_replay))),
            "vehicle": self.vehicle_replay.sample(min(self.trainer.batch_size, len(self.vehicle_replay))),
        }
        metrics = self.trainer.update(rows)
        self._diagnostics.increment("updates")
        return metrics

    def set_evaluation(self, enabled: bool) -> None:
        self.train(not bool(enabled))

    def state_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "g5-iql-state-v1",
            "method_id": self.method_id,
            "training_config": deepcopy(self.training_config),
            "training": self.training,
            "uav_q": self.uav_q.state_dict(),
            "vehicle_q": self.vehicle_q.state_dict(),
            "uav_target_q": self.uav_target_q.state_dict(),
            "vehicle_target_q": self.vehicle_target_q.state_dict(),
            "uav_replay": self.uav_replay.state_dict(),
            "vehicle_replay": self.vehicle_replay.state_dict(),
            "exploration": deepcopy(self.exploration),
            "diagnostics": self._diagnostics.state_dict(),
            "trainer": self.trainer.state_dict(),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        required = {"schema_version", "method_id", "training_config", "training", "uav_q", "vehicle_q", "uav_target_q", "vehicle_target_q", "uav_replay", "vehicle_replay", "exploration", "diagnostics", "trainer"}
        if not isinstance(state, Mapping) or set(state) != required or state.get("schema_version") != "g5-iql-state-v1":
            raise ValueError("invalid IQL state schema")
        if state["method_id"] != self.method_id or state["training_config"] != self.training_config:
            raise ValueError("IQL frozen configuration drift")
        if not isinstance(state["training"], (bool, np.bool_)):
            raise ValueError("IQL training flag must be boolean")
        exploration = state["exploration"]
        if not isinstance(exploration, Mapping) or set(exploration) != set(self.roles):
            raise ValueError("IQL exploration state must contain exact roles")
        for role in self.roles:
            item = exploration[role]
            if not isinstance(item, Mapping) or set(item) != {"epsilon", "initial", "final", "step"}:
                raise ValueError("IQL exploration state is incomplete")
            if any(not np.isfinite(float(item[name])) for name in ("epsilon", "initial", "final")):
                raise ValueError("IQL exploration values must be finite")
            if isinstance(item["step"], bool) or not isinstance(item["step"], int) or item["step"] < 0:
                raise ValueError("IQL exploration step must be nonnegative")

        modules = ((self.uav_q, "uav_q"), (self.vehicle_q, "vehicle_q"), (self.uav_target_q, "uav_target_q"), (self.vehicle_target_q, "vehicle_target_q"))
        clones = []
        try:
            for module, key in modules:
                clone = deepcopy(module)
                clone.load_state_dict(deepcopy(state[key]))
                clones.append((module, clone))
            uav_replay = JointReplayBuffer(self.uav_replay.capacity, seed=0)
            vehicle_replay = JointReplayBuffer(self.vehicle_replay.capacity, seed=1)
            uav_replay.load_state_dict(deepcopy(state["uav_replay"]))
            vehicle_replay.load_state_dict(deepcopy(state["vehicle_replay"]))
            diagnostics = DiagnosticCounters()
            diagnostics.load_state_dict(deepcopy(state["diagnostics"]))
            self.trainer.validate_state(state["trainer"])
        except (TypeError, ValueError, RuntimeError) as error:
            raise ValueError("invalid nested IQL state") from error
        for module, clone in clones:
            module.load_state_dict(clone.state_dict())
        self.uav_replay = uav_replay
        self.vehicle_replay = vehicle_replay
        self._diagnostics.load_state_dict(state["diagnostics"])
        self.trainer.load_state_dict(state["trainer"])
        self.exploration = deepcopy(dict(exploration))
        self.train(bool(state["training"]))


__all__ = ["IQLAlgorithm"]
