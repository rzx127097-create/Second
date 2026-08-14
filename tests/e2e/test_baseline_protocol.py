from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import numpy as np
import pytest

from problem2.baselines import PRIMARY_METHODS, make_policy
from problem2.experiments.evaluation import evaluate_policy
from problem2.scenarios.factory import build_synthetic_scenario
from problem2.environment.action_masks import ActionMask


ROOT = Path(__file__).parents[2]
CONFIG_DIR = ROOT / "configs"
METHODS = (
    "sr_mappo_mobile",
    "sr_mappo_fixed",
    "sr_mappo_astar",
    "mappo_mobile",
    "sr_mappo_two_stage",
)


def test_all_primary_methods_share_smoke_scenario_contract() -> None:
    records = []
    for method in METHODS:
        bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
        initial_resources = bundle.resources.total_pesticide_l
        policy = make_policy(method)
        before = (
            bundle.resources.total_pesticide_l,
            tuple((key, value.onboard_l) for key, value in sorted(bundle.resources.uavs.items())),
            tuple((key, value.inventory_l) for key, value in sorted(bundle.resources.vehicles.items())),
            tuple(sorted(bundle.adapter.state.vehicle_nodes.items())),
        )
        snapshot = bundle.reset()
        actions = policy.act(snapshot)
        after = (
            bundle.resources.total_pesticide_l,
            tuple((key, value.onboard_l) for key, value in sorted(bundle.resources.uavs.items())),
            tuple((key, value.inventory_l) for key, value in sorted(bundle.resources.vehicles.items())),
            tuple(sorted(bundle.adapter.state.vehicle_nodes.items())),
        )
        assert before == after
        bundle.step(actions)
        records.extend(evaluate_policy(policy, {"s1": bundle}, scenarios=["s1"], split="smoke", deterministic=True))
        assert bundle.resources.total_pesticide_l <= initial_resources + 1e-12
        assert bundle.resources.assert_conservation() is None
        assert getattr(policy, "smoke_only", False) is True

    assert {record.scenario_id for record in records} == {"s1"}
    assert len({record.steps for record in records}) == 1
    assert {record.pesticide_initial_l for record in records} == {records[0].pesticide_initial_l}
    assert len({tuple(sorted(record.agent_ids[role])) for record in records for role in ("uav", "vehicle")}) == 2


def test_unknown_and_diagnostic_methods_are_rejected_or_unregistered() -> None:
    assert set(PRIMARY_METHODS) == set(METHODS)
    with pytest.raises(ValueError, match="unknown policy method"):
        make_policy("teleport_service")
    with pytest.raises(ValueError, match="unknown policy method"):
        make_policy("does_not_exist")


def test_learned_policy_checkpoint_contract() -> None:
    policy = make_policy("sr_mappo_mobile")
    assert policy.smoke_only is True
    assert policy.formal_ready is False
    with pytest.raises(FileNotFoundError):
        make_policy("sr_mappo_mobile", checkpoint=ROOT / "missing-checkpoint.pt")


def test_smoke_actions_use_each_agents_own_first_legal_action() -> None:
    bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
    snapshot = bundle.reset()
    actions = ("up", "down", "left", "right", "hold", "spray")
    masks = dict(snapshot.action_masks)
    masks["uav-1"] = ActionMask(np.array([0, 0, 0, 0, 1, 0]), actions)
    masks["uav-2"] = ActionMask(np.array([0, 1, 0, 0, 0, 0]), actions)
    custom = replace(snapshot, action_masks=masks)
    policy = make_policy("sr_mappo_mobile")
    assert policy.act(custom)["uav-1"] == "hold"
    assert policy.act(custom)["uav-2"] == "down"


class _FakeAlgorithm:
    training = False

    def __init__(self):
        self.deterministic_values = []

    def act(self, observations, masks, deterministic=True):
        self.deterministic_values.append(deterministic)
        return {"uav": [5, 5], "vehicle": [1]}


def test_astar_checkpoint_uses_loaded_uav_and_current_candidate_vehicle(monkeypatch, tmp_path) -> None:
    bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"placeholder")
    policy = make_policy("sr_mappo_astar", checkpoint=checkpoint)
    called = []
    monkeypatch.setattr(policy, "_load_algorithm", lambda snapshot: called.append(snapshot) or _FakeAlgorithm())
    actions = policy.act(bundle.reset())
    assert called
    assert actions["uav-1"] == "spray"
    assert actions["uav-2"] == "spray"
    assert actions["vehicle-1"].startswith("slot-") or actions["vehicle-1"] == "hold"


def test_astar_rejects_learned_vehicle_slot_without_current_candidate(monkeypatch, tmp_path) -> None:
    bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"placeholder")
    policy = make_policy("sr_mappo_astar", checkpoint=checkpoint)
    fake = _FakeAlgorithm()
    monkeypatch.setattr(policy, "_load_algorithm", lambda snapshot: fake)
    snapshot = bundle.reset()
    snapshot = replace(snapshot, candidate_mapping={"vehicle-1": ()})
    actions = policy.act(snapshot, deterministic=False)
    assert actions["vehicle-1"] == "hold"
    assert fake.deterministic_values == [False]


def test_fixed_checkpoint_forces_vehicle_hold_and_retains_support_metadata(monkeypatch, tmp_path) -> None:
    bundle = build_synthetic_scenario("s1", seed=7, config_dir=CONFIG_DIR)
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"placeholder")
    policy = make_policy("sr_mappo_fixed", checkpoint=checkpoint)
    policy.support_node = "road-(0, 0)"
    policy.vehicle_id = "vehicle-1"
    monkeypatch.setattr(policy, "_load_algorithm", lambda snapshot: _FakeAlgorithm())
    actions = policy.act(bundle.reset())
    assert actions["vehicle-1"].startswith("slot-") or actions["vehicle-1"] == "hold"
    assert policy.support_node == "road-(0, 0)"
    assert policy.vehicle_id == "vehicle-1"


def test_learned_metadata_declares_stability_and_two_stage_protocol() -> None:
    mappo = make_policy("mappo_mobile")
    flags = mappo.metadata["stability_components"]
    assert flags["observation_normalization"] is False
    assert flags["return_normalization"] is False
    assert all(key in flags for key in ("orthogonal_initialization", "layer_normalization", "value_clipping", "huber_value_loss", "learning_rate_decay"))
    two_stage = make_policy("sr_mappo_two_stage")
    assert two_stage.metadata["initialization"] == "two_stage"
    assert two_stage.metadata["training_protocol"] == "two_stage"
    assert two_stage.smoke_only is True
