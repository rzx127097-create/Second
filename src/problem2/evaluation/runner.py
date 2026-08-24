"""Deterministic, state-frozen episode evaluation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import pickle
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

import numpy as np

from problem2.algorithms.protocol import ActionResult
from problem2.evaluation.metrics import EpisodeRecord
from problem2.evaluation.partitions import assert_partition_allowed


class PolicyAdapter(Protocol):
    def set_evaluation(self, enabled: bool) -> None: ...

    def state_dict(self) -> dict[str, Any]: ...

    def load_state_dict(self, state: dict[str, Any]) -> None: ...

    def act(self, observations, masks, deterministic: bool = False) -> ActionResult: ...


def _canonical_state(value: Any) -> Any:
    if isinstance(value, Mapping):
        items = [(_canonical_state(key), _canonical_state(item)) for key, item in value.items()]
        items.sort(key=lambda pair: pickle.dumps(pair[0], protocol=5))
        return ("mapping", tuple(items))
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        return ("array", array.dtype.str, tuple(array.shape), array.tobytes())
    if isinstance(value, np.generic):
        return _canonical_state(value.item())
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        tensor = value.detach().cpu().contiguous()
        array = tensor.numpy()
        return ("tensor", str(tensor.dtype), tuple(tensor.shape), array.tobytes())
    if isinstance(value, tuple):
        return ("tuple", tuple(_canonical_state(item) for item in value))
    if isinstance(value, list):
        return ("list", tuple(_canonical_state(item) for item in value))
    if isinstance(value, (set, frozenset)):
        items = [_canonical_state(item) for item in value]
        items.sort(key=lambda item: pickle.dumps(item, protocol=5))
        return ("set", tuple(items))
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, (str, bytes, int, bool, type(None))):
        return (type(value).__name__, value)
    if isinstance(value, Path):
        return ("path", value.as_posix())
    return ("pickle", pickle.dumps(value, protocol=5))


def _state_identity(state: Any) -> str:
    canonical = pickle.dumps(_canonical_state(state), protocol=5)
    return hashlib.sha256(canonical).hexdigest()


def evaluate_episode(
    environment,
    policy: PolicyAdapter,
    partition: str,
    scenario_id: int,
    deterministic: bool = True,
) -> EpisodeRecord:
    assert_partition_allowed(partition, scenario_id)
    original = deepcopy(policy.state_dict())
    original_training = original.get("training")
    if type(original_training) is not bool:
        raise ValueError("policy state must expose an exact training flag")
    try:
        policy.set_evaluation(True)
        before = _state_identity(policy.state_dict())
        view = environment.reset(scenario_id=scenario_id)
        while not environment.state.terminated:
            started = perf_counter()
            result = policy.act(
                view["observations"], view["masks"], deterministic=deterministic
            )
            decision_runtime_s = perf_counter() - started
            view = environment.step(result, decision_runtime_s=decision_runtime_s)
        after = _state_identity(policy.state_dict())
        if before != after:
            raise RuntimeError(
                "deterministic evaluation mutated learning, normalization, or exploration state"
            )
        return replace(
            environment.episode_record(),
            evaluation_state_before=before,
            evaluation_state_after=after,
            evaluation_state_byte_identical=True,
        )
    finally:
        policy.load_state_dict(original)


__all__ = ["PolicyAdapter", "evaluate_episode"]
