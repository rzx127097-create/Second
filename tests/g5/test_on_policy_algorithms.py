from __future__ import annotations

import copy
import io
import inspect
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms import HeterogeneousAlgorithm, build_algorithm
from problem2.algorithms.common.checkpoint import (
    load_training_checkpoint,
    save_training_checkpoint,
)
from problem2.algorithms.common.config_diff import configuration_diff
from problem2.algorithms.common.gae import compute_gae
from problem2.algorithms.ippo.trainer import RoleLocalRolloutBatch
from problem2.algorithms.protocol import ActionResult, OnPolicyEnvelope, RoleBatch
from problem2.algorithms.sr_mappo.rollout import RolloutBatch
from problem2.experiments.g5_contract import load_g5_contract


ROOT = Path(__file__).resolve().parents[2]
METHOD_IDS = ("sr_mappo_mobile", "mappo_mobile", "ippo_mobile")


@pytest.fixture(scope="module")
def contract():
    return load_g5_contract(ROOT)


def _observations() -> dict[str, np.ndarray]:
    return {
        "uav": np.stack(
            (
                np.linspace(-1.0, 1.0, 179, dtype=np.float32),
                np.linspace(1.0, -1.0, 179, dtype=np.float32),
            )
        ),
        "vehicle": np.linspace(-0.5, 0.5, 28, dtype=np.float32).reshape(1, -1),
    }


def _masks() -> dict[str, np.ndarray]:
    return {
        "uav": np.array(
            [
                [True, False, True, False, False, False],
                [False, True, False, False, True, False],
            ],
            dtype=bool,
        ),
        "vehicle": np.array([[True, False, True, False, False]], dtype=bool),
    }


def _role_batch(action_result: ActionResult, step: int = 0) -> RoleBatch:
    observations = _observations()
    return RoleBatch.from_action_result(
        action_result,
        observations=observations,
        rewards={
            "uav": np.full(2, 1.0 + step, dtype=np.float32),
            "vehicle": np.full(1, 1.0 + step, dtype=np.float32),
        },
        next_observations={
            role: values + np.float32(0.1) for role, values in observations.items()
        },
        next_masks=_masks(),
        terminated=False,
        truncated=False,
        scenario_id="development-10000",
        transition_id=f"development-10000:{step}",
    )


