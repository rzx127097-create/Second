from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms import build_algorithm
from problem2.algorithms.common.checkpoint import (
    load_training_checkpoint,
    save_training_checkpoint,
)
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.iql.networks import masked_bootstrap_max
from problem2.algorithms.maddpg.networks import masked_straight_through_gumbel
from problem2.algorithms.protocol import (
    ActionResult,
    OffPolicyEnvelope,
    OnPolicyEnvelope,
    RoleBatch,
)
from problem2.experiments.g5_contract import load_g5_contract


ROOT = Path(__file__).resolve().parents[2]
METHOD_IDS = ("maddpg_mobile", "iql_mobile")


@pytest.fixture(scope="module")
def contract():
    return load_g5_contract(ROOT)


def _observations(offset: float = 0.0) -> dict[str, np.ndarray]:
    return {
        "uav": np.stack(
            (
                np.linspace(-1.0, 1.0, 179, dtype=np.float32) + offset,
                np.linspace(1.0, -1.0, 179, dtype=np.float32) + offset,
            )
        ),
        "vehicle": np.linspace(-0.5, 0.5, 28, dtype=np.float32).reshape(1, -1) + offset,
    }


def _masks() -> dict[str, np.ndarray]:
    return {
        "uav": np.array(
            [[True, False, True, False, False, False], [False, True, False, False, True, False]],
            dtype=bool,
        ),
        "vehicle": np.array([[True, False, True, False, False]], dtype=bool),
    }


def _envelope(
    step: int = 0,
    *,
    valid: bool = True,
    valid_actor_sample: dict[str, list[bool]] | None = None,
) -> OffPolicyEnvelope:
    observations = _observations(float(step) * 0.1)
    masks = _masks()
    action_result = ActionResult(
        actions={"uav": np.array([0, 1]), "vehicle": np.array([0])},
        masks=masks,
    )
    role_batch = RoleBatch.from_action_result(
        action_result,
        observations=observations,
        rewards={
            "uav": np.full(2, 1.5 + step, dtype=np.float32),
            "vehicle": np.full(1, 1.5 + step, dtype=np.float32),
        },
        next_observations=_observations(float(step + 1) * 0.1),
        next_masks=masks,
        terminated=False,
        truncated=False,
        scenario_id="development-10000",
        transition_id=f"development-10000:{step}",
    )
    return OffPolicyEnvelope(
        role_batch=role_batch,
        critic_state=np.full(185, step * 0.1, dtype=np.float32),
        next_critic_state=np.full(185, (step + 1) * 0.1, dtype=np.float32),
        team_reward=1.5 + step,
        valid_sample=valid,
        valid_actor_sample=valid_actor_sample or {"uav": [True, True], "vehicle": [True]},
        agent_ids={"uav": ["uav-0", "uav-1"], "vehicle": ["vehicle-0"]},
        candidate_mapping={"vehicle": [None, "request-1", None, None]},
    )


def _provenance() -> dict[str, str]:
    return {
        "source_commit": "a" * 40,
        "source_bundle_sha256": "b" * 64,
        "config_hash": "c" * 64,
        "protocol_hash": "d" * 64,
        "ancestry_hash": "e" * 64,
    }


def test_off_policy_envelope_round_trip_preserves_behavior_binding() -> None:
    envelope = _envelope()
    restored = OffPolicyEnvelope.from_state_dict(envelope.state_dict())

    assert restored.team_reward == pytest.approx(envelope.team_reward)
    np.testing.assert_array_equal(restored.role_batch.masks["uav"], envelope.role_batch.masks["uav"])
    assert restored.candidate_mapping == {"vehicle": (None, "request-1", None, None)}


def test_off_policy_envelope_rejects_reward_and_mask_drift() -> None:
    state = _envelope().state_dict()
    state["team_reward"] = 99.0
    with pytest.raises(ValueError, match="team_reward"):
        OffPolicyEnvelope.from_state_dict(state)

    state = _envelope().state_dict()
    state["role_batch"]["behavior_action_result"]["masks"]["uav"][0][0] = False
    with pytest.raises(ValueError, match="mask|action"):
        OffPolicyEnvelope.from_state_dict(state)


def test_off_policy_algorithms_reject_raw_and_on_policy_transitions(contract) -> None:
    envelope = _envelope()
    for method_id in METHOD_IDS:
        algorithm = build_algorithm(method_id, contract, "cpu")
        with pytest.raises(TypeError, match="off-policy"):
            algorithm.observe(envelope.role_batch)
        with pytest.raises(TypeError, match="off-policy"):
            algorithm.observe(object.__new__(OnPolicyEnvelope))


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_factory_builds_all_frozen_off_policy_candidates(contract, method_id: str) -> None:
    for candidate_id in ("c01", "c02", "c03", "c04"):
        algorithm = build_algorithm(method_id, contract, "cpu", candidate_id=candidate_id)
        result = algorithm.act(_observations(), _masks(), deterministic=True)
        for role in ("uav", "vehicle"):
            assert result.masks[role].shape == _masks()[role].shape
            assert result.masks[role][np.arange(len(result.actions[role])), result.actions[role]].all()


