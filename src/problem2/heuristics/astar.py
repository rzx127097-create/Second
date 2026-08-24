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
        self.active_request_id: str | None = None
        self.active_sampled_slot: int | None = None
        self.selected_service_node: int | None = None
        self.cached_route_length_m = 0.0
        self.last_replan_step: int | None = None
        self.plan_version = 0

    def _record_plan(
        self,
        observation: DispatchObservation,
        *,
        request_id: str,
        sampled_slot: int,
        selected_service_node: int,
        route_length_m: float,
    ) -> None:
        self.active_request_id = request_id
        self.active_sampled_slot = sampled_slot
        self.selected_service_node = selected_service_node
        self.cached_route_length_m = route_length_m
        self.last_replan_step = observation.step
        self.plan_version += 1

    def state_dict(self) -> dict[str, int | float | str | None]:
        return {
            "active_request_id": self.active_request_id,
            "active_sampled_slot": self.active_sampled_slot,
            "cached_route_length_m": self.cached_route_length_m,
            "last_replan_step": self.last_replan_step,
            "plan_version": self.plan_version,
            "replan_interval_steps": self.replan_interval_steps,
            "selected_service_node": self.selected_service_node,
        }

    def decide(self, observation: DispatchObservation) -> ControllerDecision:
        started = perf_counter()
        if observation.active_request_id is not None:
            sampled_slot = int(observation.active_sampled_slot)
            service_node = int(observation.selected_service_node)
            same_dispatch = (
                self.active_request_id == observation.active_request_id
                and self.active_sampled_slot == sampled_slot
                and self.selected_service_node == service_node
            )
            replan_due = (
                not same_dispatch
                or self.last_replan_step is None
                or observation.step - self.last_replan_step
                >= self.replan_interval_steps
            )
            if replan_due:
                try:
                    distance = astar_distance(
                        observation.graph,
                        observation.vehicle.current_node,
                        service_node,
                    )
                except NoPathError:
                    distance = 0.0
                self._record_plan(
                    observation,
                    request_id=observation.active_request_id,
                    sampled_slot=sampled_slot,
                    selected_service_node=service_node,
                    route_length_m=distance,
                )
            return ControllerDecision(
                sampled_slot,
                observation.active_request_id,
                service_node,
                self.cached_route_length_m,
                perf_counter() - started,
                replanned=replan_due,
                plan_version=self.plan_version,
            )
        options = feasible_request_options(observation, astar_distance)
        if not options:
            self.active_request_id = None
            self.active_sampled_slot = None
            self.selected_service_node = None
            self.cached_route_length_m = 0.0
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
        self._record_plan(
            observation,
            request_id=request.request_id,
            sampled_slot=request.slot + 1,
            selected_service_node=node,
            route_length_m=distance,
        )
        return ControllerDecision(
            request.slot + 1,
            request.request_id,
            node,
            distance,
            perf_counter() - started,
            replanned=True,
            plan_version=self.plan_version,
        )


__all__ = ["RollingAStarController", "astar_path_and_distance"]
