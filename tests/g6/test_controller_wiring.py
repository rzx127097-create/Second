from __future__ import annotations

from dataclasses import replace

import numpy as np

from problem2.algorithms.protocol import ActionResult
from problem2.domain import EpisodeState, ServiceRequest, UavState, VehicleState
from problem2.heuristics import ControllerDecision
from problem2.resources.ledger import new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from problem2.training.conditions import resolve_condition_execution
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


class _MismatchedController(_SelectNodeController):
    def decide(self, observation):
        self.calls += 1
        return ControllerDecision(2, "wrong-request", self.node, 0.0, 0.0)


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


def test_controller_rejects_request_slot_identity_mismatch() -> None:
    graph = make_raster_graph([(0, 0), (0, 1)], [(0, 1)], shape=(1, 2))
    request = ServiceRequest("req-0", "uav-0", 0, requested_l=0.1)
    uav = UavState("uav-0", float(graph.node_x_m[1]), float(graph.node_y_m[1]), 0.0,
                   active_request_id=request.request_id)
    vehicle = VehicleState("vehicle-0", 0, float(graph.node_x_m[0]), float(graph.node_y_m[0]), 0.4)
    state = EpisodeState(0, (uav,), vehicle, (request,), new_ledger((uav,), vehicle.inventory_l))
    environment = Problem2CooperativeEnv(state, graph, replace(CONFIG, rendezvous_radius_m=2.0),
                                          max_steps=2, scenario_id=10000,
                                          vehicle_controller=_MismatchedController(1))
    view = environment.reset()
    result = ActionResult(actions={"uav": np.asarray([4]), "vehicle": np.asarray([1])}, masks=view["masks"])
    import pytest
    with pytest.raises(ValueError, match="mapping|request"):
        environment.step(result)


def test_mobile_condition_remains_learned_and_all_condition_semantics_are_frozen() -> None:
    expected = {
        "sr_mappo_mobile": ("learned", True),
        "sr_mappo_fixed": ("fixed_support", False),
        "sr_mappo_astar": ("rolling_astar", False),
        "sr_mappo_nearest": ("nearest_feasible", False),
        "sr_mappo_urgency": ("urgency_priority", False),
        "sr_mappo_two_stage": ("learned_two_stage", True),
    }
    for condition, semantics in expected.items():
        execution = resolve_condition_execution(condition)
        assert (execution.vehicle_controller, execution.vehicle_trainable) == semantics
