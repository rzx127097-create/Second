"""Resource-matched stationary support baseline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from problem2.experiments.policy_protocol import actions_to_environment


class FixedSupportBaseline:
    name = "fixed_support"
    frozen = True

    def __init__(self, support_node: str, vehicle_id: str | None = None) -> None:
        if not support_node:
            raise ValueError("support_node is required")
        self.support_node = str(support_node)
        self.vehicle_id = vehicle_id

    def act(self, observations: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
        if hasattr(observations, "role_observations"):
            snapshot = observations
            proposed = {agent_id: "hold" for agent_id in snapshot.role_observations}
            return actions_to_environment(snapshot, proposed)
        actions: dict[str, str] = {}
        for agent_id, data in observations.items():
            if data.get("role") != "vehicle":
                actions[agent_id] = "spray"
                continue
            if self.vehicle_id is not None and agent_id != self.vehicle_id:
                actions[agent_id] = "hold"
                continue
            position = data.get("position", data.get("node_id"))
            open_requests = data.get("open_requests") or data.get("requests") or []
            if position != self.support_node:
                actions[agent_id] = "return_to_support"
            elif open_requests:
                actions[agent_id] = "next_request_slot"
            else:
                actions[agent_id] = "hold"
        return actions

    __call__ = act