def test_maddpg_masked_gumbel_has_zero_illegal_mass_and_gradient() -> None:
    torch = pytest.importorskip("torch")
    logits = torch.tensor([[0.2, -0.4, 0.1]], requires_grad=True)
    mask = torch.tensor([[True, False, True]])
    relaxed = masked_straight_through_gumbel(logits, mask, temperature=0.7)
    relaxed.sum().backward()

    assert relaxed[0, 1].item() == 0.0
    assert logits.grad[0, 1].item() == 0.0


def test_maddpg_update_is_role_isolated_and_moves_targets(contract) -> None:
    torch = pytest.importorskip("torch")
    algorithm = build_algorithm("maddpg_mobile", contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope())
    actor_before = copy.deepcopy(algorithm.vehicle_actor.state_dict())
    target_before = copy.deepcopy(algorithm.uav_target_actor.state_dict())

    metrics = algorithm.trainer.update_role("uav", algorithm.replay.sample(1))

    assert metrics["role"] == "uav"
    assert any(not torch.equal(target_before[key], value) for key, value in algorithm.uav_target_actor.state_dict().items())
    for key, value in algorithm.vehicle_actor.state_dict().items():
        torch.testing.assert_close(value, actor_before[key], rtol=0, atol=0)


@pytest.mark.parametrize("role", ["uav", "vehicle"])
def test_maddpg_excludes_invalid_role_samples_from_updates(contract, role: str) -> None:
    torch = pytest.importorskip("torch")
    valid_actor_sample = {"uav": [True, True], "vehicle": [True]}
    valid_actor_sample[role] = [False] * len(valid_actor_sample[role])
    algorithm = build_algorithm("maddpg_mobile", contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope(valid_actor_sample=valid_actor_sample))
    actor = algorithm.uav_actor if role == "uav" else algorithm.vehicle_actor
    critic = algorithm.uav_critic if role == "uav" else algorithm.vehicle_critic
    actor_before = copy.deepcopy(actor.state_dict())
    critic_before = copy.deepcopy(critic.state_dict())

    metrics = algorithm.trainer.update_role(role, algorithm.replay.sample(1))

    assert metrics == {"role": role, "critic_loss": 0.0, "actor_loss": 0.0}
    for key, value in actor.state_dict().items():
        torch.testing.assert_close(value, actor_before[key], rtol=0, atol=0)
    for key, value in critic.state_dict().items():
        torch.testing.assert_close(value, critic_before[key], rtol=0, atol=0)


def test_maddpg_joint_critic_requires_structured_state_and_joint_actions(contract) -> None:
    torch = pytest.importorskip("torch")
    algorithm = build_algorithm("maddpg_mobile", contract, "cpu", candidate_id="c01")
    state = torch.zeros((1, 185))
    uav = torch.zeros((1, 2, 6))
    vehicle = torch.zeros((1, 1, 5))
    assert algorithm.uav_critic(state, uav, vehicle).shape == (1,)
    with pytest.raises(ValueError, match="state"):
        algorithm.uav_critic(torch.zeros((1, 184)), uav, vehicle)


def test_iql_masked_bootstrap_excludes_illegal_values() -> None:
    torch = pytest.importorskip("torch")
    q = torch.tensor([[1.0, 100.0, 3.0]])
    mask = torch.tensor([[True, False, True]])
    assert masked_bootstrap_max(q, mask).item() == pytest.approx(3.0)
    with pytest.raises(ValueError, match="legal"):
        masked_bootstrap_max(q, torch.tensor([[False, False, False]]))


def test_iql_role_replay_and_target_update_are_isolated(contract) -> None:
    torch = pytest.importorskip("torch")
    algorithm = build_algorithm("iql_mobile", contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope())
    assert len(algorithm.uav_replay) == len(algorithm.vehicle_replay) == 1
    before = copy.deepcopy(algorithm.vehicle_target_q.state_dict())
    algorithm.trainer.target_update_interval = 1
    metrics = algorithm.trainer.update_role("uav", algorithm.uav_replay.sample(1))

    assert metrics["role"] == "uav"
    for key, value in algorithm.vehicle_target_q.state_dict().items():
        torch.testing.assert_close(value, before[key], rtol=0, atol=0)
    assert any(not torch.equal(before[key], value) for key, value in algorithm.uav_target_q.state_dict().items())


