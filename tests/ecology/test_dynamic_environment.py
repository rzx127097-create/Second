from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms.protocol import ActionResult
from problem2.config import load_g2_config
from problem2.domain import EpisodeState, Event, UavState, VehicleState
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.scenario import generate_dynamic_scenario
from problem2.ecology.system import DynamicEcologySystem
from problem2.resources.ledger import new_ledger
from problem2.training.cooperative_env import Problem2CooperativeEnv
from problem2.training.dynamic_env import DynamicPestEnvironment
from tests.g2.helpers import make_raster_graph


ROOT = Path(__file__).resolve().parents[2]
G2 = load_g2_config(ROOT / "configs/problem2/g2_deterministic.yaml")
ECOLOGY = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def _physical(*, first_pesticide: float = 0.2875, second_pesticide: float = 0.0) -> Problem2CooperativeEnv:
    graph = make_raster_graph([(0, 0)], [], shape=(1, 1))
    uavs = (
        UavState("uav-0", 5.0, 5.0, first_pesticide),
        UavState("uav-1", 5.0, 5.0, second_pesticide),
    )
    vehicle = VehicleState("vehicle-0", 0, 5.0, 5.0, inventory_l=1.0)
    return Problem2CooperativeEnv(
        EpisodeState(0, uavs, vehicle, ledger=new_ledger(uavs, vehicle.inventory_l)),
        graph,
        G2,
        max_steps=4,
        scenario_id=10000,
    )


def _dynamic_environment(*, first_pesticide: float = 0.2875, second_pesticide: float = 0.0) -> DynamicPestEnvironment:
    scenario = generate_dynamic_scenario("development", 10000, "fixture", (4, 4), ECOLOGY)
    ecology = DynamicEcologySystem.from_scenario(scenario, ECOLOGY, 0.2875)
    return DynamicPestEnvironment(
        _physical(first_pesticide=first_pesticide, second_pesticide=second_pesticide),
        ecology,
        partition="development",
        source_provenance={"fixture": True},
    )


def _action(view: dict, uav_actions: list[int]) -> ActionResult:
    return ActionResult(
        actions={"uav": np.asarray(uav_actions), "vehicle": np.asarray([0])},
        masks=view["masks"],
    )


def _equal(left: object, right: object) -> None:
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        assert isinstance(left, np.ndarray) and isinstance(right, np.ndarray)
        assert left.dtype == right.dtype
        assert np.array_equal(left, right)
        return
    if isinstance(left, dict) or isinstance(right, dict):
        assert isinstance(left, dict) and isinstance(right, dict)
        assert left.keys() == right.keys()
        for key in left:
            _equal(left[key], right[key])
        return
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        assert type(left) is type(right)
        assert len(left) == len(right)  # type: ignore[arg-type]
        for a, b in zip(left, right):  # type: ignore[arg-type]
            _equal(a, b)
        return
    assert left == right


class _ZeroSprayEventPhysical(Problem2CooperativeEnv):
    def step(self, action_result: ActionResult, **kwargs: object) -> dict:
        view = super().step(action_result, **kwargs)
        view["events"] = tuple(view["events"]) + (
            Event(0, "spray", "spray", "uav-1", (("delta_l", 0.0),)),
        )
        return view


def test_only_positive_finite_physical_spray_events_are_deposited() -> None:
    base = _physical()
    base.__class__ = _ZeroSprayEventPhysical
    scenario = generate_dynamic_scenario("development", 10000, "fixture", (4, 4), ECOLOGY)
    ecology = DynamicEcologySystem.from_scenario(scenario, ECOLOGY, 0.2875)
    environment = DynamicPestEnvironment(base, ecology, partition="development", source_provenance={})
    view = environment.reset(scenario_id=10000)

    next_view = environment.step(_action(view, [5, 0]))

    assert int(ecology.spray_count.sum()) == 1
    assert ecology.concentration[2, 2] > 0.0
    assert environment.spray_action_count == 1
    assert environment.sprayed_pesticide_l == pytest.approx(G2.spray_per_step_l)
    assert next_view["metric_source"] == "dynamic_ecology_environment"
    assert next_view["ecology_dynamic_step_count"] == 1


def test_no_spray_growth_produces_signed_negative_reward_and_growth_endpoint() -> None:
    environment = _dynamic_environment(first_pesticide=0.0, second_pesticide=0.0)
    environment.ecology._prey[...] = 0.1
    environment.ecology._predator[...] = 0.001
    view = environment.reset(scenario_id=10000)

    next_view = environment.step(_action(view, [0, 0]))

    assert next_view["team_reward"] < 0.0
    assert environment.prey.sum() > environment.initial_prey.sum()
    assert next_view["final_total_pest"] > next_view["initial_total_pest"]


