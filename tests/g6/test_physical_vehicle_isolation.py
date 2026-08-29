from copy import deepcopy
from pathlib import Path

import numpy as np

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import ActionResult
from problem2.experiments.g5_contract import load_g5_contract
from problem2.training.physical_training import (
    _observe_physical_algorithm,
    _update_physical_algorithm,
    build_physical_envelope,
)
from problem2.training import physical_training
from problem2.training.tuning import build_development_environment


ROOT = Path(__file__).resolve().parents[2]


def _transition(method: str):
    contract = load_g5_contract(ROOT)
    environment = build_development_environment(ROOT, scenario_id=10000, scale="g20x20_d2")
    algorithm = build_algorithm(method, contract, "cpu", candidate_id="c01", scale="g20x20_d2")
    current = environment.reset(scenario_id=10000)
    details = algorithm.act(current["observations"], current["masks"], return_details=True)
    action_result = ActionResult(actions=details["actions"], masks=details["masks"])
    next_view = environment.step(action_result)
    return algorithm, current, next_view, details


def test_physical_envelope_binds_controller_executed_vehicle_slot() -> None:
    algorithm, current, next_view, details = _transition("sr_mappo_mobile")
    sampled = int(np.asarray(details["actions"]["vehicle"]).reshape(-1)[0])
    # Use a synthetic controller candidate on this no-request initial view.
    # The mask/mapping remain protocol-valid while the executed slot differs.
    executed = 1
    current = dict(current)
    current["masks"] = {**current["masks"], "vehicle": np.asarray([[True, True, False, False, False]])}
    current["candidate_mapping"] = {"vehicle": ["controller-request", None, None, None]}
    details = {**details, "masks": {**details["masks"], "vehicle": current["masks"]["vehicle"]}}
    next_view = dict(next_view)
    next_view["sampled_actions"] = {
        **next_view["sampled_actions"],
        "vehicle": np.asarray([executed], dtype=np.int64),
    }

    envelope = build_physical_envelope(
        algorithm,
        current,
        next_view,
        details,
        team_reward=next_view["team_reward"],
        transition_index=0,
        vehicle_trainable=False,
    )

    assert int(envelope.role_batch.actions["vehicle"][0]) == executed
    assert int(envelope.role_batch.actions["vehicle"][0]) != sampled


def test_non_trainable_iql_observation_does_not_append_vehicle_replay() -> None:
    algorithm, current, next_view, details = _transition("iql_mobile")
    envelope = build_physical_envelope(
        algorithm,
        current,
        next_view,
        details,
        team_reward=next_view["team_reward"],
        transition_index=0,
        vehicle_trainable=False,
    )
    _observe_physical_algorithm(algorithm, envelope, vehicle_trainable=False)

    assert len(algorithm.uav_replay) == 1
    assert len(algorithm.vehicle_replay) == 0


def test_non_trainable_sr_update_preserves_vehicle_optimizer_state() -> None:
    algorithm, current, next_view, details = _transition("sr_mappo_mobile")
    envelope = build_physical_envelope(
        algorithm,
        current,
        next_view,
        details,
        team_reward=next_view["team_reward"],
        transition_index=0,
        vehicle_trainable=False,
    )
    algorithm.observe(envelope)
    before_vehicle = deepcopy(algorithm.vehicle_actor.state_dict())
    before_trainer = deepcopy(algorithm.trainer.state_dict())

    _update_physical_algorithm(algorithm, vehicle_trainable=False)

    assert all(np.array_equal(value.detach().cpu().numpy(), before_vehicle[key].detach().cpu().numpy()) for key, value in algorithm.vehicle_actor.state_dict().items())
    after_trainer = algorithm.trainer.state_dict()
    assert after_trainer["optimizers"]["vehicle"] == before_trainer["optimizers"]["vehicle"]
    assert after_trainer["schedulers"]["vehicle"] == before_trainer["schedulers"]["vehicle"]


def test_physical_runner_routes_non_trainable_observation_through_isolation_boundary(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []
    real_observe = physical_training._observe_physical_algorithm

    def observe(algorithm, envelope, *, vehicle_trainable):
        calls.append((algorithm.method_id, vehicle_trainable))
        return real_observe(algorithm, envelope, vehicle_trainable=vehicle_trainable)

    monkeypatch.setattr(physical_training, "_observe_physical_algorithm", observe)
    job = {
        "source_root": ROOT,
        "method": "iql_mobile",
        "condition_id": "sr_mappo_fixed",
        "vehicle_controller": "fixed_support",
        "vehicle_trainable": False,
        "training_mode": "uav_only",
        "candidate_id": "c01",
        "partition": "development",
        "scenario_id": 10000,
        "scenario_ids": list(range(10000, 10020)),
        "training_seed": 51001,
        "scale": "g20x20_d2",
    }
    physical_training.run_noncanonical_physical_candidate_training_for_test(
        job, "cpu", 1, tmp_path / "runner"
    )
    assert calls == [("iql_mobile", False)]
