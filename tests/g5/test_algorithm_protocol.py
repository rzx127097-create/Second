from __future__ import annotations

import copy

import numpy as np
import pytest

from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.masked_distribution import masked_categorical
from problem2.algorithms.common.networks import RoleNetwork
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import (
    ActionResult,
    HeterogeneousAlgorithm,
    RoleBatch,
)


class FakeTwoRoleAlgorithm(HeterogeneousAlgorithm):
    """Minimal conformance implementation; production methods stay separate."""

    def __init__(self) -> None:
        self.evaluation = False
        self.transitions: list[RoleBatch] = []
        self.updates = 0
        self._diagnostics = DiagnosticCounters()

    def act(self, observations, masks, deterministic=False) -> ActionResult:
        actions: dict[str, np.ndarray] = {}
        for role in self.roles:
            legal = np.asarray(masks[role], dtype=bool)
            choices = np.argmax(legal, axis=1) if deterministic else np.asarray(
                [np.flatnonzero(row)[0] for row in legal], dtype=np.int64
            )
            actions[role] = choices.astype(np.int64)
        return ActionResult(actions=actions, masks=masks)

    def observe(self, batch: RoleBatch) -> None:
        self.transitions.append(batch)
        self._diagnostics.increment("observed_transitions")

    def update(self) -> dict[str, int]:
        self.updates += 1
        self._diagnostics.increment("updates")
        return {"updates": self.updates}

    def set_evaluation(self, enabled: bool) -> None:
        self.evaluation = bool(enabled)

    def state_dict(self):
        return {"evaluation": self.evaluation, "updates": self.updates}

    def load_state_dict(self, state) -> None:
        self.evaluation = bool(state["evaluation"])
        self.updates = int(state["updates"])

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics


@pytest.fixture
def two_role_algorithm() -> FakeTwoRoleAlgorithm:
    return FakeTwoRoleAlgorithm()


@pytest.fixture
def batch() -> RoleBatch:
    return RoleBatch(
        observations={
            "uav": np.zeros((2, 6), dtype=np.float32),
            "vehicle": np.zeros((1, 5), dtype=np.float32),
        },
        masks={
            "uav": np.array([[True, False, True], [False, True, False]]),
            "vehicle": np.array([[True, False]]),
        },
        actions={"uav": np.array([0, 1]), "vehicle": np.array([0])},
        rewards={"uav": np.array([1.0, 1.0]), "vehicle": np.array([1.0])},
        next_observations={
            "uav": np.ones((2, 6), dtype=np.float32),
            "vehicle": np.ones((1, 5), dtype=np.float32),
        },
        next_masks={
            "uav": np.array([[True, True, False], [True, False, False]]),
            "vehicle": np.array([[True, True]]),
        },
        terminated=False,
        truncated=False,
        scenario_id="development-10000",
        transition_id="development-10000:0",
    )


@pytest.mark.parametrize("role,shape", [("uav", (2, 6)), ("vehicle", (1, 5))])
def test_protocol_never_selects_masked_action(two_role_algorithm, batch, role, shape):
    result = two_role_algorithm.act(batch.observations, batch.masks, deterministic=False)
    assert result.actions[role].shape == shape[:1]
    assert batch.masks[role][np.arange(shape[0]), result.actions[role]].all()


def test_role_batch_preserves_exact_behavior_data_and_rejects_masked_actions(batch) -> None:
    original = copy.deepcopy(batch.masks)
    batch.masks["uav"][0, 2] = False

    restored = RoleBatch.from_state_dict(batch.state_dict())

    assert restored.transition_id == "development-10000:0"
    assert restored.scenario_id == "development-10000"
    assert restored.state_dict()["masks"]["uav"].tolist() == [[True, False, False], [False, True, False]]
    assert original["vehicle"].tolist() == [[True, False]]
    with pytest.raises(ValueError, match="illegal"):
        RoleBatch(
            observations=batch.observations,
            masks=original,
            actions={"uav": np.array([1, 1]), "vehicle": np.array([0])},
            rewards=batch.rewards,
            next_observations=batch.next_observations,
            next_masks=batch.next_masks,
            terminated=False,
            truncated=False,
            scenario_id=batch.scenario_id,
            transition_id="development-10000:illegal",
        )


def test_protocol_exposes_required_two_role_operations(two_role_algorithm, batch) -> None:
    two_role_algorithm.observe(batch)
    two_role_algorithm.set_evaluation(True)

    assert two_role_algorithm.roles == ("uav", "vehicle")
    assert two_role_algorithm.update() == {"updates": 1}
    assert two_role_algorithm.state_dict() == {"evaluation": True, "updates": 1}
    assert two_role_algorithm.diagnostics.snapshot()["updates"] == 1


def test_replay_state_contains_ring_position_size_rng_schema_and_independent_rows(batch) -> None:
    replay = JointReplayBuffer(capacity=2, seed=13)
    replay.append(batch)
    replay.append(RoleBatch.from_state_dict({**batch.state_dict(), "transition_id": "development-10000:1"}))
    replay.append(RoleBatch.from_state_dict({**batch.state_dict(), "transition_id": "development-10000:2"}))

    state = replay.state_dict()
    restored = JointReplayBuffer(capacity=2, seed=999)
    restored.load_state_dict(state)

    assert state["schema_version"] == "g5-joint-replay-v1"
    assert state["insertion_index"] == 1
    assert state["size"] == 2
    assert state["rng_state"]
    assert [row.transition_id for row in restored.rows()] == [
        "development-10000:2",
        "development-10000:1",
    ]
    assert [row.transition_id for row in restored.sample(2)] == [
        row.transition_id for row in replay.sample(2)
    ]


def test_shared_role_network_accepts_role_local_observations_only() -> None:
    torch = pytest.importorskip("torch")
    network = RoleNetwork(input_dim=6, action_dim=3, hidden_dim=8, depth=2)

    assert network(torch.zeros((2, 6))).shape == (2, 3)
    with pytest.raises(TypeError):
        network(torch.zeros((2, 6)), critic_state=torch.zeros((2, 4)))


def test_masked_distribution_rejects_behavior_action_drift() -> None:
    torch = pytest.importorskip("torch")
    distribution = masked_categorical(
        torch.tensor([[0.0, 1.0, 2.0]]), torch.tensor([[True, False, True]])
    )

    with pytest.raises(ValueError, match="masked"):
        distribution.log_prob(torch.tensor([1]))
