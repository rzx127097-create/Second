"""Rolling shortest-path dispatch baseline on the frozen road graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from problem2.road.shortest_path import shortest_path


@dataclass(frozen=True)
class RoutePlan:
    request_id: str
    path: list[str]
    distance_m: float


class RollingAStarPolicy:
    name = "rolling_astar"
    frozen = True

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def plan(self, current_node: str, requests: Iterable[Mapping[str, Any]]) -> RoutePlan | None:
        candidates = []
        for request in requests:
            target = request.get("target_node")
            if target is None:
                continue
            try:
                path, distance = shortest_path(self.graph, current_node, str(target))
            except ValueError:
                continue
            candidates.append((
                -float(request.get("urgency", 0.0)),
                int(request.get("created_step", 0)),
                str(request.get("request_id", "")),
                RoutePlan(str(request.get("request_id", "")), path, distance),
            ))
        return min(candidates, key=lambda item: item[:3])[3] if candidates else None

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if hasattr(observation, "role_observations"):
            from problem2.experiments.policy_protocol import actions_to_environment
            proposed = {agent_id: "hold" for agent_id in observation.role_observations}
            for vehicle_id, routes in observation.candidate_mapping.items():
                mask = observation.action_masks[vehicle_id]
                for slot, _ in routes:
                    if slot in mask.valid_actions:
                        proposed[vehicle_id] = slot
                        break
            return actions_to_environment(observation, proposed)
        vehicle = next((v for v in observation.values() if v.get("role") == "vehicle"), {})
        current = str(vehicle.get("road_node", vehicle.get("position", "")))
        plan = self.plan(current, observation.get("requests", []))
        return {str(vehicle.get("agent_id", "vehicle-1")): plan.path[1] if plan and len(plan.path) > 1 else "hold"}
