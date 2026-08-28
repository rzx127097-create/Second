"""Pure numerical operators for the Problem-2 dynamic ecology."""

from __future__ import annotations

import math
from typing import Final

import numpy as np

from .config import DynamicEcologyConfig


_MIN_REFLECTED_AXIS: Final[int] = 2


def _validate_field(field: np.ndarray, name: str = "field") -> np.ndarray:
    if not isinstance(field, np.ndarray):
        raise ValueError(f"{name} must be a NumPy array")
    if field.ndim != 2 or field.size == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional array")
    if not np.issubdtype(field.dtype, np.number):
        raise ValueError(f"{name} must have a numeric dtype")
    if not np.all(np.isfinite(field)):
        raise ValueError(f"{name} must contain only finite values")
    return field


def _validate_reflected_field(field: np.ndarray) -> np.ndarray:
    field = _validate_field(field)
    if min(field.shape) < _MIN_REFLECTED_AXIS:
        raise ValueError("reflected padding requires at least two cells per axis")
    return field


def _validate_dx(dx: float) -> float:
    if isinstance(dx, bool):
        raise ValueError("dx must be positive and finite")
    try:
        value = float(dx)
    except (TypeError, ValueError) as exc:
        raise ValueError("dx must be positive and finite") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("dx must be positive and finite")
    return value


def _validate_wind(wind: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(wind, tuple) or len(wind) != 2:
        raise ValueError("wind must contain exactly two finite values")
    try:
        wx, wy = float(wind[0]), float(wind[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("wind must contain exactly two finite values") from exc
    if not math.isfinite(wx) or not math.isfinite(wy):
        raise ValueError("wind must contain exactly two finite values")
    return wx, wy


def validate_density_pair(
    prey: np.ndarray, predator: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Validate and copy a finite, nonnegative, shape-matched density pair."""

    prey = _validate_field(prey, "prey")
    predator = _validate_field(predator, "predator")
    if prey.shape != predator.shape:
        raise ValueError("prey and predator must have identical shapes")
    if np.any(prey < 0.0) or np.any(predator < 0.0):
        raise ValueError("prey and predator densities must be nonnegative")
    return prey.astype(float, copy=True), predator.astype(float, copy=True)


def reflected_laplacian(field: np.ndarray, dx: float) -> np.ndarray:
    """Return the five-point Laplacian with reflected boundary padding."""

    field = _validate_reflected_field(field)
    dx = _validate_dx(dx)
    padded = np.pad(field, 1, mode="reflect")
    return (
        padded[2:, 1:-1]
        + padded[:-2, 1:-1]
        + padded[1:-1, 2:]
        + padded[1:-1, :-2]
        - 4.0 * field
    ) / (dx * dx)


def upwind_advection(
    field: np.ndarray, wind: tuple[float, float], dx: float
) -> np.ndarray:
    """Return signed first-order upwind advection with reflected boundaries."""

    field = _validate_field(field)
    wx, wy = _validate_wind(wind)
    dx = _validate_dx(dx)
    pad_modes = tuple("reflect" if size >= 2 else "edge" for size in field.shape)
    padded = np.pad(
        np.pad(field, ((1, 1), (0, 0)), mode=pad_modes[0]),
        ((0, 0), (1, 1)),
        mode=pad_modes[1],
    )

    if wx >= 0.0:
        du_dx = (padded[1:-1, 1:-1] - padded[1:-1, :-2]) / dx
    else:
        du_dx = (padded[1:-1, 2:] - padded[1:-1, 1:-1]) / dx
        du_dx[:, -1] = (field[:, -2] - field[:, -1]) / dx

    if wy >= 0.0:
        du_dy = (padded[1:-1, 1:-1] - padded[:-2, 1:-1]) / dx
    else:
        du_dy = (padded[2:, 1:-1] - padded[1:-1, 1:-1]) / dx
        du_dy[-1, :] = (field[-2, :] - field[-1, :]) / dx

    return -(wx * du_dx + wy * du_dy)


def reaction_terms(
    prey: np.ndarray, predator: np.ndarray, config: DynamicEcologyConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Return clipped Holling-Tanner prey and predator reaction terms."""

    prey, predator = validate_density_pair(prey, predator)
    prey_reaction = prey * (1.0 - config.beta * prey) - (
        config.m * prey * predator / (prey + 1.0 + 1e-10)
    )
    safe_prey = np.maximum(prey, 1e-8)
    predator_reaction = config.s * predator * (1.0 - predator / safe_prey)
    predator_reaction = np.where(
        prey < config.prey_extinction_threshold,
        -config.predator_low_prey_decay * predator,
        predator_reaction,
    )
    lower, upper = config.reaction_clip_bounds
    return (
        np.clip(prey_reaction, lower, upper),
        np.clip(predator_reaction, lower, upper),
    )


def holling_tanner_substep(
    prey: np.ndarray,
    predator: np.ndarray,
    wind: tuple[float, float],
    config: DynamicEcologyConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance both density fields by one configured ecological substep."""

    prey, predator = validate_density_pair(prey, predator)
    dx = np.pi / max(prey.shape)
    dt = config.integration_interval / config.substeps
    prey_laplacian = reflected_laplacian(prey, dx)
    predator_laplacian = reflected_laplacian(predator, dx)
    prey_reaction, predator_reaction = reaction_terms(prey, predator, config)
    advection = upwind_advection(prey, wind, dx)
    predator_advection = upwind_advection(predator, wind, dx)

    next_prey = prey + dt * (
        config.d1 * prey_laplacian
        + prey_reaction
        + config.prey_advection_multiplier * advection
    )
    next_predator = predator + dt * (
        config.d2 * predator_laplacian
        + predator_reaction
        + config.predator_advection_multiplier * predator_advection
    )
    return (
        np.clip(next_prey, 0.0, 1.0 / config.beta),
        np.clip(next_predator, 0.0, 2.0 / config.beta),
    )


def advance_holling_tanner(
    prey: np.ndarray,
    predator: np.ndarray,
    wind: tuple[float, float],
    config: DynamicEcologyConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance exactly ``config.substeps`` ecological substeps."""

    prey, predator = validate_density_pair(prey, predator)
    for _ in range(config.substeps):
        prey, predator = holling_tanner_substep(prey, predator, wind, config)
    return prey, predator


__all__ = [
    "advance_holling_tanner",
    "holling_tanner_substep",
    "reaction_terms",
    "reflected_laplacian",
    "upwind_advection",
    "validate_density_pair",
]