def _envelope(algorithm, step: int = 0) -> OnPolicyEnvelope:
    observations = _observations()
    details = algorithm.act(observations, _masks(), deterministic=True, return_details=True)
    role_batch = _role_batch(
        ActionResult(actions=details["actions"], masks=details["masks"]), step
    )
    common = {
        "role_batch": role_batch,
        "policy_observations": details["policy_observations"],
        "old_log_probs": details["log_probs"],
        "valid_actor_sample": {"uav": [True, True], "vehicle": [True]},
        "agent_ids": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
        "candidate_mapping": {"vehicle": [None, "request-1", None, None]},
        "normalization_versions": details["normalization_versions"],
        "team_reward": float(1.0 + step),
        "valid_sample": True,
    }
    next_observations = role_batch.next_observations
    if algorithm.method_id == "ippo_mobile":
        return OnPolicyEnvelope(
            value_conditioning="local",
            values=details["values"],
            next_values={
                role: algorithm.local_value(role, next_observations[role]).detach().cpu().numpy()
                for role in algorithm.roles
            },
            **common,
        )
    state = np.full(185, step * 0.1, dtype=np.float32)
    next_state = np.full(185, (step + 1) * 0.1, dtype=np.float32)
    return OnPolicyEnvelope(
        value_conditioning="centralized",
        values=float(algorithm.value(state).detach().cpu()),
        next_values=float(algorithm.value(next_state).detach().cpu()),
        critic_state=state,
        next_critic_state=next_state,
        **common,
    )


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_factory_builds_protocol_conforming_two_role_algorithms(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")

    result = algorithm.act(_observations(), _masks(), deterministic=True)

    assert isinstance(algorithm, HeterogeneousAlgorithm)
    assert algorithm.trainer.minibatch_size == 64
    assert isinstance(result, ActionResult)
    assert result.actions["uav"].shape == (2,)
    assert result.actions["vehicle"].shape == (1,)
    for role in algorithm.roles:
        assert result.masks[role][
            np.arange(result.actions[role].shape[0]), result.actions[role]
        ].all()
    algorithm.observe(_envelope(algorithm))
    assert algorithm.diagnostics.snapshot()["observed_transitions"] == 1


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_all_on_policy_methods_replay_exact_behavior_masks_and_log_probs(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    algorithm.set_evaluation(True)

    details = algorithm.act(
        _observations(), _masks(), deterministic=True, return_details=True
    )
    replayed = algorithm.replay_log_probs(
        details["policy_observations"],
        details["masks"],
        details["actions"],
    )

    for role in algorithm.roles:
        np.testing.assert_array_equal(details["masks"][role], _masks()[role])
        np.testing.assert_allclose(
            replayed[role], details["log_probs"][role], atol=1e-6
        )


def _central_rollout() -> RolloutBatch:
    batch = RolloutBatch()
    for step, (reward, value, next_value) in enumerate(
        ((1.0, 0.5, 0.7), (2.0, 0.7, 1.1), (3.0, 1.1, 4.0))
    ):
        batch.add(
            {
                "role": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "agent_id": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "raw_observation": _observations(),
                "normalized_policy_observation": _observations(),
                "critic_state": np.full(185, step + 0.25, dtype=np.float32),
                "action": {"uav": [0, 1], "vehicle": [0]},
                "action_mask": _masks(),
                "old_log_prob": {"uav": [-0.5, -0.6], "vehicle": [-0.4]},
                "value": value,
                "next_value": next_value,
                "reward": reward,
                "terminated": step == 1,
                "truncated": step == 2,
                "valid_actor_sample": {"uav": [True, True], "vehicle": [True]},
                "candidate_mapping": {"vehicle": [None, "request-1", None, None]},
                "normalization_versions": {"uav": 0, "vehicle": 0, "return": 0},
                "episode_id": "development-10000",
                "config_hash": "task4-test",
            }
        )
    return batch


def test_centralized_rollout_keeps_hand_computable_team_gae() -> None:
    batch = _central_rollout()

    advantages, returns = batch.finish(gamma=0.9, gae_lambda=0.95)

    deltas = np.array([1.0 + 0.9 * 0.7 - 0.5, 2.0 - 0.7, 3.0 + 0.9 * 4.0 - 1.1])
    expected = np.array([deltas[0] + 0.9 * 0.95 * deltas[1], deltas[1], deltas[2]])
    np.testing.assert_allclose(advantages, expected, atol=1e-6)
    np.testing.assert_allclose(returns, expected + np.array([0.5, 0.7, 1.1]), atol=1e-6)


def test_ippo_rollout_computes_role_local_gae_from_shared_team_reward() -> None:
    batch = RoleLocalRolloutBatch()
    batch.add(
        reward=1.0,
        values={"uav": [0.5, 1.0], "vehicle": [0.25]},
        next_values={"uav": [0.7, 1.2], "vehicle": [0.5]},
        terminated=False,
        truncated=False,
    )
    batch.add(
        reward=2.0,
        values={"uav": [0.7, 1.2], "vehicle": [0.5]},
        next_values={"uav": [9.0, 9.0], "vehicle": [9.0]},
        terminated=True,
        truncated=False,
    )

    advantages, returns = batch.finish(gamma=0.9, gae_lambda=0.95)

    expected_uav_last = np.array([1.3, 0.8])
    expected_uav_first = (
        np.array([1.0 + 0.9 * 0.7 - 0.5, 1.0 + 0.9 * 1.2 - 1.0])
        + 0.9 * 0.95 * expected_uav_last
    )
    np.testing.assert_allclose(advantages["uav"], [expected_uav_first, expected_uav_last])
    np.testing.assert_allclose(
        returns["vehicle"],
        advantages["vehicle"] + np.array([[0.25], [0.5]]),
    )


def test_ippo_advantage_normalization_uses_only_role_valid_samples() -> None:
    batch = RoleLocalRolloutBatch()
    batch.add(
        reward=0.0,
        values={"uav": [1.0, 100.0], "vehicle": [1.0]},
        next_values={"uav": [0.0, 0.0], "vehicle": [0.0]},
        terminated=False,
        truncated=False,
        valid_actor_sample={"uav": [True, False], "vehicle": [True]},
    )
    batch.add(
        reward=0.0,
        values={"uav": [3.0, 100.0], "vehicle": [3.0]},
        next_values={"uav": [0.0, 0.0], "vehicle": [0.0]},
        terminated=True,
        truncated=False,
        valid_actor_sample={"uav": [True, False], "vehicle": [True]},
    )
    batch.finish(gamma=0.0, gae_lambda=0.0)

    normalized = batch.normalize_advantages()

    np.testing.assert_allclose(normalized["uav"][:, 0], [1.0, -1.0], atol=1e-6)
    assert not np.isclose(normalized["uav"][:, 1], 0.0).all()


def test_centralized_and_role_local_value_information_boundaries(contract) -> None:
    torch = pytest.importorskip("torch")
    sr_mappo = build_algorithm("sr_mappo_mobile", contract, "cpu")
    mappo = build_algorithm("mappo_mobile", contract, "cpu")
    ippo = build_algorithm("ippo_mobile", contract, "cpu")

    assert sr_mappo.value(torch.zeros(185)).shape == ()
    assert mappo.value(torch.zeros(185)).shape == ()
    assert not hasattr(ippo, "critic")
    assert ippo.local_value("uav", torch.zeros((2, 179))).shape == (2,)
    assert ippo.local_value("vehicle", torch.zeros((1, 28))).shape == (1,)
    with pytest.raises(TypeError):
        ippo.uav_value(torch.zeros((2, 179)), critic_state=torch.zeros((2, 185)))
    with pytest.raises(TypeError):
        sr_mappo.uav_actor(torch.zeros((2, 179)), critic_state=torch.zeros((2, 185)))


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_role_optimizer_parameter_sets_are_disjoint(contract, method_id: str) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    optimizer_parameters = {
        role: {
            parameter
            for group in optimizer.param_groups
            for parameter in group["params"]
        }
        for role, optimizer in algorithm.trainer.optimizers.items()
    }

    assert optimizer_parameters["uav"].isdisjoint(optimizer_parameters["vehicle"])
    if "critic" in optimizer_parameters:
        assert optimizer_parameters["uav"].isdisjoint(optimizer_parameters["critic"])
        assert optimizer_parameters["vehicle"].isdisjoint(optimizer_parameters["critic"])


def _parameter_snapshot(modules) -> list:
    return [
        parameter.detach().cpu().clone()
        for module in modules
        for parameter in module.parameters()
    ]


def _parameters_changed(before: list, modules) -> bool:
    after = [
        parameter.detach().cpu()
        for module in modules
        for parameter in module.parameters()
    ]
    return any(not np.array_equal(left.numpy(), right.numpy()) for left, right in zip(before, after))


@pytest.mark.parametrize("method_id", ("sr_mappo_mobile", "mappo_mobile"))
def test_centralized_methods_complete_mask_replayed_updates(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    batch = RolloutBatch()
    before = {
        "uav": _parameter_snapshot((algorithm.uav_actor,)),
        "vehicle": _parameter_snapshot((algorithm.vehicle_actor,)),
        "critic": _parameter_snapshot((algorithm.critic,)),
    }
    for step in range(3):
        observations = {
            role: values + np.float32(step * 0.05)
            for role, values in _observations().items()
        }
        details = algorithm.act(
            observations, _masks(), deterministic=False, return_details=True
        )
        critic_state = np.full(185, step * 0.1, dtype=np.float32)
        next_critic_state = np.full(185, (step + 1) * 0.1, dtype=np.float32)
        batch.add(
            {
                "role": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "agent_id": {"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
                "raw_observation": observations,
                "normalized_policy_observation": details["policy_observations"],
                "critic_state": critic_state,
                "action": details["actions"],
                "action_mask": details["masks"],
                "old_log_prob": details["log_probs"],
                "value": float(algorithm.value(critic_state).detach().cpu()),
                "next_value": float(algorithm.value(next_critic_state).detach().cpu()),
                "reward": float(step + 1),
                "terminated": False,
                "truncated": step == 2,
                "valid_actor_sample": {"uav": [True, True], "vehicle": [True]},
                "candidate_mapping": {"vehicle": [None, "request-1", None, None]},
                "normalization_versions": details["normalization_versions"],
                "episode_id": "development-10000",
                "config_hash": "task4-central-update",
            }
        )
    batch.finish(gamma=0.99, gae_lambda=0.95)

    metrics = algorithm.trainer.update(batch, epochs=2, progress=0.1)

    assert metrics["critic_updates"] == 2
    assert metrics["uav_actor_updates"] == 2
    assert metrics["vehicle_actor_updates"] == 2
    assert np.isfinite(metrics["critic_loss"])
    assert _parameters_changed(before["uav"], (algorithm.uav_actor,))
    assert _parameters_changed(before["vehicle"], (algorithm.vehicle_actor,))
    assert _parameters_changed(before["critic"], (algorithm.critic,))


def test_ippo_completes_role_local_mask_replayed_update(contract) -> None:
    algorithm = build_algorithm("ippo_mobile", contract, "cpu")
    algorithm.trainer.minibatch_size = 2
    batch = RoleLocalRolloutBatch()
    before = {
        "uav": _parameter_snapshot((algorithm.uav_actor, algorithm.uav_value)),
        "vehicle": _parameter_snapshot((algorithm.vehicle_actor, algorithm.vehicle_value)),
    }
    for step in range(3):
        observations = {
            role: values + np.float32(step * 0.05)
            for role, values in _observations().items()
        }
        next_observations = {
            role: values + np.float32(0.05)
            for role, values in observations.items()
        }
        details = algorithm.act(
            observations, _masks(), deterministic=False, return_details=True
        )
        next_values = {
            role: algorithm.local_value(role, next_observations[role])
            .detach()
            .cpu()
            .numpy()
            for role in algorithm.roles
        }
        batch.add(
            reward=float(step + 1),
            values=details["values"],
            next_values=next_values,
            terminated=False,
            truncated=step == 2,
            observations=details["policy_observations"],
            masks=details["masks"],
            actions=details["actions"],
            old_log_probs=details["log_probs"],
            valid_actor_sample={
                "uav": [True, step != 1],
                "vehicle": [step != 1],
            },
        )
    batch.finish(gamma=0.99, gae_lambda=0.95)

    metrics = algorithm.trainer.update(batch, epochs=2)

    assert metrics["uav_actor_updates"] == 6
    assert metrics["vehicle_actor_updates"] == 2
    assert metrics["uav_valid_samples"] == 5
    assert metrics["vehicle_valid_samples"] == 2
    assert np.isfinite(metrics["uav_value_loss"])
    assert np.isfinite(metrics["vehicle_value_loss"])
    assert _parameters_changed(before["uav"], (algorithm.uav_actor, algorithm.uav_value))
    assert _parameters_changed(
        before["vehicle"], (algorithm.vehicle_actor, algorithm.vehicle_value)
    )


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_deterministic_evaluation_freezes_normalizers_byte_identically(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    algorithm.train(True)
    algorithm.act(_observations(), _masks(), deterministic=False)
    before = algorithm.normalizer_state_bytes()

    algorithm.set_evaluation(True)
    algorithm.act(_observations(), _masks(), deterministic=True)

    assert algorithm.normalizer_state_bytes() == before


def _provenance() -> dict[str, str]:
    return {
        "source_commit": "a" * 40,
        "source_bundle_sha256": "b" * 64,
        "config_hash": "c" * 64,
        "protocol_hash": "d" * 64,
        "ancestry_hash": "e" * 64,
    }


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_complete_checkpoint_round_trip_preserves_each_on_policy_method(
    tmp_path: Path, contract, method_id: str
) -> None:
    torch = pytest.importorskip("torch")
    torch.manual_seed(20260823)
    algorithm = build_algorithm(method_id, contract, "cpu")
    algorithm.set_evaluation(True)
    before = algorithm.act(
        _observations(), _masks(), deterministic=True, return_details=True
    )
    pending = [_envelope(algorithm, step) for step in range(2)]
    for envelope in pending:
        algorithm.observe(envelope)
    state = algorithm.state_dict()
    assert state["method_id"] == method_id
    assert state["trainer"]
    assert state["diagnostics"]
    assert state["rollout_position"] == len(pending)
    path = tmp_path / f"{method_id}.pt"

    save_training_checkpoint(
        path,
        {
            "algorithm": state,
            "method_state": {"family": "on_policy"},
            "rollout_position": state["rollout_position"],
            "counters": algorithm.diagnostics.snapshot(),
        },
        _provenance(),
    )
    restored, record = load_training_checkpoint(
        path,
        lambda: build_algorithm(method_id, contract, "cpu"),
        _provenance(),
    )
    after = restored.act(
        _observations(), _masks(), deterministic=True, return_details=True
    )

    assert record.state["method_state"] == {"family": "on_policy"}
    assert restored.state_dict()["rollout_position"] == len(pending)
    assert restored.diagnostics.snapshot() == algorithm.diagnostics.snapshot()
    assert after["actions"] == before["actions"]
    for role in restored.roles:
        np.testing.assert_allclose(after["log_probs"][role], before["log_probs"][role])


def test_sr_mappo_and_mappo_configuration_diff_is_stability_only(contract) -> None:
    sr_mappo = build_algorithm("sr_mappo_mobile", contract, "cpu")
    mappo = build_algorithm("mappo_mobile", contract, "cpu")

    diff = configuration_diff(
        copy.deepcopy(sr_mappo.comparison_config),
        copy.deepcopy(mappo.comparison_config),
    )

    assert diff["changed_keys"] == [
        f"stability_components.{name}"
        for name in sorted(contract.stability_components["sr_mappo_mobile"])
    ]
    assert diff["only_declared_stability_flags_changed"] is True


@pytest.mark.parametrize("method_id", METHOD_IDS)
@pytest.mark.parametrize("candidate_id", ("c02", "c03", "c04"))
def test_factory_accepts_every_frozen_on_policy_candidate(
    contract, method_id: str, candidate_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu", candidate_id=candidate_id)

    assert algorithm.training_config["candidate_id"] == candidate_id
    assert algorithm.trainer.clip_radius == pytest.approx(
        next(
            candidate.parameters["clip_radius"]
            for candidate in contract.tuning_candidates[method_id]
            if candidate.candidate_id == candidate_id
        )
    )


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_observe_rejects_independent_on_policy_rollouts_and_requires_bound_envelope(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    independent = RoleLocalRolloutBatch() if method_id == "ippo_mobile" else RolloutBatch()

    with pytest.raises(TypeError, match="behavior-bound"):
        algorithm.observe(independent)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_envelope_is_the_only_actual_on_policy_update_ingest_path(
    contract, method_id: str
) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    envelope = _envelope(algorithm)
    algorithm.observe(envelope)
    assert algorithm.state_dict()["rollout_position"] == 1
    metrics = algorithm.update()
    assert metrics["uav_actor_updates"] > 0


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_envelope_rejects_behavior_log_probability_and_identity_drift(contract, method_id: str) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    envelope = _envelope(algorithm)
    state = envelope.state_dict()
    state["old_log_probs"]["uav"][0] += 1.0
    with pytest.raises(ValueError, match="log probabilities"):
        algorithm.observe(OnPolicyEnvelope.from_state_dict(state))
    state = envelope.state_dict()
    state["agent_ids"]["uav"][1] = "uav-0"
    with pytest.raises(ValueError, match="unique"):
        OnPolicyEnvelope.from_state_dict(state)


def _torch_bytes(value) -> bytes:
    torch = pytest.importorskip("torch")
    target = io.BytesIO()
    torch.save(value, target)
    return target.getvalue()


def _assert_nested_equal(left, right) -> None:
    torch = pytest.importorskip("torch")
    if torch.is_tensor(left):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    elif isinstance(left, np.ndarray):
        np.testing.assert_array_equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            _assert_nested_equal(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for first, second in zip(left, right):
            _assert_nested_equal(first, second)
    elif isinstance(left, float):
        assert left == pytest.approx(right, rel=0, abs=0)
    else:
        assert left == right


@pytest.mark.parametrize("method_id", METHOD_IDS)
@pytest.mark.parametrize("mutation", ("missing_trainer", "extra", "config", "stability", "malformed_pending"))
def test_g5_method_state_rejects_drift_before_model_or_optimizer_mutation(contract, method_id, mutation) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    algorithm.observe(_envelope(algorithm))
    state = algorithm.state_dict()
    before_model = _torch_bytes(algorithm.state_dict())
    before_optimizer = _torch_bytes(algorithm.trainer.state_dict())
    if mutation == "missing_trainer":
        del state["trainer"]
    elif mutation == "extra":
        state["extra"] = True
    elif mutation == "config":
        state["training_config"] = {**state["training_config"], "clip_radius": 0.123}
    elif mutation == "stability":
        state["stability_components"] = {**state["stability_components"], "value_clipping": not state["stability_components"]["value_clipping"]}
    else:
        state["pending_envelopes"][0]["old_log_probs"]["uav"][0] = np.nan
    with pytest.raises(ValueError):
        algorithm.load_state_dict(state)
    assert _torch_bytes(algorithm.state_dict()) == before_model
    assert _torch_bytes(algorithm.trainer.state_dict()) == before_optimizer


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_checkpoint_resume_matches_uninterrupted_next_envelope_update(tmp_path, contract, method_id) -> None:
    import random
    torch = pytest.importorskip("torch")
    random.seed(7); np.random.seed(7); torch.manual_seed(7)
    uninterrupted = build_algorithm(method_id, contract, "cpu")
    for step in range(2):
        uninterrupted.observe(_envelope(uninterrupted, step))
    path = tmp_path / f"{method_id}-resume.pt"
    save_training_checkpoint(path, {"algorithm": uninterrupted.state_dict()}, _provenance())
    uninterrupted_metrics = uninterrupted.update()
    uninterrupted_state = _torch_bytes(uninterrupted.state_dict())
    resumed, _ = load_training_checkpoint(path, lambda: build_algorithm(method_id, contract, "cpu"), _provenance())
    resumed_metrics = resumed.update()
    _assert_nested_equal(resumed_metrics, uninterrupted_metrics)
    _assert_nested_equal(resumed.state_dict(), uninterrupted.state_dict())
    resumed_action = resumed.act(_observations(), _masks(), deterministic=True)
    uninterrupted_action = uninterrupted.act(_observations(), _masks(), deterministic=True)
    for role in resumed.roles:
        np.testing.assert_array_equal(resumed_action.actions[role], uninterrupted_action.actions[role])


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_nonfinite_envelope_is_rejected_without_update_mutation(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    envelope = _envelope(algorithm)
    state = envelope.state_dict()
    state["policy_observations"]["uav"][0, 0] = np.nan
    before = _torch_bytes(algorithm.state_dict())
    with pytest.raises(ValueError, match="finite"):
        algorithm.observe(OnPolicyEnvelope.from_state_dict(state))
    assert _torch_bytes(algorithm.state_dict()) == before


def test_nondefault_clip_radius_changes_the_hand_computable_ppo_loss() -> None:
    torch = pytest.importorskip("torch")
    from problem2.algorithms.sr_mappo.losses import ppo_policy_loss
    new = torch.tensor([np.log(1.3)], dtype=torch.float32)
    old = torch.tensor([0.0], dtype=torch.float32)
    advantage = torch.tensor([1.0], dtype=torch.float32)
    assert ppo_policy_loss(new, old, advantage, clip_epsilon=0.10).item() == pytest.approx(-1.10)
    assert ppo_policy_loss(new, old, advantage, clip_epsilon=0.30).item() == pytest.approx(-1.30)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_finite_overflowing_trainer_loss_rolls_back_parameters_and_optimizer(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    if method_id == "ippo_mobile":
        batch = RoleLocalRolloutBatch()
        for _ in range(2):
            batch.add(reward=1.0, values={"uav": [0.0, 0.0], "vehicle": [0.0]}, next_values={"uav": [0.0, 0.0], "vehicle": [0.0]}, terminated=False, truncated=True, observations=_observations(), masks=_masks(), actions={"uav": [0, 1], "vehicle": [0]}, old_log_probs={"uav": [-1e38, -1e38], "vehicle": [-1e38]}, valid_actor_sample={"uav": [True, True], "vehicle": [True]})
        batch.finish(0.99, 0.95)
    else:
        batch = _central_rollout()
        for item in batch.transitions:
            item["old_log_prob"] = {"uav": [-1e38, -1e38], "vehicle": [-1e38]}
        batch.finish(0.99, 0.95)
    before = copy.deepcopy(algorithm.state_dict())
    with pytest.raises(FloatingPointError):
        algorithm.trainer.update(batch, epochs=1)
    _assert_nested_equal(algorithm.state_dict(), before)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_envelope_requires_exact_shared_reward_validity_mapping_and_normalization(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    envelope = _envelope(algorithm)
    assert envelope.team_reward == pytest.approx(1.0)
    assert envelope.valid_sample is True

    state = envelope.state_dict()
    state["role_batch"]["rewards"]["vehicle"][0] = 0.5
    with pytest.raises(ValueError, match="team_reward"):
        OnPolicyEnvelope.from_state_dict(state)

    state = envelope.state_dict()
    state["valid_actor_sample"]["uav"] = [1, True]
    with pytest.raises(ValueError, match="boolean"):
        OnPolicyEnvelope.from_state_dict(state)

    state = envelope.state_dict()
    state["candidate_mapping"]["vehicle"] = ["request-1", None, None, None]
    with pytest.raises(ValueError, match="candidate"):
        OnPolicyEnvelope.from_state_dict(state)

    state = envelope.state_dict()
    state["role_batch"]["masks"]["vehicle"][0, 2] = True
    state["role_batch"]["behavior_action_result"]["masks"]["vehicle"][0, 2] = True
    state["candidate_mapping"]["vehicle"] = [None, "request-1", "request-1", None]
    with pytest.raises(ValueError, match="candidate"):
        OnPolicyEnvelope.from_state_dict(state)

    state = envelope.state_dict()
    state["normalization_versions"] = {"uav": 0, "vehicle": 0}
    with pytest.raises(ValueError, match="normalization"):
        OnPolicyEnvelope.from_state_dict(state)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_envelope_rejects_nonfinite_raw_or_next_observations_before_observe_mutation(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    for field in ("observations", "next_observations"):
        state = _envelope(algorithm).state_dict()
        state["role_batch"][field]["uav"][0, 0] = np.nan
        with pytest.raises(ValueError, match="finite"):
            OnPolicyEnvelope.from_state_dict(state)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_envelope_rejects_invalid_value_and_critic_shapes_before_observe_mutation(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    state = _envelope(algorithm).state_dict()
    if method_id == "ippo_mobile":
        state["values"]["uav"] = [0.0]
        with pytest.raises(ValueError, match="values"):
            OnPolicyEnvelope.from_state_dict(state)
    else:
        state["values"] = [0.0, 1.0]
        with pytest.raises(ValueError, match="values"):
            OnPolicyEnvelope.from_state_dict(state)
        state = _envelope(algorithm).state_dict()
        state["critic_state"] = np.zeros((1, 185), dtype=np.float32)
        with pytest.raises(ValueError, match="critic_state"):
            OnPolicyEnvelope.from_state_dict(state)


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_g5_load_prevalidates_malformed_nested_state_before_different_weights_mutate_live_objects(contract, method_id) -> None:
    torch = pytest.importorskip("torch")
    algorithm = build_algorithm(method_id, contract, "cpu")
    algorithm.observe(_envelope(algorithm))
    before = copy.deepcopy(algorithm.state_dict())
    incoming = copy.deepcopy(before)
    incoming["uav_actor"][next(iter(incoming["uav_actor"]))].add_(1.0)
    incoming["pending_envelopes"][0]["old_log_probs"]["uav"][0] = np.nan
    incoming["trainer"] = {"malformed": True}
    with pytest.raises(ValueError):
        algorithm.load_state_dict(incoming)
    _assert_nested_equal(algorithm.state_dict(), before)
    assert not torch.equal(
        incoming["uav_actor"][next(iter(incoming["uav_actor"]))],
        before["uav_actor"][next(iter(before["uav_actor"]))],
    )


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_observe_requires_current_exact_normalization_versions(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    state = _envelope(algorithm).state_dict()
    state["normalization_versions"]["uav"] += 1
    before = _torch_bytes(algorithm.state_dict())
    with pytest.raises(ValueError, match="normalization"):
        algorithm.observe(OnPolicyEnvelope.from_state_dict(state))
    assert _torch_bytes(algorithm.state_dict()) == before


def test_public_protocol_advertises_and_exports_on_policy_envelope() -> None:
    from problem2.algorithms import OnPolicyEnvelope as public_envelope

    assert public_envelope is OnPolicyEnvelope
    annotation = inspect.signature(HeterogeneousAlgorithm.observe).parameters["batch"].annotation
    assert annotation in (OnPolicyEnvelope, "OnPolicyEnvelope")


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_strict_trainer_state_rejects_bad_optimizer_before_live_optimizer_changes(contract, method_id) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    before = _torch_bytes(algorithm.trainer.state_dict())
    state = copy.deepcopy(algorithm.trainer.state_dict())
    state["optimizers"]["uav"] = {"state": "not-an-optimizer"}
    with pytest.raises(ValueError, match="trainer"):
        algorithm.trainer.load_state_dict(state)
    assert _torch_bytes(algorithm.trainer.state_dict()) == before


def test_ippo_reports_sample_weighted_minibatch_policy_entropy_and_value_metrics(contract) -> None:
    algorithm = build_algorithm("ippo_mobile", contract, "cpu")
    algorithm.trainer.minibatch_size = 1
    for step in range(2):
        algorithm.observe(_envelope(algorithm, step))
    metrics = algorithm.trainer.update(algorithm._rollout_from_envelopes(), epochs=1)

    assert metrics["uav_actor_updates"] == 4
    assert metrics["vehicle_actor_updates"] == 2
    for role in algorithm.roles:
        for name in ("policy_loss", "entropy", "value_loss"):
            assert np.isfinite(metrics[f"{role}_{name}"])


def test_central_invalid_team_sample_is_neutral_and_cuts_hand_gold_gae_trace() -> None:
    common = dict(
        rewards=[1.0, 2.0, 3.0],
        values=[0.5, 0.7, 1.1],
        terminated=[False, False, False],
        truncated=[False, False, False],
        last_value=4.0,
        next_values=[0.7, 1.1, 4.0],
        gamma=0.9,
        gae_lambda=0.95,
        valid_sample=[True, False, True],
    )
    advantages, returns = compute_gae(**common)
    altered = dict(common, rewards=[1.0, -999.0, 3.0], values=[0.5, 999.0, 1.1], next_values=[0.7, -999.0, 4.0])
    altered_advantages, altered_returns = compute_gae(**altered)

    np.testing.assert_allclose(advantages[0], 1.0 + 0.9 * 0.7 - 0.5)
    np.testing.assert_allclose(returns[0], advantages[0] + 0.5)
    np.testing.assert_array_equal(advantages[[0, 2]], altered_advantages[[0, 2]])
    np.testing.assert_array_equal(returns[[0, 2]], altered_returns[[0, 2]])
    assert advantages[1] == returns[1] == 0.0


def test_role_local_invalid_agent_sample_is_neutral_and_cuts_only_its_hand_gold_trace() -> None:
    def make_batch(invalid_value: float) -> RoleLocalRolloutBatch:
        batch = RoleLocalRolloutBatch()
        for index in range(3):
            batch.add(
                reward=float(index + 1),
                values={"uav": [0.5 + index, invalid_value if index == 1 else 0.25 + index], "vehicle": [0.4 + index]},
                next_values={"uav": [1.5 + index, invalid_value if index == 1 else 1.25 + index], "vehicle": [1.4 + index]},
                terminated=False,
                truncated=False,
                valid_sample=True,
                valid_actor_sample={"uav": [True, index != 1], "vehicle": [True]},
            )
        batch.finish(gamma=0.9, gae_lambda=0.95)
        return batch

    baseline = make_batch(5.0)
    altered = make_batch(-999.0)

    np.testing.assert_array_equal(baseline.advantages["uav"][[0, 2], 1], altered.advantages["uav"][[0, 2], 1])
    np.testing.assert_array_equal(baseline.returns["uav"][[0, 2], 1], altered.returns["uav"][[0, 2], 1])
    assert baseline.advantages["uav"][1, 1] == baseline.returns["uav"][1, 1] == 0.0
    assert baseline.advantages["uav"][0, 0] == altered.advantages["uav"][0, 0]
    assert baseline.normalized_advantages == {}
    normalized = baseline.normalize_advantages()
    assert not np.isclose(normalized["uav"][1, 1], 0.0)


@pytest.mark.parametrize("method_id", METHOD_IDS)
@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("minibatch_size", 64.0),
        ("minibatch_size", True),
        ("minibatch_size", np.int64(64)),
        ("value_coef", np.nan),
        ("entropy_coef", np.inf),
        ("max_grad_norm", True),
        ("clip_radius", np.nan),
    ),
)
def test_trainer_state_requires_type_exact_finite_frozen_scalars_before_live_mutation(contract, method_id, field, value) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu")
    before = copy.deepcopy(algorithm.state_dict())
    incoming = copy.deepcopy(before)
    incoming["trainer"][field] = value
    with pytest.raises(ValueError, match="trainer|frozen|minibatch"):
        algorithm.load_state_dict(incoming)
    _assert_nested_equal(algorithm.state_dict(), before)


@pytest.mark.parametrize("field,value", (("lr_decay", 1), ("lr_decay", np.bool_(True))))
def test_central_trainer_state_requires_boolean_lr_decay_before_live_mutation(contract, field, value) -> None:
    algorithm = build_algorithm("sr_mappo_mobile", contract, "cpu")
    before = copy.deepcopy(algorithm.state_dict())
    incoming = copy.deepcopy(before)
    incoming["trainer"][field] = value
    with pytest.raises(ValueError, match="trainer|frozen|lr_decay"):
        algorithm.load_state_dict(incoming)
    _assert_nested_equal(algorithm.state_dict(), before)
