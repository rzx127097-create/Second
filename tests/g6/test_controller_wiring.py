from __future__ import annotations

from dataclasses import replace

import numpy as np

from problem2.algorithms.protocol import ActionResult
from problem2.domain import EpisodeState, ServiceRequest, UavState, VehicleState
from problem2.heuristics import ControllerDecision
from problem2.resources.ledger import new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from tests.g2.helpers import make_raster_graph
from tests.g5.test_environment_metrics import CONFIG


class _SelectNodeController:
    def __init__(self, node: int) -> None:
        self.node = node
        self.calls = 0

    def decide(self, observation):
        self.calls += 1
        request = observation.requests[0]
        return ControllerDecision(
            sampled_slot=request.slot + 1,
            request_id=request.request_id,
            selected_service_node=self.node,
            route_length_m=0.0,
            decision_runtime_s=0.0,
        )


def test_nonlearned_controller_decision_selects_service_node() -> None:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (1, 1), (1, 2), (0, 2)],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        shape=(3, 3),
    )
    request = ServiceRequest("req-0", "uav-0", 0, requested_l=0.6)
    uav = UavState("uav-0", float(graph.node_x_m[4]), float(graph.node_y_m[4]), 0.2,
                   active_request_id=request.request_id)
    vehicle = VehicleState("vehicle-0", 0, float(graph.node_x_m[0]), float(graph.node_y_m[0]), 0.4)
    state = EpisodeState(0, (uav,), vehicle, (request,), new_ledger((uav,), vehicle.inventory_l))
    controller = _SelectNodeController(2)
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=2, scenario_id=10000,
                                          vehicle_controller=controller)
    view = environment.reset()
    result = ActionResult(actions={"uav": np.asarray([4]), "vehicle": np.asarray([1])}, masks=view["masks"])
    next_view = environment.step(result)
    dispatch = next(event for event in next_view["events"] if event.kind == "dispatch_reserved")
    assert dict(dispatch.payload)["selected_service_node"] == 2
    assert controller.calls == 1

