"""Versioned joint transition replay with deterministic sampling after resume."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np

from problem2.algorithms.protocol import OffPolicyEnvelope, RoleBatch


JOINT_REPLAY_SCHEMA_VERSION = "g5-joint-replay-v1"


class JointReplayBuffer:
    def __init__(self, capacity: int, seed: int | None = None) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("replay capacity must be a positive integer")
        self.capacity = capacity
        self._data: list[RoleBatch | None] = [None] * capacity
        self.insertion_index = 0
        self.size = 0
        self._rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return self.size

    @staticmethod
    def _copy_row(row: RoleBatch | OffPolicyEnvelope) -> RoleBatch | OffPolicyEnvelope:
        if isinstance(row, OffPolicyEnvelope):
            return OffPolicyEnvelope.from_state_dict(row.state_dict())
        if isinstance(row, RoleBatch):
            return RoleBatch.from_state_dict(row.state_dict())
        raise TypeError("replay accepts RoleBatch or OffPolicyEnvelope transitions")

    @staticmethod
    def _decode_row(state: Mapping[str, Any]) -> RoleBatch | OffPolicyEnvelope:
        if not isinstance(state, Mapping):
            raise ValueError("replay rows must be mappings")
        schema = state.get("schema_version")
        if schema == "g5-role-batch-v1":
            return RoleBatch.from_state_dict(state)
        if schema == "g5-off-policy-envelope-v1":
            return OffPolicyEnvelope.from_state_dict(state)
        raise ValueError("replay row has an unsupported schema")

    def append(self, batch: RoleBatch | OffPolicyEnvelope) -> None:
        if not isinstance(batch, (RoleBatch, OffPolicyEnvelope)):
            raise TypeError("replay accepts RoleBatch or OffPolicyEnvelope transitions")
        self._data[self.insertion_index] = self._copy_row(batch)
        self.insertion_index = (self.insertion_index + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def rows(self) -> list[RoleBatch | OffPolicyEnvelope]:
        return [
            self._copy_row(row)
            for row in self._data
            if row is not None
        ]

    def sample(self, count: int) -> list[RoleBatch | OffPolicyEnvelope]:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0 or count > self.size:
            raise ValueError("sample count must be between one and replay size")
        rows = self.rows()
        indices = self._rng.choice(len(rows), size=count, replace=False)
        return [self._copy_row(rows[int(index)]) for index in indices]

    def state_dict(self) -> dict[str, Any]:
        return {"schema_version": JOINT_REPLAY_SCHEMA_VERSION, "capacity": self.capacity, "data": [None if row is None else row.state_dict() for row in self._data], "insertion_index": self.insertion_index, "size": self.size, "rng_state": deepcopy(self._rng.bit_generator.state)}

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        expected_keys = {"schema_version", "capacity", "data", "insertion_index", "size", "rng_state"}
        if not isinstance(state, Mapping) or set(state) != expected_keys or state.get("schema_version") != JOINT_REPLAY_SCHEMA_VERSION:
            raise ValueError("unsupported joint replay schema")
        if state.get("capacity") != self.capacity:
            raise ValueError("replay capacity does not match checkpoint")
        data, index, size = state.get("data"), state.get("insertion_index"), state.get("size")
        if not isinstance(data, list) or len(data) != self.capacity:
            raise ValueError("replay data does not match capacity")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < self.capacity:
            raise ValueError("replay insertion index is invalid")
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= self.capacity:
            raise ValueError("replay size is invalid")
        restored = [None if row is None else self._decode_row(row) for row in data]
        if sum(row is not None for row in restored) != size:
            raise ValueError("replay size does not match stored rows")
        if size < self.capacity:
            if index != size or any(row is None for row in restored[:size]) or any(row is not None for row in restored[size:]):
                raise ValueError("replay sparse layout is invalid")
        elif any(row is None for row in restored):
            raise ValueError("full replay must not contain empty ring slots")
        rng_state = state.get("rng_state")
        if not isinstance(rng_state, Mapping):
            raise ValueError("replay RNG state is missing")
        generator = np.random.default_rng()
        try:
            generator.bit_generator.state = deepcopy(dict(rng_state))
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError("replay RNG state is invalid") from error
        self._data, self.insertion_index, self.size, self._rng = restored, index, size, generator


__all__ = ["JOINT_REPLAY_SCHEMA_VERSION", "JointReplayBuffer"]
