from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from problem2.domain import Action, RequestStatus, UavState, VehicleState
from problem2.road.models import RasterRoadGraph
from problem2.road.search import NoPathError, astar_distance


def _primary_nodes(graph: RasterRoadGraph) -> tuple[int, ...]:
    return tuple(
        node
        for node, (row, col) in enumerate(zip(graph.node_rows, graph.node_cols))
        if int(graph.component_id[int(row), int(col)]) == graph.primary_component_id
    )


@dataclass(frozen=True)
class FixedSupportPolicy:
    """Keep the support vehicle at its frozen initial road node."""

    def choose_vehicle_action(
        self,
        state: VehicleState,
        graph: RasterRoadGraph,
        *,
        requests: Iterable[object] = (),
        uavs: Iterable[UavState] = (),
    ) -> Action:
        return Action.STAY


@dataclass(frozen=True)
class MobileSupportPolicy:
    """Move along the road toward the oldest pending service request."""

    def choose_vehicle_action(
        self,
        state: VehicleState,
        graph: RasterRoadGraph,
        *,
        requests: Iterable[object] = (),
        uavs: Iterable[UavState] = (),
    ) -> Action:
        if state.mode.value == "serving":
            return Action.STAY
        if state.target_node is not None:
            if state.direction is None:
                return Action.STAY
            return state.direction
        uav_by_id = {uav.uav_id: uav for uav in uavs}
        pending = [
            request
            for request in requests
            if getattr(request, "status", None) is RequestStatus.PENDING
            and getattr(request, "uav_id", None) in uav_by_id
        ]
        if not pending:
            return Action.STAY
        request = min(
            pending,
            key=lambda item: (
                int(getattr(item, "created_step")),
                str(getattr(item, "uav_id")),
                str(getattr(item, "request_id")),
            ),
        )
        uav = uav_by_id[str(request.uav_id)]
        candidates = _primary_nodes(graph)
        target = min(
            candidates,
            key=lambda node: math.hypot(
                float(graph.node_x_m[node]) - uav.x_m,
                float(graph.node_y_m[node]) - uav.y_m,
            ),
        )
        if target == state.current_node and state.target_node is None:
            return Action.STAY
        origin = state.target_node if state.target_node is not None else state.current_node
        choices = []
        for neighbor, action, _ in graph.neighbors(origin):
            try:
                distance = astar_distance(graph, neighbor, target)
            except NoPathError:
                continue
            choices.append((distance, int(action), action))
        if not choices:
            return Action.STAY
        return min(choices, key=lambda item: (item[0], item[1]))[2]


__all__ = ["FixedSupportPolicy", "MobileSupportPolicy"]
