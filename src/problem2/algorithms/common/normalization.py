"""Running normalization used by SR-MAPPO.

Statistics are updated only while collecting training rollouts. Evaluation uses
the frozen statistics and therefore cannot leak information from test episodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class RunningNormalizer:
    """Numerically stable per-feature running mean and variance."""

    epsilon: float = 1e-8
    clip: float | None = 10.0

    def __post_init__(self) -> None:
        self.mean: np.ndarray | None = None
        self.m2: np.ndarray | None = None
        self.count: int = 0

    @property
    def variance(self) -> np.ndarray:
        if self.m2 is None or self.count == 0:
            return np.array(1.0, dtype=np.float64)
        return self.m2 / max(self.count, 1)

    def update(self, values: Any) -> None:
        array = np.asarray(values, dtype=np.float64)
        if array.ndim == 0:
            array = array.reshape(1, 1)
        elif array.ndim == 1:
            array = array.reshape(1, -1)
        batch_count = array.shape[0]
        batch_mean = array.mean(axis=0)
        batch_m2 = ((array - batch_mean) ** 2).sum(axis=0)
        if self.mean is None:
            self.mean = batch_mean.copy()
            self.m2 = batch_m2.copy()
            self.count = batch_count
            return
        delta = batch_mean - self.mean
        total = self.count + batch_count
        self.m2 = self.m2 + batch_m2 + delta * delta * self.count * batch_count / total
        self.mean = self.mean + delta * batch_count / total
        self.count = total

    def normalize(self, values: Any, *, update: bool = False) -> np.ndarray:
        array = np.asarray(values, dtype=np.float64)
        if update:
            self.update(array)
        if self.mean is None:
            result = array.copy()
        else:
            result = (array - self.mean) / np.sqrt(self.variance + self.epsilon)
        if self.clip is not None:
            result = np.clip(result, -self.clip, self.clip)
        return result.astype(np.float32)

    def state_dict(self) -> dict[str, Any]:
        return {"mean": self.mean, "m2": self.m2, "count": self.count, "epsilon": self.epsilon, "clip": self.clip}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.mean = None if state.get("mean") is None else np.asarray(state["mean"], dtype=np.float64)
        self.m2 = None if state.get("m2") is None else np.asarray(state["m2"], dtype=np.float64)
        self.count = int(state.get("count", 0))
        self.epsilon = float(state.get("epsilon", self.epsilon))
        self.clip = state.get("clip", self.clip)


ObservationNormalizer = RunningNormalizer
ReturnNormalizer = RunningNormalizer
