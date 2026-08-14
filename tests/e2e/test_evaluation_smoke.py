from __future__ import annotations

import pytest

from problem2.experiments.evaluation import evaluate_policy
from problem2.experiments.policy_protocol import HoldPolicy
from problem2.scenarios.factory import build_synthetic_scenario


CONFIG_DIR = "configs"


def _factory(scenario_id: str):
    return build_synthetic_scenario(scenario_id, seed=19, config_dir=CONFIG_DIR)


def _rows(records):
    rows = []
    for record in records:
        row = record.to_row()
        row.pop("events", None)
        rows.append(row)
    return rows


def test_deterministic_hold_evaluation_repeats_identical_rows_without_updates():
    policy = HoldPolicy()
    first = evaluate_policy(policy, _factory, scenarios=["s1"], split="smoke", deterministic=True)
    second = evaluate_policy(policy, _factory, scenarios=["s1"], split="smoke", deterministic=True)

    assert _rows(first) == _rows(second)
    assert first[0].to_row()["policy_name"] == "hold"
    assert first[0].to_row()["split"] == "smoke"
    assert first[0].to_row()["scenario_id"] == "s1"
    assert first[0].events == second[0].events


def test_formal_split_rejects_provisional_scenario():
    with pytest.raises(ValueError, match="provisional"):
        evaluate_policy(HoldPolicy(), _factory, scenarios=["s1"], split="validation", deterministic=True)


def test_numeric_policy_action_is_converted_and_invalid_index_rejected():
    from problem2.experiments.policy_protocol import actions_to_environment

    bundle = _factory("s1")
    snapshot = bundle.reset()
    valid = {"uav": [4, 4], "vehicle": [0]}
    converted = actions_to_environment(snapshot, valid)
    assert converted == {agent_id: "hold" for agent_id in converted}
    with pytest.raises(ValueError, match="not legal"):
        actions_to_environment(snapshot, {"uav": [99, 4], "vehicle": [0]})


def test_checkpoint_integrity_rejects_missing_and_bad_payload(tmp_path):
    from problem2.experiments.evaluation import load_evaluation_checkpoint

    with pytest.raises(FileNotFoundError):
        load_evaluation_checkpoint(tmp_path / "missing.pt", lambda: object())
    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"not-a-checkpoint")
    with pytest.raises(ValueError, match="invalid evaluation checkpoint"):
        load_evaluation_checkpoint(bad, lambda: object())
