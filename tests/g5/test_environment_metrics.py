from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms.protocol import ActionResult
from problem2.config import load_g2_config
from problem2.domain import (
    EpisodeState,
    Event,
    RequestStatus,
    ServiceRequest,
    UavState,
    VehicleState,
)
from problem2.evaluation.metrics import EpisodeMetrics
from problem2.evaluation.partitions import PartitionAccessError, assert_partition_allowed
from problem2.evaluation.runner import evaluate_episode
from problem2.resources.ledger import apply_transfer, new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG = load_g2_config(ROOT / "configs" / "problem2" / "g2_deterministic.yaml")
CONFIG = replace(
    BASE_CONFIG,
    vehicle_speed_mps=10.0,
    usable_capacity_l=1.0,
    transfer_rate_lpm=60.0,
    setup_time_s=0.0,
    service_cap_l=0.6,
    rendezvous_radius_m=1.0,
)


def _detour_fixture(*, vehicle_inventory_l: float = 0.4) -> tuple:
    graph = make_raster_graph(
        [(0, 0), (0, 1), (1, 1), (1, 2), (0, 2)],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        shape=(3, 3),
    )
    request = ServiceRequest("req-0", "uav-0", 0, requested_l=0.6)
    uav = UavState(
        "uav-0",
        x_m=float(graph.node_x_m[4]),
        y_m=float(graph.node_y_m[4]),
        pesticide_l=0.2,
        active_request_id=request.request_id,
    )
    vehicle = VehicleState(
        "vehicle-0",
        current_node=0,
        x_m=float(graph.node_x_m[0]),
        y_m=float(graph.node_y_m[0]),
        inventory_l=vehicle_inventory_l,
    )
    state = EpisodeState(
        step=0,
        uavs=(uav,),
        vehicle=vehicle,
        requests=(request,),
        ledger=new_ledger((uav,), vehicle.inventory_l),
    )
    return graph, state


def _action(view: dict, *, vehicle: int, uav: int = 4) -> ActionResult:
    return ActionResult(
        actions={"uav": np.asarray([uav]), "vehicle": np.asarray([vehicle])},
        masks=view["masks"],
    )


def test_adapter_preserves_sampled_slot_and_records_direct_road_dispatch_metric() -> None:
    graph, state = _detour_fixture()
    environment = Problem2CooperativeEnv(
        initial_state=state,
        graph=graph,
        config=CONFIG,
        max_steps=4,
        scenario_id=10000,
    )
    view = environment.reset()

    assert view["candidate_mapping"]["vehicle"] == ["req-0", None, None, None]
    assert view["masks"]["vehicle"].tolist() == [[True, True, False, False, False]]

    view = environment.step(_action(view, vehicle=1))
    dispatch = next(event for event in view["events"] if event.kind == "dispatch_reserved")
    payload = dict(dispatch.payload)
    assert payload == {
        "origin_current_node": 0,
        "origin_edge_progress_m": 0.0,
        "origin_target_node": None,
        "request_id": "req-0",
        "route_length_m": 40.0,
        "sampled_slot": 1,
        "selected_service_node": 4,
    }
    execution = next(
        event for event in view["events"] if event.kind == "vehicle_slot_executed"
    )
    assert dict(execution.payload)["sampled_slot"] == 1
    assert dict(execution.payload)["physical_direction"] == "RIGHT"
    assert view["sampled_actions"]["vehicle"].tolist() == [1]
    assert view["candidate_mapping"]["vehicle"] == ["req-0", None, None, None]
    assert view["masks"]["vehicle"].tolist() == [[False, True, False, False, False]]

    while not environment.state.terminated:
        view = environment.step(_action(view, vehicle=1))

    record = environment.episode_record()
    assert record.rendezvous_distance_m == pytest.approx(40.0)
    assert record.vehicle_service_travel_m == pytest.approx(40.0)
    assert record.completed_request_waiting_steps == 3
    assert record.waiting_steps == 3
    assert record.partial_service_count == 1
    assert record.zero_transfer_count == 0
    assert record.transferred_pesticide_l == pytest.approx(0.4)
    assert record.final_vehicle_inventory_l == pytest.approx(0.0)
    assert record.resource_residual_l == pytest.approx(0.0, abs=1e-12)
    assert record.reduction_rate is None
    assert record.success_at_0_85 is None
    assert not record.primary_outcomes_available


