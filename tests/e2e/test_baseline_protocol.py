from __future__ import annotations

from pathlib import Path

import pytest

from problem2.baselines import PRIMARY_METHODS, make_policy
from problem2.experiments.evaluation import evaluate_policy
from problem2.scenarios.factory import build_synthetic_scenario


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
