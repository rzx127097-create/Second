"""Nearest feasible current-request controller."""

from __future__ import annotations

from time import perf_counter

from problem2.heuristics import (
    ControllerDecision,
    DispatchObservation,
    feasible_request_options,
    hold_decision,
)
from problem2.road.search import astar_distance


class NearestRequestController:
    def decide(self, observation: DispatchObservation) -> ControllerDecision:
        started = perf_counter()
        if observation.active_request_id is not None:
            distance = astar_distance(
                observation.graph,
                observation.vehicle.current_node,
                int(observation.selected_service_node),
            )
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
            key=lambda item: (item[2], item[0].request_id, item[0].uav_id, item[1]),
        )
        return ControllerDecision(
            request.slot + 1,
            request.request_id,
            node,
            distance,
            perf_counter() - started,
        )


__all__ = ["NearestRequestController"]