def test_active_dispatch_rejects_action_outside_stored_slot_mask_without_substitution() -> None:
    graph, state = _detour_fixture()
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=6, scenario_id=10000)
    view = environment.reset()
    view = environment.step(_action(view, vehicle=1))
    before = environment.state
    drifted_masks = {
        "uav": view["masks"]["uav"].copy(),
        "vehicle": np.asarray([[True, False, False, False, False]], dtype=bool),
    }
    illegal = ActionResult(
        actions={"uav": np.asarray([4]), "vehicle": np.asarray([0])},
        masks=drifted_masks,
    )

    with pytest.raises(ValueError, match="stored role mask"):
        environment.step(illegal)

    assert environment.state == before


def test_reserved_dispatch_waits_when_uav_is_outside_rendezvous_radius() -> None:
    graph, state = _detour_fixture()
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=6, scenario_id=10000)
    view = environment.reset()

    view = environment.step(_action(view, vehicle=1, uav=0))
    for _ in range(3):
        view = environment.step(_action(view, vehicle=1))

    assert environment.state.requests[0].status is RequestStatus.RESERVED
    assert environment.state.vehicle.current_node == 4
    assert environment.state.vehicle.mode.value == "idle"
    assert view["masks"]["vehicle"].tolist() == [[False, True, False, False, False]]
    assert not any(event.kind == "service_started" for event in view["events"])


def test_metrics_count_terminal_wait_by_elapsed_intervals_and_zero_transfer_explicitly() -> None:
    graph, state = _detour_fixture(vehicle_inventory_l=0.0)
    initial = replace(
        state,
        step=1,
        requests=(replace(state.requests[0], created_step=1),),
        ledger=new_ledger(state.uavs, 0.0),
    )
    cancelled = replace(
        initial,
        step=5,
        requests=(replace(initial.requests[0], status=RequestStatus.CANCELLED),),
        terminated=True,
    )
    full_uav = replace(initial.uavs[0], pesticide_l=CONFIG.usable_capacity_l)
    _, _, _, zero_transfer = apply_transfer(
        full_uav,
        0.5,
        new_ledger((full_uav,), 0.5),
        CONFIG.service_cap_l,
        CONFIG.usable_capacity_l,
        step=4,
    )
    metrics = EpisodeMetrics(initial)
    metrics.record_events((zero_transfer,))

    record = metrics.finalize(cancelled, terminal_boundary_step=5)

    assert record.waiting_steps == 4
    assert record.completed_request_waiting_steps == 0
    assert record.unresolved_terminal_requests == 1
    assert record.zero_transfer_count == 1
    assert record.transferred_pesticide_l == 0.0


def test_metrics_count_positive_spray_disabled_and_return_uav_time_from_real_events() -> None:
    graph = make_raster_graph([(0, 0)], [])
    uavs = (
        UavState("uav-0", 5.0, 35.0, pesticide_l=CONFIG.spray_per_step_l),
        UavState("uav-1", 5.0, 35.0, pesticide_l=0.0),
    )
    vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
    state = EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, 1.0))
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=1, scenario_id=10000)
    view = environment.reset()
    result = ActionResult(
        actions={"uav": np.asarray([5, 4]), "vehicle": np.asarray([0])},
        masks=view["masks"],
    )

    environment.step(result, returning_uav_ids=("uav-1",), decision_runtime_s=0.125)
    record = environment.episode_record()

    assert record.effective_spray_steps == 1
    assert record.pesticide_disabled_steps == 1
    assert record.return_steps == 1
    assert record.decision_runtime_s == pytest.approx(0.125)
    assert record.resource_residual_l == pytest.approx(0.0, abs=1e-12)


def test_primary_outcomes_require_complete_explicit_finite_pest_totals() -> None:
    _, state = _detour_fixture()
    final = replace(state, terminated=True)

    available = EpisodeMetrics(state).finalize(
        final,
        initial_total_pest=100.0,
        final_total_pest=10.0,
    )
    unavailable = EpisodeMetrics(state).finalize(final)

    assert available.reduction_rate == pytest.approx(0.9)
    assert available.success_at_0_85 is True
    assert available.primary_outcomes_available
    assert unavailable.reduction_rate is None
    assert unavailable.success_at_0_85 is None
    with pytest.raises(ValueError, match="both be supplied"):
        EpisodeMetrics(state).finalize(final, initial_total_pest=100.0)
    with pytest.raises(ValueError, match="finite"):
        EpisodeMetrics(state).finalize(
            final, initial_total_pest=float("nan"), final_total_pest=0.0
        )