def test_matched_spray_trajectory_reduces_prey_more_than_no_spray() -> None:
    sprayed = _dynamic_environment()
    held = _dynamic_environment()
    sprayed.ecology._prey[...] = 0.1
    held.ecology._prey[...] = 0.1
    sprayed.ecology._predator[...] = 0.001
    held.ecology._predator[...] = 0.001
    sprayed_view = sprayed.reset(scenario_id=10000)
    held_view = held.reset(scenario_id=10000)

    sprayed_next = sprayed.step(_action(sprayed_view, [5, 0]))
    held_next = held.step(_action(held_view, [0, 0]))

    assert sprayed_next["final_total_pest"] < held_next["final_total_pest"]
    assert sprayed_next["team_reward"] > held_next["team_reward"]


def test_ecology_effect_does_not_change_physical_pesticide_conservation() -> None:
    environment = _dynamic_environment()
    view = environment.reset(scenario_id=10000)
    initial_total = environment.physical.state.ledger.initial_total_l

    environment.step(_action(view, [5, 0]))

    ledger = environment.physical.state.ledger
    observed = sum(uav.pesticide_l for uav in environment.physical.state.uavs) + environment.physical.state.vehicle.inventory_l
    expected = initial_total - ledger.cumulative_sprayed_l
    assert abs(observed - expected) <= G2.tolerance
    assert environment.field_summary[0] == pytest.approx(environment.prey.mean())


def test_wrapper_state_restore_reproduces_uninterrupted_transitions() -> None:
    left = _dynamic_environment()
    first = left.reset(scenario_id=10000)
    left.step(_action(first, [5, 0]))
    snapshot = left.state_dict()
    left_next = left.step(_action(left._current_view, [4, 4]))

    right = _dynamic_environment()
    right.load_state_dict(snapshot)
    right_next = right.step(_action(right._current_view, [4, 4]))

    _equal(left_next, right_next)
    _equal(left.ecology.state_dict(), right.ecology.state_dict())
    assert left.physical.state == right.physical.state


def test_wrapper_state_restore_preserves_the_current_view_exactly() -> None:
    left = _dynamic_environment()
    view = left.reset(scenario_id=10000)
    left.step(_action(view, [5, 4]))
    snapshot = left.state_dict()

    right = _dynamic_environment()
    right.load_state_dict(snapshot)

    _equal(snapshot["current_view"], right._current_view)
    _equal(left._current_view, right._current_view)
    for role in ("uav", "vehicle"):
        assert left._current_view["observations"][role].tobytes() == right._current_view["observations"][role].tobytes()


def test_static_diagnostic_requires_explicit_development_scope(tmp_path: Path) -> None:
    from problem2.training.tuning import build_static_diagnostic_environment

    with pytest.raises(ValueError, match="static_ecology_diagnostic"):
        build_static_diagnostic_environment(
            ROOT,
            scenario_id=10000,
            scale="g20x20_d2",
            partition="development",
            purpose="wrong",
            output_root=tmp_path,
        )
    with pytest.raises(ValueError, match="outside"):
        build_static_diagnostic_environment(
            ROOT,
            scenario_id=10000,
            scale="g20x20_d2",
            partition="development",
            purpose="static_ecology_diagnostic",
            output_root=ROOT / "outputs/problem2_sr_mappo_v1/g5/validation",
        )


def test_static_adapter_cannot_bypass_diagnostic_scope_or_output_root() -> None:
    from problem2.training.tuning import ActionDrivenValidationEnv

    base = _physical()
    with pytest.raises(TypeError, match="_internal_legacy"):
        ActionDrivenValidationEnv(
            base,
            initial_pest=np.ones((1, 1)),
            mortality_per_l=1.0,
            partition="development",
            purpose="static_ecology_diagnostic",
            output_root=ROOT / "outputs/problem2_sr_mappo_v1/static_diagnostic",
            repository_root=ROOT,
            _internal_legacy=True,
        )
    with pytest.raises(ValueError, match="repository_root"):
        ActionDrivenValidationEnv(
            base,
            initial_pest=np.ones((1, 1)),
            mortality_per_l=1.0,
            partition="development",
            purpose="static_ecology_diagnostic",
            output_root=ROOT / "outputs/problem2_sr_mappo_v1/g5/validation",
        )
