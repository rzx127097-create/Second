"""MAPPO adapter over the accepted heterogeneous SR-MAPPO implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm


class MAPPOAlgorithm(SRMAPPOAlgorithm):
    """The same centralized PPO implementation with SR stability flags off."""

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
        training_config: Mapping[str, Any] | None = None,
    ) -> None:
        flags = dict(stability_components or {})
        if not flags or any(flags.values()):
            raise ValueError("same-source MAPPO requires every frozen SR stability flag off")
        super().__init__(
            uav_obs_dim=uav_obs_dim,
            vehicle_obs_dim=vehicle_obs_dim,
            state_dim=state_dim,
            uav_action_dim=uav_action_dim,
            vehicle_action_dim=vehicle_action_dim,
            hidden_dim=hidden_dim,
            device=device,
            stability_components=flags,
            method_id="mappo_mobile",
            training_config=training_config,
        )


__all__ = ["MAPPOAlgorithm"]
