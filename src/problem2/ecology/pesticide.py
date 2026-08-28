"""Persistent pesticide effect state for the dynamic Problem-2 ecology."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np

from .config import DynamicEcologyConfig


@dataclass(frozen=True, slots=True)
class AcceptedSpray:
    """A physically accepted spray event expressed in litres."""

    row: int
    col: int
    delta_l: float


def _validate_population(value: np.ndarray, name: str, shape: tuple[int, int]) -> np.ndarray:
    if not isinstance(value, np.ndarray) or value.ndim != 2 or value.shape != shape:
        raise ValueError(f"{name} must be a two-dimensional array with shape {shape}")
    if (
        not np.issubdtype(value.dtype, np.number)
        or not np.all(np.isfinite(value))
        or np.any(value < 0.0)
    ):
        raise ValueError(f"{name} must contain only finite numeric values")
    return value


class PesticideEffectField:
    """Radius-weighted, persistent pesticide concentration on an ecology grid."""

    def __init__(self, shape: tuple[int, int], config: DynamicEcologyConfig) -> None:
        self.shape = shape
        self.config = config
        self.concentration = np.zeros(shape, dtype=np.float32)
        self.duration = np.zeros(shape, dtype=np.float32)
        self.spray_count = np.zeros(shape, dtype=np.int32)

    @classmethod
    def empty(
        cls, shape: tuple[int, int], config: DynamicEcologyConfig
    ) -> "PesticideEffectField":
        if (
            not isinstance(shape, tuple)
            or len(shape) != 2
            or any(isinstance(axis, bool) or not isinstance(axis, int) or axis <= 0 for axis in shape)
        ):
            raise ValueError("shape must be a pair of positive integers")
        if not isinstance(config, DynamicEcologyConfig):
            raise TypeError("config must be a DynamicEcologyConfig")
        return cls(shape, config)

    def deposit(self, spray: AcceptedSpray, reference_volume_l: float) -> None:
        """Deposit an accepted physical spray using the Problem-1 radial profile."""

        if not isinstance(spray, AcceptedSpray):
            raise TypeError("spray must be an AcceptedSpray")
        if (
            isinstance(spray.row, bool)
            or not isinstance(spray.row, int)
            or isinstance(spray.col, bool)
            or not isinstance(spray.col, int)
            or not (0 <= spray.row < self.shape[0] and 0 <= spray.col < self.shape[1])
        ):
            raise ValueError("spray center is out of bounds")
        if (
            isinstance(reference_volume_l, bool)
            or not isinstance(reference_volume_l, (int, float))
            or not math.isfinite(float(reference_volume_l))
            or float(reference_volume_l) <= 0.0
        ):
            raise ValueError("reference_volume_l must be finite and positive")
        if (
            isinstance(spray.delta_l, bool)
            or not isinstance(spray.delta_l, (int, float))
            or not math.isfinite(float(spray.delta_l))
            or float(spray.delta_l) <= 0.0
        ):
            raise ValueError("spray delta_l must be finite and positive")

        amount = self.config.effect_amount * float(spray.delta_l) / float(reference_volume_l)
        radius = self.config.spray_radius
        row, col = spray.row, spray.col
        for d_row in range(-radius, radius + 1):
            for d_col in range(-radius, radius + 1):
                distance = math.hypot(d_row, d_col)
                if distance > radius:
                    continue
                target_row = row + d_row
                target_col = col + d_col
                if not (0 <= target_row < self.shape[0] and 0 <= target_col < self.shape[1]):
                    continue
                weight = 1.0 - distance / (radius + 1.0)
                deposited = amount * weight
                self.concentration[target_row, target_col] = min(
                    self.config.concentration_cap,
                    float(self.concentration[target_row, target_col]) + deposited,
                )
                self.duration[target_row, target_col] = max(
                    float(self.duration[target_row, target_col]),
                    self.config.effect_duration,
                )
        self.spray_count[row, col] += 1

    def apply_mortality(
        self, prey: np.ndarray, predator: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return prey and predator fields after current pesticide mortality."""

        prey = _validate_population(prey, "prey", self.shape)
        predator = _validate_population(predator, "predator", self.shape)
        prey_kill = np.minimum(
            self.concentration * self.config.prey_mortality_scale,
            self.config.prey_mortality_cap,
        )
        predator_kill = np.minimum(
            self.concentration * self.config.predator_sensitivity,
            self.config.predator_mortality_cap,
        )
        return prey * (1.0 - prey_kill), predator * (1.0 - predator_kill)

    def decay(self) -> None:
        """Advance effect duration, decay concentration, and clear expired cells."""

        self.duration[...] = np.maximum(self.duration - 1.0, 0.0)
        self.concentration[...] *= self.config.decay_rate
        expired = self.duration <= 0.0
        self.concentration[expired] = 0.0
        self.concentration[self.concentration < self.config.prey_extinction_threshold] = 0.0

    def state_dict(self) -> dict[str, object]:
        """Return a detached ecological snapshot; physical litres are not included."""

        return {
            "shape": self.shape,
            "concentration": self.concentration.copy(),
            "duration": self.duration.copy(),
            "spray_count": self.spray_count.copy(),
        }

    @classmethod
    def from_state_dict(
        cls, state: Mapping[str, object], config: DynamicEcologyConfig
    ) -> "PesticideEffectField":
        if not isinstance(state, Mapping):
            raise ValueError("pesticide state must be a mapping")
        expected = {"shape", "concentration", "duration", "spray_count"}
        if set(state) != expected:
            raise ValueError("pesticide state keys drifted")
        shape = state["shape"]
        if not isinstance(shape, tuple) or len(shape) != 2:
            raise ValueError("pesticide state shape is invalid")
        field = cls.empty(shape, config)
        for name, dtype in (
            ("concentration", np.dtype(np.float32)),
            ("duration", np.dtype(np.float32)),
            ("spray_count", np.dtype(np.int32)),
        ):
            value = state[name]
            if not isinstance(value, np.ndarray) or value.shape != shape or value.dtype != dtype:
                raise ValueError(f"pesticide state {name} has invalid shape or dtype")
            if not np.all(np.isfinite(value)):
                raise ValueError(f"pesticide state {name} must be finite")
            if name == "concentration" and (
                np.any(value < 0.0) or np.any(value > config.concentration_cap)
            ):
                raise ValueError("concentration contains values outside its ecological domain")
            if name == "duration" and (
                np.any(value < 0.0)
                or np.any(value > config.effect_duration)
                or np.any(value != np.floor(value))
            ):
                raise ValueError("duration contains values outside its ecological domain")
            if name == "spray_count" and np.any(value < 0):
                raise ValueError("spray_count contains values outside its ecological domain")
            setattr(field, name, value.copy())
        return field


__all__ = ["AcceptedSpray", "PesticideEffectField"]
