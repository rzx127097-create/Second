"""Common policy and action protocol used by training and evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Integral, Real
from typing import Any, Protocol

import numpy as np


class PolicyProtocol(Protocol):
    name: str

    def act(self, snapshot: Any) -> Mapping[str, str]:
        """Return legal high-level actions for the supplied decision snapshot."""


class HoldPolicy:
    """Deterministic baseline that holds every role slot."""

    name = "hold"

    def act(self, snapshot: Any, **_: Any) -> Mapping[str, str]:
        return {agent_id: "hold" for agent_id in sorted(snapshot.role_observations)}


def _role_ids(snapshot: Any, role: str) -> list[str]:
    return sorted(agent_id for agent_id, observation in snapshot.role_observations.items() if str(observation.get("role")) == role)


def actions_to_environment(snapshot: Any, actions: Mapping[str, Any]) -> dict[str, str]:
    """Convert numeric actor outputs to exact legal ActionMask action names."""
    by_agent: dict[str, Any] = {}
    for role in ("uav", "vehicle"):
        if role not in actions:
            continue
        ids = _role_ids(snapshot, role)
        values = np.asarray(actions[role]).reshape(-1)
        if len(values) != len(ids):
            raise ValueError(f"{role} action count does not match ScenarioBundle slots")
        by_agent.update(dict(zip(ids, values.tolist())))
    for agent_id, value in actions.items():
        if agent_id not in {"uav", "vehicle"}:
            by_agent[str(agent_id)] = value
    converted: dict[str, str] = {}
    for agent_id, mask in snapshot.action_masks.items():
        if agent_id not in by_agent:
            raise ValueError(f"policy omitted action for {agent_id}")
        value = by_agent[agent_id]
        if isinstance(value, (str, np.str_)):
            action = str(value)
            if action not in mask.actions or not mask.mask[mask.actions.index(action)]:
                raise ValueError(f"action is not legal for {agent_id}: {action}")
        else:
            if isinstance(value, (bool, np.bool_)):
                raise ValueError(f"invalid action index for {agent_id}: {value!r}")
            if isinstance(value, Real) and not isinstance(value, Integral) and not float(value).is_integer():
                raise ValueError(f"action index must be an integer for {agent_id}: {value!r}")
            try:
                index = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid action for {agent_id}: {value!r}") from exc
            if index < 0 or index >= len(mask.actions) or not mask.mask[index]:
                raise ValueError(f"action index is not legal for {agent_id}: {index}")
            action = str(mask.actions[index])
        converted[str(agent_id)] = action
    extra = set(by_agent) - set(snapshot.action_masks)
    if extra:
        raise ValueError(f"unknown policy agent IDs: {sorted(extra)}")
    return converted


class AlgorithmPolicyAdapter:
    """Adapt SR-MAPPO's role-batched numeric actor interface to this protocol."""

    def __init__(self, algorithm: Any, *, name: str = "SR-MAPPO") -> None:
        self.algorithm = algorithm
        self.name = name

    @property
    def training(self) -> bool:
        return bool(getattr(self.algorithm, "training", False))

    def eval(self) -> "AlgorithmPolicyAdapter":
        if hasattr(self.algorithm, "eval"):
            self.algorithm.eval()
        return self

    def train(self, mode: bool = True) -> "AlgorithmPolicyAdapter":
        if hasattr(self.algorithm, "train"):
            self.algorithm.train(mode)
        return self

    def act(self, snapshot: Any, *, deterministic: bool = True) -> Mapping[str, str]:
        role_ids = {role: _role_ids(snapshot, role) for role in ("uav", "vehicle")}
        observations = {role: np.asarray([snapshot.role_observations[agent_id]["vector"] for agent_id in ids], dtype=np.float32) for role, ids in role_ids.items()}
        masks = {role: np.asarray([snapshot.action_masks[agent_id].mask for agent_id in ids], dtype=bool) for role, ids in role_ids.items()}
        output = self.algorithm.evaluate(observations, masks) if deterministic and hasattr(self.algorithm, "evaluate") else self.algorithm.act(observations, masks, deterministic=deterministic)
        return actions_to_environment(snapshot, output)


__all__ = ["PolicyProtocol", "HoldPolicy", "AlgorithmPolicyAdapter", "actions_to_environment"]
