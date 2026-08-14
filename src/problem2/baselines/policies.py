"""Fair common-policy adapters for smoke and formal evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from problem2.experiments.methods import PRIMARY_METHODS, STABILITY_COMPONENTS
from problem2.experiments.policy_protocol import PolicyProtocol, actions_to_environment


class _SnapshotPolicy:
    """Deterministic legal-action policy used only when no checkpoint is supplied."""

    frozen = True
    smoke_only = True
    formal_ready = False

    def __init__(self, name: str, *, checkpoint: Path | None = None, metadata: Mapping[str, Any] | None = None) -> None:
        self.name = name
        self.checkpoint = checkpoint
        self.metadata = dict(metadata or {})
        self.smoke_only = checkpoint is None
        self.formal_ready = checkpoint is not None
        self._algorithm: Any | None = None

    @property
    def training(self) -> bool:
        return False

    def eval(self) -> "_SnapshotPolicy":
        return self

    def train(self, mode: bool = True) -> "_SnapshotPolicy":
        if mode:
            raise ValueError("baseline policies are frozen")
        return self

    @staticmethod
    def _legal(snapshot: Any, agent_id: str) -> str:
        mask = snapshot.action_masks[agent_id]
        return str(mask.valid_actions[0])

    def _smoke_actions(self, snapshot: Any) -> dict[str, str]:
        proposed = {
            agent_id: self._legal(snapshot, agent_id)
            for agent_id in snapshot.role_observations
        }
        return actions_to_environment(snapshot, proposed)

    def _learned_actions(
        self,
        snapshot: Any,
        algorithm: Any,
        *,
        deterministic: bool = True,
        force_vehicle_hold: bool = False,
    ) -> dict[str, str]:
        observations = {
            role: [snapshot.role_observations[agent_id]["vector"] for agent_id, obs in snapshot.role_observations.items() if str(obs.get("role")) == role]
            for role in ("uav", "vehicle")
        }
        masks = {
            role: [snapshot.action_masks[agent_id].mask for agent_id, obs in snapshot.role_observations.items() if str(obs.get("role")) == role]
            for role in ("uav", "vehicle")
        }
        sampled = dict(algorithm.act(observations, masks, deterministic=deterministic))
        if force_vehicle_hold:
            sampled["vehicle"] = [
                "hold"
                for observation in snapshot.role_observations.values()
                if str(observation.get("role")) == "vehicle"
            ]
        return actions_to_environment(snapshot, sampled)

    def _load_algorithm(self, snapshot: Any) -> Any:
        if self._algorithm is not None:
            return self._algorithm
        if self.checkpoint is None:
            return None
        from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
        from problem2.experiments.evaluation import load_evaluation_checkpoint

        role_ids = {
            role: sorted(agent_id for agent_id, obs in snapshot.role_observations.items() if str(obs.get("role")) == role)
            for role in ("uav", "vehicle")
        }
        uav_dim = len(snapshot.role_observations[role_ids["uav"][0]]["vector"])
        vehicle_dim = len(snapshot.role_observations[role_ids["vehicle"][0]]["vector"])
        state_dim = len(snapshot.critic_state["vector"])
        action_dims = {
            role: len(snapshot.action_masks[role_ids[role][0]].actions)
            for role in ("uav", "vehicle")
        }
        factory = lambda: SRMAPPOAlgorithm(
            uav_dim,
            vehicle_dim,
            state_dim,
            action_dims["uav"],
            action_dims["vehicle"],
            stability_components=self.metadata.get("stability_components"),
        )
        self._algorithm, _ = load_evaluation_checkpoint(self.checkpoint, factory)
        return self._algorithm

    def act(self, snapshot: Any, *, deterministic: bool = True) -> Mapping[str, str]:
        if self.checkpoint is None:
            return self._smoke_actions(snapshot)
        algorithm = self._load_algorithm(snapshot)
        return self._learned_actions(snapshot, algorithm, deterministic=deterministic)


class FixedSupportPolicy(_SnapshotPolicy):
    def __init__(self, *, support_node: str = "road-(0, 0)", vehicle_id: str | None = None, **kwargs: Any) -> None:
        super().__init__("sr_mappo_fixed", **kwargs)
        self.support_node = str(support_node)
        self.vehicle_id = vehicle_id

    def act(self, snapshot: Any, *, deterministic: bool = True) -> Mapping[str, str]:
        if self.checkpoint is None:
            proposed = self._smoke_actions(snapshot)
        else:
            proposed = self._learned_actions(
                snapshot,
                self._load_algorithm(snapshot),
                deterministic=deterministic,
                force_vehicle_hold=True,
            )
        for vehicle_id, observation in snapshot.role_observations.items():
            if str(observation.get("role")) == "vehicle":
                mask = snapshot.action_masks[vehicle_id]
                routes = snapshot.candidate_mapping.get(vehicle_id, ())
                proposed[vehicle_id] = next(
                    (str(slot) for slot, _ in routes if str(slot) in mask.valid_actions),
                    "hold",
                )
        return actions_to_environment(snapshot, proposed)


class RollingAStarAdapter(_SnapshotPolicy):
    def act(self, snapshot: Any, *, deterministic: bool = True) -> Mapping[str, str]:
        # Candidate routes are the only route information exposed to this policy.
        proposed = (
            self._smoke_actions(snapshot)
            if self.checkpoint is None
            else self._learned_actions(
                snapshot,
                self._load_algorithm(snapshot),
                deterministic=deterministic,
                force_vehicle_hold=True,
            )
        )
        vehicle_ids = [
            agent_id for agent_id, observation in snapshot.role_observations.items()
            if str(observation.get("role")) == "vehicle"
        ]
        for vehicle_id in vehicle_ids:
            routes = snapshot.candidate_mapping.get(vehicle_id, ())
            mask = snapshot.action_masks[vehicle_id]
            valid_slots = [str(slot) for slot, _ in routes if str(slot) in mask.valid_actions]
            proposed[vehicle_id] = valid_slots[0] if valid_slots else "hold"
        return actions_to_environment(snapshot, proposed)


def make_policy(method: str, checkpoint: Path | None = None) -> PolicyProtocol:
    """Construct one of the five registered, resource-neutral policy adapters."""
    method = str(method)
    if method not in PRIMARY_METHODS:
        raise ValueError(f"unknown policy method: {method}")
    if checkpoint is not None:
        checkpoint = Path(checkpoint)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"checkpoint does not exist: {checkpoint}")
    metadata = {
        "method": method,
        "formal": checkpoint is not None,
        "stability_components": {component: True for component in STABILITY_COMPONENTS},
    }
    if method == "sr_mappo_fixed":
        return FixedSupportPolicy(checkpoint=checkpoint, metadata=metadata)
    if method == "sr_mappo_astar":
        policy = RollingAStarAdapter(method, checkpoint=checkpoint, metadata=metadata)
        policy.name = method
        return policy
    if method == "mappo_mobile":
        metadata["algorithm_family"] = "same_source_heterogeneous_mappo"
        metadata["stability_components"] = {component: False for component in STABILITY_COMPONENTS}
    if method == "sr_mappo_two_stage":
        metadata["initialization"] = "two_stage"
        metadata["training_protocol"] = "two_stage"
    return _SnapshotPolicy(method, checkpoint=checkpoint, metadata=metadata)


__all__ = ["PRIMARY_METHODS", "STABILITY_COMPONENTS", "make_policy", "FixedSupportPolicy", "RollingAStarAdapter"]