class _FrozenPolicy:
    def __init__(self) -> None:
        self.training = True
        self.normalizer = np.asarray([3.0, 4.0])
        self.exploration = {"epsilon": 0.2, "step": 7}

    def set_evaluation(self, enabled: bool) -> None:
        self.training = not enabled

    def state_dict(self) -> dict:
        return {
            "training": self.training,
            "normalizer": self.normalizer.copy(),
            "exploration": dict(self.exploration),
        }

    def load_state_dict(self, state) -> None:
        self.training = bool(state["training"])
        self.normalizer = state["normalizer"].copy()
        self.exploration = dict(state["exploration"])

    def act(self, observations, masks, deterministic=False) -> ActionResult:
        if not deterministic:
            self.normalizer += 1.0
            self.exploration["step"] += 1
        actions = {
            role: np.asarray([np.flatnonzero(row)[0] for row in mask], dtype=np.int64)
            for role, mask in masks.items()
        }
        return ActionResult(actions=actions, masks=masks)


def test_evaluation_freezes_policy_state_and_partition_guard_fails_closed() -> None:
    graph = make_raster_graph([(0, 0)], [])
    uav = UavState("uav-0", 5.0, 35.0, pesticide_l=0.0)
    vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
    state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=1, scenario_id=10000)
    policy = _FrozenPolicy()

    record = evaluate_episode(
        environment,
        policy,
        partition="development",
        scenario_id=10000,
        deterministic=True,
    )

    assert record.evaluation_state_before == record.evaluation_state_after
    assert record.evaluation_state_byte_identical
    assert policy.training is True
    assert policy.exploration == {"epsilon": 0.2, "step": 7}
    assert policy.normalizer.tolist() == [3.0, 4.0]
    assert record.decision_runtime_s >= 0.0
    assert assert_partition_allowed("development", 10019) == "development"
    for partition, scenario_id in (
        ("development", 10020),
        ("validation", 20000),
        ("sealed_test", 30000),
        ("undeclared", 10000),
    ):
        with pytest.raises(PartitionAccessError):
            assert_partition_allowed(partition, scenario_id)


def test_evaluation_rejects_mutation_and_restores_original_policy_state() -> None:
    graph = make_raster_graph([(0, 0)], [])
    uav = UavState("uav-0", 5.0, 35.0, pesticide_l=0.0)
    vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
    state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=1, scenario_id=10000)
    policy = _FrozenPolicy()

    with pytest.raises(RuntimeError, match="mutated"):
        evaluate_episode(
            environment,
            policy,
            partition="development",
            scenario_id=10000,
            deterministic=False,
        )

    assert policy.training is True
    assert policy.normalizer.tolist() == [3.0, 4.0]
    assert policy.exploration == {"epsilon": 0.2, "step": 7}


class _ReorderedStatePolicy(_FrozenPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.state_calls = 0

    def state_dict(self) -> dict:
        self.state_calls += 1
        state = super().state_dict()
        if self.state_calls % 2 == 0:
            return {key: state[key] for key in reversed(tuple(state))}
        return state


def test_evaluation_identity_is_canonical_across_mapping_order() -> None:
    graph = make_raster_graph([(0, 0)], [])
    uav = UavState("uav-0", 5.0, 35.0, pesticide_l=0.0)
    vehicle = VehicleState("vehicle-0", 0, 5.0, 35.0, inventory_l=1.0)
    state = EpisodeState(0, (uav,), vehicle, ledger=new_ledger((uav,), 1.0))
    environment = Problem2CooperativeEnv(state, graph, CONFIG, max_steps=1, scenario_id=10000)

    record = evaluate_episode(
        environment,
        _ReorderedStatePolicy(),
        partition="development",
        scenario_id=10000,
    )

    assert record.evaluation_state_byte_identical
    assert record.evaluation_state_before == record.evaluation_state_after
