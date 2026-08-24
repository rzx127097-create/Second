"""Deterministic urgency-aware rolling A* dispatch."""

from __future__ import annotations

import heapq
import math
from time import perf_counter

from problem2.heuristics import (
    ControllerDecision,
    DispatchObservation,
    feasible_request_options,
    hold_decision,
)
from problem2.road.models import RasterRoadGraph
from problem2.road.search import NoPathError, astar_distance


def _heuristic(graph: RasterRoadGraph, node: int, goal: int) -> float:
    row = abs(int(graph.node_rows[node]) - int(graph.node_rows[goal]))
    col = abs(int(graph.node_cols[node]) - int(graph.node_cols[goal]))
    return row * graph.cell_height_m + col * graph.cell_width_m


def astar_path_and_distance(
    graph: RasterRoadGraph, start: int, goal: int
) -> tuple[tuple[int, ...], float]:
    distance = astar_distance(graph, start, goal)
    if start == goal:
        return (start,), distance
    best = {start: 0.0}
    parent: dict[int, int] = {}
    queue: list[tuple[float, float, int]] = [(_heuristic(graph, start, goal), 0.0, start)]
    while queue:
        _, travelled, node = heapq.heappop(queue)
        if travelled != best.get(node):
            continue
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parent[path[-1]])
            path.reverse()
            return tuple(path), distance
        for neighbor, _, edge_length in graph.neighbors(node):
            candidate = travelled + edge_length
            previous = best.get(neighbor, math.inf)
            if candidate < previous or (
                math.isclose(candidate, previous, rel_tol=0.0, abs_tol=1e-12)
                and node < parent.get(neighbor, node + 1)
            ):
                best[neighbor] = candidate
                parent[neighbor] = node
                heapq.heappush(
                    queue,
                    (candidate + _heuristic(graph, neighbor, goal), candidate, neighbor),
                )
    raise NoPathError(f"no path from road node {start} to {goal}")


class RollingAStarController:
    def __init__(self, *, replan_interval_steps: int) -> None:
        if (
            isinstance(replan_interval_steps, bool)
            or not isinstance(replan_interval_steps, int)
            or replan_interval_steps <= 0
        ):
            raise ValueError("replan_interval_steps must be a positive integer")
        self.replan_interval_steps = replan_interval_steps

    def decide(self, observation: DispatchObservation) -> ControllerDecision:
        started = perf_counter()
        if observation.active_request_id is not None:
            try:
                distance = astar_distance(
                    observation.graph,
                    observation.vehicle.current_node,
                    int(observation.selected_service_node),
                )
            except NoPathError:
                distance = 0.0
            return ControllerDecision(
                int(observation.active_sampled_slot),
                observation.active_request_id,
                int(observation.selected_service_node),
                distance,
                perf_counter() - started,
            )
        options = feasible_request_options(observation, astar_distance)
        if not options:
            return hold_decision(perf_counter() - started)
        request, node, distance = min(
            options,
            key=lambda item: (
                item[0].endurance_steps - item[2] / observation.vehicle_speed_mps,
                -(observation.step - item[0].created_step),
                item[2],
                item[0].request_id,
                item[1],
            ),
        )
        return ControllerDecision(
            request.slot + 1,
            request.request_id,
            node,
            distance,
            perf_counter() - started,
        )


__all__ = ["RollingAStarController", "astar_path_and_distance"]
