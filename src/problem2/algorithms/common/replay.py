"""Versioned joint transition replay with deterministic sampling after resume."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np

from problem2.algorithms.protocol import RoleBatch


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

    def append(self, batch: RoleBatch) -> None:
        if not isinstance(batch, RoleBatch):
            raise TypeError("replay accepts RoleBatch transitions")
        self._data[self.insertion_index] = RoleBatch.from_state_dict(batch.state_dict())
        self.insertion_index = (self.insertion_index + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def rows(self) -> list[RoleBatch]:
        return [row for row in self._data if row is not None]

    def sample(self, count: int) -> list[RoleBatch]:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0 or count > self.size:
            raise ValueError("sample count must be between one and replay size")
        rows = self.rows()
        indices = self._rng.choice(len(rows), size=count, replace=False)
        return [RoleBatch.from_state_dict(rows[int(index)].state_dict()) for index in indices]

    def state_dict(self) -> dict[str, Any]:
        return {"schema_version": JOINT_REPLAY_SCHEMA_VERSION, "capacity": self.capacity, "data": [None if row is None else row.state_dict() for row in self._data], "insertion_index": self.insertion_index, "size": self.size, "rng_state": deepcopy(self._rng.bit_generator.state)}

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping) or state.get("schema_version") != JOINT_REPLAY_SCHEMA_VERSION:
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
        restored = [None if row is None else RoleBatch.from_state_dict(row) for row in data]
        if sum(row is not None for row in restored) != size:
            raise ValueError("replay size does not match stored rows")
        rng_state = state.get("rng_state")
        if not isinstance(rng_state, Mapping):
            raise ValueError("replay RNG state is missing")
        generator = np.random.default_rng()
        generator.bit_generator.state = deepcopy(dict(rng_state))
        self._data, self.insertion_index, self.size, self._rng = restored, index, size, generator


__all__ = ["JOINT_REPLAY_SCHEMA_VERSION", "JointReplayBuffer"]
