"""Scenario-owned wind state for the dynamic Problem-2 ecology."""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import math
from numbers import Real
from typing import Any, Mapping

import numpy as np

from .config import DYNAMIC_ECOLOGY_VERSION, DynamicEcologyConfig
from .pesticide import PesticideEffectField


_PROBLEM1_SOURCE_COMMIT = "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"
_SCENARIO_IMPLEMENTATION_VERSION = DYNAMIC_ECOLOGY_VERSION
_PARTITION_RANGES = {
    "development": range(10000, 10020),
    "validation": range(20000, 20050),
    "sealed_test": range(30000, 30100),
}
_SCENARIO_STATE_KEYS = frozenset(
    {
        "partition",
        "scenario_id",
        "scale_id",
        "grid_shape",
        "initial_prey",
        "initial_predator",
        "initial_effect",
        "initial_wind",
        "rng_state",
        "config_hash",
        "source_commit",
        "implementation_version",
        "scenario_sha256",
    }
)


def _json_compatible(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_compatible(item) for item in value]
    return value


def _canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    try:
        return json.dumps(
            _json_compatible(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("scenario metadata is not canonically serializable") from exc


def _canonical_array(value: object, name: str, dtype: np.dtype[Any], shape: tuple[int, int]) -> np.ndarray:
    if not isinstance(value, np.ndarray) or value.ndim != 2 or value.shape != shape:
        raise ValueError(f"{name} must be a two-dimensional array with shape {shape}")
    if value.dtype != dtype:
        raise ValueError(f"{name} must have dtype {dtype.str}")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} must contain only finite values")
    if name != "initial_spray_count" and np.any(value < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    if name == "initial_spray_count" and np.any(value < 0):
        raise ValueError("initial_spray_count must be nonnegative")
    return np.array(value, dtype=dtype, order="C", copy=True)


def _validate_identity_text(value: object, name: str, length: int) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"{name} must be a lowercase SHA-256/SHA-1 identity")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256/SHA-1 identity")
    return value


def _validate_partition(partition: object, scenario_id: object) -> tuple[str, int]:
    if not isinstance(partition, str) or partition not in _PARTITION_RANGES:
        raise ValueError("scenario partition is undeclared")
    if isinstance(scenario_id, bool) or not isinstance(scenario_id, int):
        raise ValueError("scenario ID must be an integer in its partition")
    if scenario_id not in _PARTITION_RANGES[partition]:
        raise ValueError("scenario ID is outside its declared partition")
    return partition, scenario_id


def _validate_shape(grid_shape: object) -> tuple[int, int]:
    if (
        not isinstance(grid_shape, tuple)
        or len(grid_shape) != 2
        or any(
            isinstance(axis, bool) or not isinstance(axis, int) or axis < 2
            for axis in grid_shape
        )
    ):
        raise ValueError("grid_shape must contain two integers of at least two cells")
    return grid_shape


def _wind_payload(state: WindState) -> dict[str, object]:
    return {
        "direction": state.direction,
        "strength": state.strength,
        "step_count": state.step_count,
    }


def _wind_from_payload(value: object) -> WindState:
    if not isinstance(value, Mapping) or set(value) != {
        "direction",
        "strength",
        "step_count",
    }:
        raise ValueError("initial_wind state is incomplete")
    direction, strength, step_count = (
        value["direction"],
        value["strength"],
        value["step_count"],
    )
    if (
        isinstance(direction, bool)
        or not isinstance(direction, Real)
        or not math.isfinite(float(direction))
        or isinstance(strength, bool)
        or not isinstance(strength, Real)
        or not math.isfinite(float(strength))
        or isinstance(step_count, bool)
        or not isinstance(step_count, int)
        or step_count != 0
        or not 0.0 <= float(strength) <= 0.5
    ):
        raise ValueError("initial_wind state is invalid")
    return WindState(float(direction), float(strength), step_count)


def _validate_rng_state(value: object) -> tuple[str, dict[str, object]]:
    if not isinstance(value, Mapping) or "bit_generator" not in value:
        raise ValueError("rng_state is incomplete")
    name = value["bit_generator"]
    if not isinstance(name, str) or not name:
        raise ValueError("rng_state bit-generator name is invalid")
    bit_generator_type = getattr(np.random, name, None)
    if not isinstance(bit_generator_type, type) or not issubclass(
        bit_generator_type, np.random.BitGenerator
    ):
        raise ValueError("rng_state bit-generator name is unsupported")
    try:
        bit_generator = bit_generator_type()
        normalized_state = copy.deepcopy(dict(value))
        bit_generator.state = normalized_state
    except (TypeError, ValueError) as exc:
        raise ValueError("rng_state state is invalid") from exc
    return name, normalized_state


def _scenario_digest(
    *,
    partition: str,
    scenario_id: int,
    scale_id: str,
    grid_shape: tuple[int, int],
    initial_prey: np.ndarray,
    initial_predator: np.ndarray,
    initial_concentration: np.ndarray,
    initial_duration: np.ndarray,
    initial_spray_count: np.ndarray,
    initial_wind: WindState,
    rng_state: Mapping[str, object],
    config_hash: str,
    source_commit: str,
    implementation_version: str,
) -> str:
    bit_generator, raw_rng_state = _validate_rng_state(rng_state)
    metadata = {
        "partition": partition,
        "scenario_id": scenario_id,
        "scale_id": scale_id,
        "grid_shape": list(grid_shape),
        "config_hash": config_hash,
        "initial_wind": _wind_payload(initial_wind),
        "bit_generator": bit_generator,
        "rng_state": raw_rng_state,
        "source_commit": source_commit,
        "implementation_version": implementation_version,
    }
    digest = hashlib.sha256()
    digest.update(_canonical_json_bytes(metadata))
    for array in (
        initial_prey,
        initial_predator,
        initial_concentration,
        initial_duration,
        initial_spray_count,
    ):
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


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
    if (
        isinstance(state.direction, bool)
        or not isinstance(state.direction, Real)
        or not math.isfinite(float(state.direction))
    ):
        raise ValueError("wind direction must be a finite real number")
    if (
        isinstance(state.strength, bool)
        or not isinstance(state.strength, Real)
        or not math.isfinite(float(state.strength))
    ):
        raise ValueError("wind strength must be a finite real number")
    if not 0.0 <= state.strength <= config.wind_strength_range[1]:
        raise ValueError("wind strength is outside the configured range")
    if (
        isinstance(state.step_count, bool)
        or not isinstance(state.step_count, int)
        or state.step_count < 0
    ):
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
        direction = raw_state["direction"]
        strength = raw_state["strength"]
        step_count = raw_state["step_count"]
        if (
            isinstance(direction, bool)
            or not isinstance(direction, Real)
            or isinstance(strength, bool)
            or not isinstance(strength, Real)
        ):
            raise ValueError("wind direction and strength must be real numbers")
        if isinstance(step_count, bool) or not isinstance(step_count, int):
            raise ValueError("wind step_count must be an integer")
        wind_state = WindState(
            direction,
            strength,
            step_count,
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


@dataclass(frozen=True, slots=True)
class DynamicPestScenario:
    """Canonical initial state shared by every paired dynamic-ecology run."""

    partition: str
    scenario_id: int
    scale_id: str
    grid_shape: tuple[int, int]
    initial_prey: np.ndarray
    initial_predator: np.ndarray
    initial_concentration: np.ndarray
    initial_duration: np.ndarray
    initial_spray_count: np.ndarray
    initial_wind: WindState
    rng_state: dict[str, object]
    config_hash: str
    source_commit: str
    implementation_version: str
    scenario_sha256: str

    def __post_init__(self) -> None:
        partition, scenario_id = _validate_partition(self.partition, self.scenario_id)
        grid_shape = _validate_shape(self.grid_shape)
        if not isinstance(self.scale_id, str) or not self.scale_id.strip():
            raise ValueError("scale_id must be non-empty text")
        if not isinstance(self.initial_wind, WindState):
            raise ValueError("initial_wind must be a WindState")
        initial_wind = _wind_from_payload(_wind_payload(self.initial_wind))
        rng_name, raw_rng_state = _validate_rng_state(self.rng_state)
        if not isinstance(self.rng_state, dict) or "bit_generator" not in self.rng_state:
            raise ValueError("rng_state is incomplete")
        if rng_name != self.rng_state["bit_generator"]:
            raise ValueError("rng_state bit-generator name is inconsistent")
        config_hash = _validate_identity_text(self.config_hash, "config_hash", 64)
        if self.source_commit != _PROBLEM1_SOURCE_COMMIT:
            raise ValueError("source_commit is not the approved Problem-1 snapshot")
        if self.implementation_version != _SCENARIO_IMPLEMENTATION_VERSION:
            raise ValueError("implementation_version is unsupported")
        scenario_sha256 = _validate_identity_text(
            self.scenario_sha256, "scenario_sha256", 64
        )

        prey = _canonical_array(
            self.initial_prey, "initial_prey", np.dtype("<f8"), grid_shape
        )
        predator = _canonical_array(
            self.initial_predator, "initial_predator", np.dtype("<f8"), grid_shape
        )
        concentration = _canonical_array(
            self.initial_concentration,
            "initial_concentration",
            np.dtype("<f4"),
            grid_shape,
        )
        duration = _canonical_array(
            self.initial_duration, "initial_duration", np.dtype("<f4"), grid_shape
        )
        spray_count = _canonical_array(
            self.initial_spray_count,
            "initial_spray_count",
            np.dtype("<i4"),
            grid_shape,
        )
        if np.any(prey > 0.5):
            raise ValueError("initial_prey exceeds the Problem-1 source clip")
        if np.any(concentration > 1.0):
            raise ValueError("initial_concentration exceeds its ecological cap")
        if np.any(duration > 15.0) or np.any(duration != np.floor(duration)):
            raise ValueError("initial_duration is outside its canonical domain")

        normalized_rng_state = raw_rng_state
        digest = _scenario_digest(
            partition=partition,
            scenario_id=scenario_id,
            scale_id=self.scale_id,
            grid_shape=grid_shape,
            initial_prey=prey,
            initial_predator=predator,
            initial_concentration=concentration,
            initial_duration=duration,
            initial_spray_count=spray_count,
            initial_wind=initial_wind,
            rng_state=normalized_rng_state,
            config_hash=config_hash,
            source_commit=self.source_commit,
            implementation_version=self.implementation_version,
        )
        if digest != scenario_sha256:
            raise ValueError("scenario_sha256 does not match canonical scenario state")

        object.__setattr__(self, "partition", partition)
        object.__setattr__(self, "scenario_id", scenario_id)
        object.__setattr__(self, "grid_shape", grid_shape)
        object.__setattr__(self, "initial_prey", prey)
        object.__setattr__(self, "initial_predator", predator)
        object.__setattr__(self, "initial_concentration", concentration)
        object.__setattr__(self, "initial_duration", duration)
        object.__setattr__(self, "initial_spray_count", spray_count)
        object.__setattr__(self, "initial_wind", initial_wind)
        object.__setattr__(self, "rng_state", normalized_rng_state)
        for array in (prey, predator, concentration, duration, spray_count):
            array.setflags(write=False)

    @property
    def initial_wind_state(self) -> WindState:
        return self.initial_wind

    @property
    def initial_effect_state(self) -> dict[str, object]:
        return {
            "shape": self.grid_shape,
            "concentration": self.initial_concentration.copy(),
            "duration": self.initial_duration.copy(),
            "spray_count": self.initial_spray_count.copy(),
        }

    def state_dict(self) -> dict[str, object]:
        """Return a detached snapshot suitable for exact restoration."""

        return {
            "partition": self.partition,
            "scenario_id": self.scenario_id,
            "scale_id": self.scale_id,
            "grid_shape": self.grid_shape,
            "initial_prey": self.initial_prey.copy(),
            "initial_predator": self.initial_predator.copy(),
            "initial_effect": self.initial_effect_state,
            "initial_wind": _wind_payload(self.initial_wind),
            "rng_state": copy.deepcopy(self.rng_state),
            "config_hash": self.config_hash,
            "source_commit": self.source_commit,
            "implementation_version": self.implementation_version,
            "scenario_sha256": self.scenario_sha256,
        }

    @classmethod
    def from_state_dict(cls, state: Mapping[str, object]) -> "DynamicPestScenario":
        if not isinstance(state, Mapping) or set(state) != _SCENARIO_STATE_KEYS:
            raise ValueError("scenario state keys are incomplete or non-canonical")
        effect = state["initial_effect"]
        if not isinstance(effect, Mapping) or set(effect) != {
            "shape",
            "concentration",
            "duration",
            "spray_count",
        }:
            raise ValueError("initial_effect state is incomplete")
        shape = state["grid_shape"]
        if effect["shape"] != shape:
            raise ValueError("initial_effect shape does not match grid_shape")
        return cls(
            partition=state["partition"],  # type: ignore[arg-type]
            scenario_id=state["scenario_id"],  # type: ignore[arg-type]
            scale_id=state["scale_id"],  # type: ignore[arg-type]
            grid_shape=shape,  # type: ignore[arg-type]
            initial_prey=state["initial_prey"],  # type: ignore[arg-type]
            initial_predator=state["initial_predator"],  # type: ignore[arg-type]
            initial_concentration=effect["concentration"],  # type: ignore[arg-type]
            initial_duration=effect["duration"],  # type: ignore[arg-type]
            initial_spray_count=effect["spray_count"],  # type: ignore[arg-type]
            initial_wind=_wind_from_payload(state["initial_wind"]),
            rng_state=copy.deepcopy(state["rng_state"]),  # type: ignore[arg-type]
            config_hash=state["config_hash"],  # type: ignore[arg-type]
            source_commit=state["source_commit"],  # type: ignore[arg-type]
            implementation_version=state["implementation_version"],  # type: ignore[arg-type]
            scenario_sha256=state["scenario_sha256"],  # type: ignore[arg-type]
        )


def _gaussian_sources(
    rng: np.random.Generator,
    grid_shape: tuple[int, int],
    sigma: float,
    peak: float,
    clip_upper: float | None,
) -> np.ndarray:
    height, width = grid_shape
    row_grid, col_grid = np.indices(grid_shape, dtype=np.float64)
    source_count = int(rng.integers(1, 3))
    row_low, row_high = height // 4, 3 * height // 4
    col_low, col_high = width // 4, 3 * width // 4
    rows = rng.integers(row_low, row_high, size=source_count)
    cols = rng.integers(col_low, col_high, size=source_count)
    field = np.zeros(grid_shape, dtype=np.float64)
    for row, col in zip(rows, cols):
        squared_distance = (row_grid - int(row)) ** 2 + (col_grid - int(col)) ** 2
        field += peak * np.exp(-squared_distance / (2.0 * sigma * sigma))
    if clip_upper is not None:
        field = np.clip(field, 0.0, clip_upper)
    else:
        field = np.maximum(field, 0.0)
    return np.ascontiguousarray(field, dtype=np.dtype("<f8"))


def generate_dynamic_scenario(
    partition: str,
    scenario_id: int,
    scale_id: str,
    grid_shape: tuple[int, int],
    config: DynamicEcologyConfig,
) -> DynamicPestScenario:
    """Generate one deterministic, independently seeded ecology scenario."""

    partition, scenario_id = _validate_partition(partition, scenario_id)
    grid_shape = _validate_shape(grid_shape)
    if not isinstance(scale_id, str) or not scale_id.strip():
        raise ValueError("scale_id must be non-empty text")
    if not isinstance(config, DynamicEcologyConfig):
        raise TypeError("config must be a DynamicEcologyConfig")

    seed_material = _canonical_json_bytes(
        {
            "partition": partition,
            "scenario_id": scenario_id,
            "scale_id": scale_id,
            "grid_shape": list(grid_shape),
            "config_hash": config.contract_sha256,
            "implementation_version": _SCENARIO_IMPLEMENTATION_VERSION,
        }
    )
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    initial_prey = _gaussian_sources(rng, grid_shape, min(grid_shape) / 5.0, 0.10, 0.5)
    initial_predator = _gaussian_sources(rng, grid_shape, 6.0, 0.30, None)
    effect = PesticideEffectField.empty(grid_shape, config)
    wind = DynamicWind.initialize(rng, config)
    rng_state = copy.deepcopy(rng.bit_generator.state)
    scenario_sha256 = _scenario_digest(
        partition=partition,
        scenario_id=scenario_id,
        scale_id=scale_id,
        grid_shape=grid_shape,
        initial_prey=initial_prey,
        initial_predator=initial_predator,
        initial_concentration=effect.concentration,
        initial_duration=effect.duration,
        initial_spray_count=effect.spray_count,
        initial_wind=wind.state,
        rng_state=rng_state,
        config_hash=config.contract_sha256,
        source_commit=_PROBLEM1_SOURCE_COMMIT,
        implementation_version=_SCENARIO_IMPLEMENTATION_VERSION,
    )
    return DynamicPestScenario(
        partition=partition,
        scenario_id=scenario_id,
        scale_id=scale_id,
        grid_shape=grid_shape,
        initial_prey=initial_prey,
        initial_predator=initial_predator,
        initial_concentration=effect.concentration,
        initial_duration=effect.duration,
        initial_spray_count=effect.spray_count,
        initial_wind=wind.state,
        rng_state=rng_state,
        config_hash=config.contract_sha256,
        source_commit=_PROBLEM1_SOURCE_COMMIT,
        implementation_version=_SCENARIO_IMPLEMENTATION_VERSION,
        scenario_sha256=scenario_sha256,
    )


__all__ = [
    "DynamicPestScenario",
    "DynamicWind",
    "WindState",
    "generate_dynamic_scenario",
]
