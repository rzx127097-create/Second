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


def test_sealed_test_requires_deterministic_frozen_policy():
    with pytest.raises(ValueError, match="deterministic"):
        evaluate_policy(HoldPolicy(), _factory, scenarios=["s1"], split="sealed_test", deterministic=False)
    with pytest.raises(ValueError, match="frozen"):
        evaluate_policy(HoldPolicy(), _factory, scenarios=["s1"], split="sealed_test", deterministic=True)


def test_sealed_test_rejects_mutable_named_policy_on_verified_bundle():
    class MutablePolicy:
        name = "mutable"
        frozen = False
        training = True

        def eval(self):
            return self

        def train(self, mode=True):
            self.training = mode
            return self

        def act(self, snapshot, **kwargs):
            return {agent_id: "hold" for agent_id in snapshot.role_observations}

    def verified_factory(scenario_id):
        bundle = _factory(scenario_id)
        bundle.parameter_status = "verified"
        return bundle

    with pytest.raises(ValueError, match="frozen"):
        evaluate_policy(MutablePolicy(), verified_factory, scenarios=["s1"], split="sealed_test", deterministic=True)


def test_stochastic_algorithm_adapter_freezes_normalization_and_training_state():
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.algorithm import SRMAPPOAlgorithm
    from problem2.algorithms.sr_mappo.trainer import SRMAPPOTrainer
    from problem2.experiments.policy_protocol import AlgorithmPolicyAdapter

    bundle = _factory("s1")
    snapshot = bundle.reset()
    algorithm = SRMAPPOAlgorithm(
        uav_obs_dim=len(snapshot.role_observations["uav-1"]["vector"]),
        vehicle_obs_dim=len(snapshot.role_observations["vehicle-1"]["vector"]),
        state_dim=len(snapshot.critic_state["vector"]),
        uav_action_dim=len(snapshot.action_masks["uav-1"]),
        vehicle_action_dim=len(snapshot.action_masks["vehicle-1"]),
        hidden_dim=8,
    )
    trainer = SRMAPPOTrainer(algorithm, learning_rate=1e-3)
    algorithm.obs_normalizer.update([[1.0] * len(snapshot.role_observations["uav-1"]["vector"])])
    algorithm.vehicle_obs_normalizer.update([[1.0] * len(snapshot.role_observations["vehicle-1"]["vector"])])
    mean_before = algorithm.obs_normalizer.mean.copy()
    count_before = algorithm.obs_normalizer.count
    vehicle_mean_before = algorithm.vehicle_obs_normalizer.mean.copy()
    vehicle_count_before = algorithm.vehicle_obs_normalizer.count
    training_before = algorithm.training
    optimizer_before = trainer.state_dict()
    evaluate_policy(AlgorithmPolicyAdapter(algorithm), _factory, scenarios=["s1"], split="smoke", deterministic=False)
    assert algorithm.training is training_before
    assert algorithm.obs_normalizer.count == count_before
    assert algorithm.vehicle_obs_normalizer.count == vehicle_count_before
    assert (algorithm.obs_normalizer.mean == mean_before).all()
    assert (algorithm.vehicle_obs_normalizer.mean == vehicle_mean_before).all()
    assert trainer.state_dict() == optimizer_before


@pytest.mark.parametrize(
    ("step", "format_value"),
    [
        (1.5, 2),
        ("7", 2),
        (True, 2),
        (1, 2.0),
        (1, "2"),
        (1, None),
    ],
)
def test_checkpoint_rejects_noncanonical_raw_metadata(tmp_path, step, format_value):
    torch = pytest.importorskip("torch")
    from problem2.experiments.evaluation import load_evaluation_checkpoint

    payload = {"step": step, "algorithm": {}}
    if format_value is not None:
        payload["format"] = format_value
    path = tmp_path / f"bad-{str(step)}-{str(format_value)}.pt"
    torch.save(payload, path)
    with pytest.raises(ValueError):
        load_evaluation_checkpoint(path, lambda: (_ for _ in ()).throw(AssertionError("factory must not run")))


def test_action_conversion_rejects_non_integral_float_index():
    from problem2.experiments.policy_protocol import actions_to_environment

    snapshot = _factory("s1").reset()
    with pytest.raises(ValueError, match="integer"):
        actions_to_environment(snapshot, {"uav": [4.9, 4], "vehicle": [0]})


def test_role_batched_boolean_actions_are_rejected_before_integer_conversion():
    from problem2.experiments.policy_protocol import actions_to_environment

    snapshot = _factory("s1").reset()
    with pytest.raises(ValueError, match="invalid action index"):
        actions_to_environment(snapshot, {"uav": [True, 4], "vehicle": [False]})