def test_iql_target_update_interval_is_role_local(contract) -> None:
    torch = pytest.importorskip("torch")
    algorithm = build_algorithm("iql_mobile", contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope())
    algorithm.trainer.target_update_interval = 2
    uav_before = copy.deepcopy(algorithm.uav_target_q.state_dict())
    vehicle_before = copy.deepcopy(algorithm.vehicle_target_q.state_dict())

    algorithm.trainer.update_role("uav", algorithm.uav_replay.sample(1))
    algorithm.trainer.update_role("vehicle", algorithm.vehicle_replay.sample(1))

    assert algorithm.trainer.target_update_count == {"uav": 0, "vehicle": 0}
    for key, value in algorithm.uav_target_q.state_dict().items():
        torch.testing.assert_close(value, uav_before[key], rtol=0, atol=0)
    for key, value in algorithm.vehicle_target_q.state_dict().items():
        torch.testing.assert_close(value, vehicle_before[key], rtol=0, atol=0)


def test_iql_loads_pre_fix_v1_trainer_state_with_safe_role_counters(contract) -> None:
    algorithm = build_algorithm("iql_mobile", contract, "cpu", candidate_id="c01")
    state = copy.deepcopy(algorithm.state_dict())
    del state["trainer"]["role_update_count"]

    restored = build_algorithm("iql_mobile", contract, "cpu", candidate_id="c01")
    restored.load_state_dict(state)

    assert restored.trainer.role_update_count == {"uav": 0, "vehicle": 0}
    assert restored.trainer.state_dict()["schema_version"] == "g5-iql-trainer-v1"


def test_iql_new_v1_state_rejects_malformed_role_update_count(contract) -> None:
    algorithm = build_algorithm("iql_mobile", contract, "cpu", candidate_id="c01")
    state = copy.deepcopy(algorithm.state_dict())
    state["trainer"]["role_update_count"] = {"uav": 0}

    with pytest.raises(ValueError, match="role update counters"):
        algorithm.trainer.load_state_dict(state["trainer"])


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_deterministic_evaluation_does_not_mutate_exploration_or_replay(contract, method_id: str) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu", candidate_id="c01")
    before = copy.deepcopy(algorithm.state_dict())
    result = algorithm.act(_observations(), _masks(), deterministic=True)
    after = algorithm.state_dict()

    for role in ("uav", "vehicle"):
        assert result.masks[role][np.arange(len(result.actions[role])), result.actions[role]].all()
    assert after["exploration"] == before["exploration"]
    assert after["replay"] == before["replay"] if method_id == "maddpg_mobile" else after["uav_replay"] == before["uav_replay"]


def test_replay_restore_is_fail_closed_before_live_mutation() -> None:
    replay = JointReplayBuffer(capacity=2, seed=7)
    replay.append(_envelope())
    before = replay.rows()[0].state_dict()
    malformed = replay.state_dict()
    malformed["size"] = 2

    with pytest.raises(ValueError, match="size"):
        replay.load_state_dict(malformed)

    restored = replay.rows()[0].state_dict()
    assert restored["role_batch"]["transition_id"] == before["role_batch"]["transition_id"]
    np.testing.assert_array_equal(
        restored["role_batch"]["masks"]["uav"],
        before["role_batch"]["masks"]["uav"],
    )


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_off_policy_checkpoint_round_trip_preserves_next_deterministic_action(tmp_path, contract, method_id: str) -> None:
    algorithm = build_algorithm(method_id, contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope())
    path = tmp_path / f"{method_id}.pt"
    save_training_checkpoint(path, {"algorithm": algorithm.state_dict()}, _provenance())
    restored, _ = load_training_checkpoint(
        path,
        lambda: build_algorithm(method_id, contract, "cpu", candidate_id="c01"),
        _provenance(),
    )

    original = algorithm.act(_observations(), _masks(), deterministic=True)
    resumed = restored.act(_observations(), _masks(), deterministic=True)
    for role in ("uav", "vehicle"):
        np.testing.assert_array_equal(original.actions[role], resumed.actions[role])


@pytest.mark.parametrize("method_id", METHOD_IDS)
def test_off_policy_checkpoint_resume_matches_the_next_update(tmp_path, contract, method_id: str) -> None:
    torch = pytest.importorskip("torch")
    import random

    random.seed(91)
    np.random.seed(91)
    torch.manual_seed(91)
    algorithm = build_algorithm(method_id, contract, "cpu", candidate_id="c01")
    algorithm.observe(_envelope())
    path = tmp_path / f"{method_id}-update.pt"
    save_training_checkpoint(path, {"algorithm": algorithm.state_dict()}, _provenance())
    uninterrupted = algorithm.update()
    resumed, _ = load_training_checkpoint(
        path,
        lambda: build_algorithm(method_id, contract, "cpu", candidate_id="c01"),
        _provenance(),
    )
    replayed = resumed.update()

    assert replayed.keys() == uninterrupted.keys()
    for key in uninterrupted:
        assert replayed[key] == pytest.approx(uninterrupted[key])
