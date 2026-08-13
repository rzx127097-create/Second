"""Metric road executor with residual-distance carry-over."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from problem2.road.graph import RoadGraph


@dataclass(frozen=True)
class RoadAdvance:
    node: str
    residual_distance_m: float
    remaining_edge_distance_m: float
    travelled_distance_m: float
    on_road: bool
    route_complete: bool


class RoadVehicleExecutor:
    def __init__(self, road_graph: RoadGraph, *, current_node: str, speed_mps: float) -> None:
        if speed_mps <= 0:
            raise ValueError("vehicle speed must be positive")
        if not road_graph.has_node(current_node):
            raise ValueError("current vehicle node must belong to road graph")
        self.road_graph = road_graph
        self.current_node = current_node
        self.speed_mps = float(speed_mps)
        self.route: list[str] = [current_node]
        self.route_index = 0
        self.residual_distance_m = 0.0

    def set_route(self, route: Iterable[str]) -> None:
        values = [str(node) for node in route]
        if not values or values[0] != self.current_node:
            raise ValueError("route must start at current vehicle node")
        for left, right in zip(values, values[1:]):
            if not self.road_graph.has_node(left) or not self.road_graph.has_node(right):
                raise ValueError("route contains a node outside the road graph")
            try:
                self.road_graph.edge_weight(left, right)
            except KeyError as exc:
                raise ValueError("route contains an edge outside the road graph") from exc
        self.route = values
        self.route_index = 0
        self.residual_distance_m = 0.0

    def advance(self, *, dt_s: float) -> RoadAdvance:
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        budget = self.speed_mps * dt_s
        travelled = 0.0
        while self.route_index < len(self.route) - 1:
            source = self.route[self.route_index]
            target = self.route[self.route_index + 1]
            edge = self.road_graph.edge_weight(source, target)
            remaining_edge = edge - self.residual_distance_m
            if budget + 1e-12 < remaining_edge:
                self.residual_distance_m += budget
                travelled += budget
                budget = 0.0
                break
            budget -= remaining_edge
            travelled += remaining_edge
            self.current_node = target
            self.route_index += 1
            self.residual_distance_m = 0.0
        if self.route_index >= len(self.route) - 1:
            # Keep consumed budget out of the next route; a completed route is idle.
            self.residual_distance_m = 0.0
            remaining_edge = 0.0
        else:
            remaining_edge = max(
                0.0,
                self.road_graph.edge_weight(
                    self.route[self.route_index], self.route[self.route_index + 1]
                )
                - self.residual_distance_m,
            )
        return RoadAdvance(
            node=self.current_node,
            residual_distance_m=self.residual_distance_m,
            remaining_edge_distance_m=remaining_edge,
            travelled_distance_m=travelled,
            on_road=self.road_graph.has_node(self.current_node),
            route_complete=self.route_index >= len(self.route) - 1,
        )
