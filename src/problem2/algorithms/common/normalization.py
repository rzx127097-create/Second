from __future__ import annotations

from typing import Any

import numpy as np


class RunningNormalizer:
    """Running population statistics for one role-local feature space."""

    def __init__(
        self,
        shape: int | tuple[int, ...],
        *,
        role: str,
        epsilon: float = 1e-8,
    ) -> None:
        if isinstance(shape, int):
            shape = (shape,)
        else:
            shape = tuple(shape)
        if not shape or any(not isinstance(item, int) or item <= 0 for item in shape):
            raise ValueError("shape must contain positive dimensions")
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be non-empty text")
        epsilon = float(epsilon)
        if not np.isfinite(epsilon) or epsilon <= 0.0:
            raise ValueError("epsilon must be positive and finite")

        self.shape = shape
        self.role = role
        self.epsilon = epsilon
        self.count = 0
        self.mean = np.zeros(shape, dtype=np.float64)
        self.variance = np.ones(shape, dtype=np.float64)
        self.version = 0

    def _samples(self, values: Any) -> np.ndarray:
        array = np.asarray(values, dtype=np.float64)
        if array.ndim < len(self.shape) or array.shape[-len(self.shape) :] != self.shape:
            raise ValueError(f"values must end with role shape {self.shape}")
        samples = array.reshape((-1,) + self.shape)
        if not np.isfinite(samples).all():
            raise ValueError("values must contain only finite numbers")
        return samples

    def update(self, values: Any) -> None:
        samples = self._samples(values)
        sample_count = len(samples)
        if sample_count == 0:
            return
        sample_mean = samples.mean(axis=0, dtype=np.float64)
        sample_variance = samples.var(axis=0, dtype=np.float64)

        if self.count == 0:
            self.mean = sample_mean
            self.variance = sample_variance
            self.count = sample_count
        else:
            total = self.count + sample_count
            delta = sample_mean - self.mean
            combined_m2 = (
                self.variance * self.count
                + sample_variance * sample_count
                + np.square(delta) * self.count * sample_count / total
            )
            self.mean = self.mean + delta * sample_count / total
            self.variance = combined_m2 / total
            self.count = total
        self.version += 1

    def normalize(self, values: Any, update: bool = False) -> np.ndarray:
        if update:
            self.update(values)
        array = np.asarray(values, dtype=np.float64)
        if array.ndim < len(self.shape) or array.shape[-len(self.shape) :] != self.shape:
            raise ValueError(f"values must end with role shape {self.shape}")
        if not np.isfinite(array).all():
            raise ValueError("values must contain only finite numbers")
        scale = np.sqrt(np.maximum(self.variance, 0.0) + self.epsilon)
        return ((array - self.mean) / scale).astype(np.float32)

    def state_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "shape": self.shape,
            "epsilon": self.epsilon,
            "count": self.count,
            "mean": self.mean.copy(),
            "variance": self.variance.copy(),
            "var": self.variance.copy(),
            "version": self.version,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict):
            raise TypeError("normalizer state must be a mapping")
        if state.get("role") != self.role:
            raise ValueError("normalizer role does not match")
        state_shape = tuple(state.get("shape", ()))
        if state_shape != self.shape:
            raise ValueError("normalizer shape does not match")
        count = state.get("count")
        version = state.get("version", 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("normalizer count must be a nonnegative integer")
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise ValueError("normalizer version must be a nonnegative integer")

        mean = np.asarray(state.get("mean"), dtype=np.float64)
        variance_value = state.get("variance", state.get("var"))
        variance = np.asarray(variance_value, dtype=np.float64)
        if mean.shape != self.shape or variance.shape != self.shape:
            raise ValueError("normalizer statistics do not match shape")
        if not np.isfinite(mean).all() or not np.isfinite(variance).all():
            raise ValueError("normalizer statistics must be finite")
        if (variance < 0.0).any():
            raise ValueError("normalizer variance must be nonnegative")

        self.count = count
        self.mean = mean.copy()
        self.variance = variance.copy()
        self.version = version
