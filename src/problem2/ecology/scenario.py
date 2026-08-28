"""Scenario-owned wind state for the dynamic Problem-2 ecology."""

from __future__ import annotations

from dataclasses import dataclass
import copy
import math
from typing import Mapping

import numpy as np

from .config import DynamicEcologyConfig


@dataclass(frozen=True, slots=True)
class WindState:
    direction: float
    strength: float
    step_count: int

    @property
    def vector(self) -> tuple[float, float]:
        return (
            self.strength * math.cos(self.direction),
            self.strength * math.sin(self.direction),
        )


def _validate_state(state: WindState, config: DynamicEcologyConfig) -> None:
    if not math.isfinite(state.direction) or not math.isfinite(state.strength):
        raise ValueError("wind state must be finite")
    if not 0.0 <= state.strength <= config.wind_strength_range[1]:
        raise ValueError("wind strength is outside the configured range")
    if isinstance(state.step_count, bool) or not isinstance(state.step_count, int) or state.step_count < 0:
        raise ValueError("wind step_count must be a non-negative integer")


class DynamicWind:
    """A deterministic wind process backed by an explicit NumPy Generator."""

    def __init__(
        self, rng: np.random.Generator, state: WindState, config: DynamicEcologyConfig
    ) -> None:
        if not isinstance(rng, np.random.Generator):
            raise TypeError("rng must be a NumPy Generator")
        if not isinstance(state, WindState):
            raise TypeError("state must be a WindState")
        if not isinstance(config, DynamicEcologyConfig):
            raise TypeError("config must be a DynamicEcologyConfig")
        _validate_state(state, config)
        self.rng = rng
        self.state = state
        self.config = config

    @classmethod
    def initialize(
        cls, rng: np.random.Generator, config: DynamicEcologyConfig
    ) -> "DynamicWind":
        direction = float(rng.uniform(0.0, 2.0 * np.pi))
        lower, upper = config.wind_strength_range
        strength = float(rng.uniform(lower, upper))
        return cls(rng, WindState(direction, strength, 0), config)

    def update(self) -> WindState:
        step_count = self.state.step_count + 1
        direction = (
            self.state.direction
            + float(self.rng.normal(0.0, self.config.wind_direction_noise_std))
            + self.config.wind_slow_direction_amplitude
            * math.sin(step_count / self.config.wind_slow_direction_period)
        ) % (2.0 * np.pi)
        lower, upper = self.config.wind_strength_range
        strength = float(
            np.clip(
                self.state.strength
                + self.rng.normal(0.0, self.config.wind_strength_noise_std),
                lower,
                upper,
            )
        )
        self.state = WindState(direction, strength, step_count)
        return self.state

    def state_dict(self) -> dict[str, object]:
        """Return wind and generator state with detached nested values."""

        return {
            "state": {
                "direction": self.state.direction,
                "strength": self.state.strength,
                "step_count": self.state.step_count,
            },
            "bit_generator": type(self.rng.bit_generator).__name__,
            "rng_state": copy.deepcopy(self.rng.bit_generator.state),
        }

    @classmethod
    def from_state_dict(
        cls, state: Mapping[str, object], config: DynamicEcologyConfig
    ) -> "DynamicWind":
        if not isinstance(state, Mapping):
            raise ValueError("wind state must be a mapping")
        if set(state) != {"state", "bit_generator", "rng_state"}:
            raise ValueError("wind state keys drifted")
        raw_state = state["state"]
        if not isinstance(raw_state, Mapping) or set(raw_state) != {
            "direction",
            "strength",
            "step_count",
        }:
            raise ValueError("wind state payload is invalid")
        wind_state = WindState(
            float(raw_state["direction"]),
            float(raw_state["strength"]),
            int(raw_state["step_count"]),
        )
        _validate_state(wind_state, config)
        bit_generator_name = state["bit_generator"]
        if not isinstance(bit_generator_name, str) or not bit_generator_name:
            raise ValueError("wind bit-generator name is invalid")
        bit_generator_type = getattr(np.random, bit_generator_name, None)
        if not isinstance(bit_generator_type, type) or not issubclass(
            bit_generator_type, np.random.BitGenerator
        ):
            raise ValueError("wind bit-generator name is unsupported")
        bit_generator = bit_generator_type()
        bit_generator.state = copy.deepcopy(state["rng_state"])
        return cls(np.random.Generator(bit_generator), wind_state, config)


__all__ = ["DynamicWind", "WindState"]
