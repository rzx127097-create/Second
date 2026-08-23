from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np
import pytest

from problem2.algorithms.common.checkpoint import (
    TRAINING_CHECKPOINT_FORMAT_VERSION,
    load_training_checkpoint,
    save_training_checkpoint,
)
from problem2.algorithms.common.diagnostics import DiagnosticCounters
from problem2.algorithms.common.replay import JointReplayBuffer
from problem2.algorithms.protocol import HeterogeneousAlgorithm


class ResumableTwoRoleAlgorithm(HeterogeneousAlgorithm):
    def __init__(self) -> None:
        self.weight = 0.0
        self.evaluation = False
        self._diagnostics = DiagnosticCounters()

    def act(self, observations, masks, deterministic=False):
        raise NotImplementedError

    def observe(self, batch) -> None:
        raise NotImplementedError

    def update(self):
        self.weight += random.random() + float(np.random.random())
        self.weight += float(__import__("torch").rand(1).item())
        self._diagnostics.increment("updates")
        return {"weight": self.weight}

    def set_evaluation(self, enabled: bool) -> None:
        self.evaluation = bool(enabled)

    def state_dict(self):
        return {
            "weight": self.weight,
            "evaluation": self.evaluation,
            "diagnostics": self._diagnostics.state_dict(),
        }

    def load_state_dict(self, state) -> None:
        self.weight = float(state["weight"])
        self.evaluation = bool(state["evaluation"])
        self._diagnostics.load_state_dict(state["diagnostics"])

    @property
    def diagnostics(self) -> DiagnosticCounters:
        return self._diagnostics


def _provenance(**overrides: str) -> dict[str, str]:
    values = {
        "source_commit": "a" * 40,
        "source_bundle_sha256": "b" * 64,
        "config_hash": "b" * 64,
        "protocol_hash": "c" * 64,
        "ancestry_hash": "d" * 64,
    }
    values.update(overrides)
    return values


def _state(algorithm: ResumableTwoRoleAlgorithm) -> dict:
    replay = JointReplayBuffer(capacity=4, seed=5)
    return {
        "algorithm": algorithm.state_dict(),
        "method_state": {"target_updates": 3, "exploration": {"temperature": 0.7}},
        "replay": replay.state_dict(),
        "rollout_position": 7,
        "counters": {"episode": 2, "interaction": 19, "update": 3, "checkpoint": 1},
    }


def _factory() -> ResumableTwoRoleAlgorithm:
    return ResumableTwoRoleAlgorithm()


def test_checkpoint_hash_is_calculated_after_verified_reload_and_full_state_is_preserved(tmp_path: Path) -> None:
    algorithm = _factory()
    path = tmp_path / "training.pt"

    record = save_training_checkpoint(path, _state(algorithm), _provenance())
    restored, loaded = load_training_checkpoint(path, _factory, _provenance())

    assert record.format_version == TRAINING_CHECKPOINT_FORMAT_VERSION
    assert record.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert loaded.sha256 == record.sha256
    assert loaded.state["method_state"] == {"target_updates": 3, "exploration": {"temperature": 0.7}}
    assert loaded.state["rollout_position"] == 7
    assert loaded.state["replay"]["schema_version"] == "g5-joint-replay-v1"
    assert restored.state_dict() == algorithm.state_dict()


@pytest.mark.parametrize("key", ["source_commit", "source_bundle_sha256", "config_hash", "protocol_hash", "ancestry_hash"])
def test_checkpoint_rejects_hash_drift(tmp_path: Path, key: str) -> None:
    path = tmp_path / "training.pt"
    save_training_checkpoint(path, _state(_factory()), _provenance())
    expected = _provenance(**{key: "e" * 64})

    with pytest.raises(ValueError, match=key):
        load_training_checkpoint(path, _factory, expected)


@pytest.mark.parametrize(
    "provenance",
    [
        {key: value for key, value in _provenance().items() if key != "config_hash"},
        {**_provenance(), "unexpected_hash": "e" * 64},
        _provenance(source_commit="A" * 40),
        _provenance(source_bundle_sha256="z" * 64),
    ],
)
def test_checkpoint_rejects_non_exact_provenance_schema(tmp_path: Path, provenance: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="provenance"):
        save_training_checkpoint(tmp_path / "training.pt", _state(_factory()), provenance)


@pytest.mark.parametrize(
    "expected",
    [
        {},
        {"source_commit": "a" * 40},
        {**_provenance(), "unexpected_hash": "e" * 64},
        _provenance(protocol_hash="UPPER" + "c" * 59),
    ],
)
def test_checkpoint_rejects_non_exact_expected_hash_schema(tmp_path: Path, expected: dict[str, str]) -> None:
    path = tmp_path / "training.pt"
    save_training_checkpoint(path, _state(_factory()), _provenance())

    with pytest.raises(ValueError, match="expected_hashes"):
        load_training_checkpoint(path, _factory, expected)


def test_atomic_replacement_retains_the_last_valid_checkpoint_after_new_file_verification(tmp_path: Path) -> None:
    path = tmp_path / "training.pt"
    first = _factory()
    first.weight = 1.0
    first_record = save_training_checkpoint(path, _state(first), _provenance())
    second = _factory()
    second.weight = 2.0
    second_record = save_training_checkpoint(path, _state(second), _provenance())
    previous = Path(f"{path}.previous")

    previous_algorithm, previous_record = load_training_checkpoint(previous, _factory, _provenance())
    current_algorithm, current_record = load_training_checkpoint(path, _factory, _provenance())

    assert previous.exists()
    assert previous_record.sha256 == first_record.sha256
    assert previous_algorithm.weight == 1.0
    assert current_record.sha256 == second_record.sha256
    assert current_algorithm.weight == 2.0


def test_checkpoint_restores_all_rng_states_for_next_update_equivalence(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    random.seed(88)
    np.random.seed(88)
    torch.manual_seed(88)
    uninterrupted = _factory()
    uninterrupted.update()
    path = tmp_path / "training.pt"
    save_training_checkpoint(path, _state(uninterrupted), _provenance())
    uninterrupted_next = uninterrupted.update()

    random.seed(999)
    np.random.seed(999)
    torch.manual_seed(999)
    resumed, record = load_training_checkpoint(path, _factory, _provenance())
    resumed_next = resumed.update()

    assert record.state["rng"]
    assert resumed_next["weight"] == pytest.approx(uninterrupted_next["weight"])
    assert resumed.diagnostics.snapshot() == uninterrupted.diagnostics.snapshot()
