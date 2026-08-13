"""Consistency checks required by the Section 4.2 model contract."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from typing import Any, Mapping

from problem2.domain.resources import PesticideResources
from problem2.environment.action_masks import ActionMask
from problem2.road.graph import RoadGraph


@dataclass(frozen=True)
class AuditResult:
    ok: bool
    violations: tuple[str, ...]


class ConsistencyAuditor:
    def check(
        self,
        *,
        vehicle_positions: Mapping[str, str],
        road_graph: RoadGraph,
        service_assignments: Mapping[str, str],
        vehicle_assignments: Mapping[str, str],
        sampled_actions: Mapping[str, str],
        action_masks: Mapping[str, ActionMask],
        resources: PesticideResources,
    ) -> AuditResult:
        violations: list[str] = []
        for vehicle_id, node in vehicle_positions.items():
            if not road_graph.has_node(node):
                violations.append(f"vehicle_off_road:{vehicle_id}")
        vehicle_requests: list[str] = []
        for assignment in vehicle_assignments.values():
            if isinstance(assignment, str):
                vehicle_requests.append(assignment)
            elif isinstance(assignment, Iterable):
                assigned = [str(item) for item in assignment]
                vehicle_requests.extend(assigned)
                if len(assigned) > 1:
                    violations.append("vehicle_serves_multiple_requests")
            else:
                vehicle_requests.append(str(assignment))
        if len(vehicle_requests) != len(set(vehicle_requests)):
            violations.append("request_has_multiple_vehicles")
        service_request_ids = {str(request_id) for request_id in service_assignments}
        for request_id in vehicle_requests:
            if request_id not in service_request_ids:
                violations.append(f"service_assignment_mismatch:{request_id}")
        uav_requests: dict[str, int] = {}
        for uav_id in service_assignments.values():
            key = str(uav_id)
            uav_requests[key] = uav_requests.get(key, 0) + 1
        if any(count > 1 for count in uav_requests.values()):
            violations.append("uav_has_multiple_service_assignments")
        for agent_id, action in sampled_actions.items():
            mask = action_masks.get(agent_id)
            if mask is None or action not in mask.actions:
                violations.append(f"unknown_action:{agent_id}")
            elif not bool(mask.mask[mask.actions.index(action)]):
                violations.append(f"masked_action:{agent_id}:{action}")
        try:
            resources.assert_conservation()
        except AssertionError:
            violations.append("pesticide_conservation")
        return AuditResult(not violations, tuple(violations))
