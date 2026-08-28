"""Ordered, snapshot-able dynamic ecology for Problem 2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Any

import numpy as np

from . import dynamics
from .config import DYNAMIC_ECOLOGY_VERSION, DynamicEcologyConfig
from .pesticide import AcceptedSpray, PesticideEffectField
from .scenario import DynamicPestScenario, DynamicWind, WindState


_STATE_KEYS = frozenset(
    {
        "scenario_sha256",
        "config_hash",
        "implementation_version",
        "shape",
        "reference_spray_l",
        "prey",
        "predator",
        "pesticide",
        "wind",
        "rng_state",
        "step_count",
        "deposited_effect",
        "state_sha256",
    }
)
_CANONICAL_SUBSTEPS = 3


@dataclass(frozen=True, slots=True)
class EcologyTransition:
    prey_before_total: float
    prey_after_total: float
    predator_before_total: float
    predator_after_total: float
    deposited_effect: float
    wind_vector: tuple[float, float]
    step_count: int


def _detached(value: Any) -> Any:
    """Copy frozen mappings and NumPy values without copying the scenario."""

    if isinstance(value, Mapping):
        return {key: _detached(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_detached(item) for item in value)
    if isinstance(value, list):
        return [_detached(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _copy_rng_state(value: Mapping[str, object]) -> dict[str, object]:
    copied = _detached(value)
    if not isinstance(copied, dict):
        raise ValueError("rng_state must be a mapping")
    return copied


def _generator_from_state(value: Mapping[str, object]) -> np.random.Generator:
    if not isinstance(value, Mapping) or "bit_generator" not in value:
        raise ValueError("rng_state is incomplete")
    name = value["bit_generator"]
    if not isinstance(name, str) or not name:
        raise ValueError("rng_state bit-generator name is invalid")
    generator_type = getattr(np.random, name, None)
    if not isinstance(generator_type, type) or not issubclass(
        generator_type, np.random.BitGenerator
    ):
        raise ValueError("rng_state bit-generator name is unsupported")
    try:
        bit_generator = generator_type()
        bit_generator.state = _detached(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rng_state state is invalid") from exc
    return np.random.Generator(bit_generator)


def _finite_positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be finite and positive")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _validate_population(
    value: object,
    name: str,
    shape: tuple[int, int],
    dtype: np.dtype[Any],
    upper: float,
) -> np.ndarray:
    if not isinstance(value, np.ndarray) or value.ndim != 2 or value.shape != shape:
        raise ValueError(f"{name} has the wrong shape")
    if value.dtype != dtype:
        raise ValueError(f"{name} has the wrong dtype")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} must be finite")
    if np.any(value < 0.0) or np.any(value > upper):
        raise ValueError(f"{name} is outside its ecological domain")
    return value.copy()


def _digest_payload(payload: Mapping[str, object]) -> str:
    metadata = {
        key: _jsonable(value)
        for key, value in payload.items()
        if key not in {"prey", "predator", "pesticide", "state_sha256"}
    }
    metadata["pesticide_shape"] = _jsonable(payload["pesticide"]["shape"])  # type: ignore[index]
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            metadata, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )
    for array in (
        payload["prey"],
        payload["predator"],
        payload["pesticide"]["concentration"],  # type: ignore[index]
        payload["pesticide"]["duration"],  # type: ignore[index]
        payload["pesticide"]["spray_count"],  # type: ignore[index]
    ):
        if not isinstance(array, np.ndarray):
            raise ValueError("state arrays are invalid")
        digest.update(np.ascontiguousarray(array).tobytes(order="C"))
    return digest.hexdigest()


class DynamicEcologySystem:
    """Own the complete ecology state coupled to one physical decision step."""

    def __init__(
        self,
        scenario: DynamicPestScenario,
        config: DynamicEcologyConfig,
        reference_spray_l: float,
    ) -> None:
        if not isinstance(scenario, DynamicPestScenario):
            raise TypeError("scenario must be a DynamicPestScenario")
        if not isinstance(config, DynamicEcologyConfig):
            raise TypeError("config must be a DynamicEcologyConfig")
        if config.substeps != _CANONICAL_SUBSTEPS:
            raise ValueError("substeps must remain exactly 3")
        if scenario.config_hash != config.contract_sha256:
            raise ValueError("scenario/config_hash mismatch")
        self.scenario = scenario
        self.config = config
        self._reference_spray_l = _finite_positive(
            reference_spray_l, "reference_spray_l"
        )
        self._prey = scenario.initial_prey.copy()
        self._predator = scenario.initial_predator.copy()
        self._pesticide = PesticideEffectField.from_state_dict(
            scenario.initial_effect_state, config
        )
        initial_wind = {
            "state": {
                "direction": scenario.initial_wind.direction,
                "strength": scenario.initial_wind.strength,
                "step_count": scenario.initial_wind.step_count,
            },
            "bit_generator": scenario.rng_state["bit_generator"],
            "rng_state": _copy_rng_state(scenario.rng_state),
        }
        self._wind = DynamicWind.from_state_dict(initial_wind, config)
        self._rng = self._wind.rng
        self._step_count = 0
        self._deposited_effect = 0.0

    @classmethod
    def from_scenario(
        cls,
        scenario: DynamicPestScenario,
        config: DynamicEcologyConfig,
        reference_spray_l: float,
    ) -> "DynamicEcologySystem":
        return cls(scenario, config, reference_spray_l)

    @property
    def shape(self) -> tuple[int, int]:
        return self._prey.shape

    @property
    def prey(self) -> np.ndarray:
        return self._prey.copy()

    @property
    def predator(self) -> np.ndarray:
        return self._predator.copy()

    @property
    def concentration(self) -> np.ndarray:
        return self._pesticide.concentration.copy()

    @property
    def duration(self) -> np.ndarray:
        return self._pesticide.duration.copy()

    @property
    def spray_count(self) -> np.ndarray:
        return self._pesticide.spray_count.copy()

    @property
    def pesticide(self) -> PesticideEffectField:
        return PesticideEffectField.from_state_dict(
            self._pesticide.state_dict(), self.config
        )

    @property
    def wind_state(self) -> WindState:
        return self._wind.state

    @property
    def wind_vector(self) -> tuple[float, float]:
        return self._wind.state.vector

    @property
    def rng_state(self) -> dict[str, object]:
        return _copy_rng_state(self._rng.bit_generator.state)

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def deposited_effect(self) -> float:
        return self._deposited_effect

    def step(self, accepted_sprays: Sequence[AcceptedSpray]) -> EcologyTransition:
        if isinstance(accepted_sprays, (str, bytes)) or not isinstance(
            accepted_sprays, Sequence
        ):
            raise TypeError("accepted_sprays must be a sequence")
        for spray in accepted_sprays:
            if not isinstance(spray, AcceptedSpray):
                raise TypeError("accepted_sprays must contain AcceptedSpray values")
            if (
                isinstance(spray.delta_l, bool)
                or not isinstance(spray.delta_l, Real)
                or not math.isfinite(float(spray.delta_l))
                or float(spray.delta_l) <= 0.0
            ):
                raise ValueError("spray delta_l must be finite and positive")

        prey_before_total = float(np.sum(self._prey))
        predator_before_total = float(np.sum(self._predator))
        deposited_this_step = 0.0

        for spray in accepted_sprays:
            self._pesticide.deposit(spray, self._reference_spray_l)
            deposited_this_step += (
                self.config.effect_amount
                * float(spray.delta_l)
                / self._reference_spray_l
            )
        self._deposited_effect += deposited_this_step

        wind_state = self._wind.update()
        wind_vector = wind_state.vector
        self._prey, self._predator = self._pesticide.apply_mortality(
            self._prey, self._predator
        )
        for _ in range(_CANONICAL_SUBSTEPS):
            self._prey, self._predator = dynamics.holling_tanner_substep(
                self._prey, self._predator, wind_vector, self.config
            )
        self._pesticide.decay()
        self._step_count += 1

        return EcologyTransition(
            prey_before_total=prey_before_total,
            prey_after_total=float(np.sum(self._prey)),
            predator_before_total=predator_before_total,
            predator_after_total=float(np.sum(self._predator)),
            deposited_effect=self._deposited_effect,
            wind_vector=wind_vector,
            step_count=self._step_count,
        )

    @staticmethod
    def _stats(field: np.ndarray, upper: float) -> tuple[float, ...]:
        return (
            float(np.sum(field) / (field.size * upper)),
            float(np.mean(field)),
            float(np.max(field)),
            float(np.std(field)),
            float(np.mean(field > 0.2)),
            float(np.mean(field > 0.0)),
        )

    def global_summary(self) -> tuple[float, ...]:
        return self._stats(self._prey, 1.0 / self.config.beta) + (
            float(np.mean(self._pesticide.concentration)),
            float(np.max(self._pesticide.concentration)),
        ) + self._stats(self._predator, 2.0 / self.config.beta) + (
            math.cos(self._wind.state.direction),
            math.sin(self._wind.state.direction),
            self._wind.state.strength / self.config.wind_strength_range[1],
        )

    def local_context(self, row: int, col: int) -> tuple[float, ...]:
        if (
            isinstance(row, bool)
            or not isinstance(row, int)
            or isinstance(col, bool)
            or not isinstance(col, int)
            or not (0 <= row < self.shape[0] and 0 <= col < self.shape[1])
        ):
            raise ValueError("local context cell is out of bounds")
        padded = np.pad(self._prey, 1, mode="reflect")
        gradient_x = (padded[row + 1, col + 2] - padded[row + 1, col]) / 2.0
        gradient_y = (padded[row + 2, col + 1] - padded[row, col + 1]) / 2.0
        neighborhood = padded[row : row + 3, col : col + 3]
        return (
            float(self._prey[row, col]),
            float(self._predator[row, col]),
            float(self._pesticide.concentration[row, col]),
            float(gradient_x),
            float(gradient_y),
            float(np.mean(neighborhood)),
        )

    def _state_payload(self) -> dict[str, object]:
        return {
            "scenario_sha256": self.scenario.scenario_sha256,
            "config_hash": self.config.contract_sha256,
            "implementation_version": DYNAMIC_ECOLOGY_VERSION,
            "shape": self.shape,
            "reference_spray_l": self._reference_spray_l,
            "prey": self._prey.copy(),
            "predator": self._predator.copy(),
            "pesticide": self._pesticide.state_dict(),
            "wind": self._wind.state_dict(),
            "rng_state": self.rng_state,
            "step_count": self._step_count,
            "deposited_effect": self._deposited_effect,
        }

    def state_dict(self) -> dict[str, object]:
        payload = self._state_payload()
        result = {key: _detached(value) for key, value in payload.items()}
        result["state_sha256"] = _digest_payload(result)
        return result

    def load_state_dict(
        self,
        state: Mapping[str, object],
        *,
        config: DynamicEcologyConfig | None = None,
    ) -> None:
        if not isinstance(state, Mapping) or set(state) != _STATE_KEYS:
            raise ValueError("ecology state keys are incomplete or non-canonical")
        active_config = self.config if config is None else config
        if not isinstance(active_config, DynamicEcologyConfig):
            raise TypeError("config must be a DynamicEcologyConfig")
        if active_config.substeps != _CANONICAL_SUBSTEPS:
            raise ValueError("substeps must remain exactly 3")
        if active_config.contract_sha256 != self.scenario.config_hash:
            raise ValueError("scenario/config_hash mismatch")
        if state["scenario_sha256"] != self.scenario.scenario_sha256:
            raise ValueError("scenario_sha256 drifted")
        if state["config_hash"] != active_config.contract_sha256:
            raise ValueError("config_hash drifted")
        if state["implementation_version"] != DYNAMIC_ECOLOGY_VERSION:
            raise ValueError("implementation_version drifted")
        shape = state["shape"]
        if shape != self.shape:
            raise ValueError("state shape drifted")
        reference = _finite_positive(state["reference_spray_l"], "reference_spray_l")
        if reference != self._reference_spray_l:
            raise ValueError("reference_spray_l drifted")
        prey = _validate_population(
            state["prey"], "prey", self.shape, np.dtype("<f8"), 1.0 / active_config.beta
        )
        predator = _validate_population(
            state["predator"],
            "predator",
            self.shape,
            np.dtype("<f8"),
            2.0 / active_config.beta,
        )
        pesticide_state = state["pesticide"]
        if not isinstance(pesticide_state, Mapping):
            raise ValueError("pesticide state is invalid")
        pesticide_shape = pesticide_state.get("shape")
        if not isinstance(pesticide_shape, tuple) or pesticide_shape != self.shape:
            raise ValueError("pesticide shape drifted")
        pesticide = PesticideEffectField.from_state_dict(pesticide_state, active_config)
        wind_state = state["wind"]
        if not isinstance(wind_state, Mapping):
            raise ValueError("wind state is invalid")
        if wind_state.get("bit_generator") != type(self._rng.bit_generator).__name__:
            raise ValueError("bit-generator is unsupported")
        wind = DynamicWind.from_state_dict(wind_state, active_config)
        rng_state = state["rng_state"]
        if not isinstance(rng_state, Mapping):
            raise ValueError("rng_state is invalid")
        rng = _generator_from_state(rng_state)
        if _jsonable(rng.bit_generator.state) != _jsonable(wind.rng.bit_generator.state):
            raise ValueError("rng_state does not match wind state")
        step_count = state["step_count"]
        if isinstance(step_count, bool) or not isinstance(step_count, int) or step_count < 0:
            raise ValueError("step_count is invalid")
        deposited_effect = state["deposited_effect"]
        if (
            isinstance(deposited_effect, bool)
            or not isinstance(deposited_effect, Real)
            or not math.isfinite(float(deposited_effect))
            or float(deposited_effect) < 0.0
        ):
            raise ValueError("deposited_effect is invalid")
        candidate = {
            "scenario_sha256": state["scenario_sha256"],
            "config_hash": state["config_hash"],
            "implementation_version": state["implementation_version"],
            "shape": shape,
            "reference_spray_l": reference,
            "prey": prey,
            "predator": predator,
            "pesticide": pesticide.state_dict(),
            "wind": wind.state_dict(),
            "rng_state": _copy_rng_state(rng_state),
            "step_count": step_count,
            "deposited_effect": float(deposited_effect),
        }
        if state["state_sha256"] != _digest_payload(candidate):
            raise ValueError("state_sha256 does not match canonical state")
        self.config = active_config
        self._prey = prey
        self._predator = predator
        self._pesticide = pesticide
        self._wind = wind
        self._rng = wind.rng
        self._step_count = step_count
        self._deposited_effect = float(deposited_effect)


__all__ = ["DynamicEcologySystem", "EcologyTransition"]
