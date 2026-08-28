from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from problem2.ecology import dynamics
from problem2.ecology.config import DynamicEcologyConfig
from problem2.ecology.dynamics import reflected_laplacian, upwind_advection


ROOT = Path(__file__).parents[2]
CONFIG = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")


def test_reflected_laplacian_matches_hand_computed_corner_and_center() -> None:
    field = np.array(
        [[1.0, 2.0, 4.0], [3.0, 5.0, 8.0], [6.0, 9.0, 10.0]]
    )
    observed = reflected_laplacian(field, dx=1.0)
    assert observed[0, 0] == pytest.approx(6.0)
    assert observed[1, 1] == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("wind", "expected"),
    [
        ((2.0, 0.0), np.array([[2.0, -2.0, -4.0]])),
        ((-2.0, 0.0), np.array([[2.0, 4.0, -4.0]])),
    ],
)
def test_upwind_advection_uses_wind_sign(
    wind: tuple[float, float], expected: np.ndarray
) -> None:
    field = np.array([[1.0, 2.0, 4.0]])
    assert np.allclose(upwind_advection(field, wind, 1.0), expected)


@pytest.mark.parametrize(
    ("field", "wind"),
    [
        (np.ones((1, 3)), (0.0, -1.0)),
        (np.ones((2, 1)), (-1.0, 0.0)),
    ],
)
def test_upwind_advection_handles_negative_wind_on_degenerate_axis(
    field: np.ndarray, wind: tuple[float, float]
) -> None:
    observed = upwind_advection(field, wind, dx=1.0)
    assert np.array_equal(observed, np.zeros_like(field))


def _independent_reference_advance(
    prey: np.ndarray,
    predator: np.ndarray,
    wind: tuple[float, float],
    config: DynamicEcologyConfig,
    steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Hand-written reference equations; production dynamics are not called."""

    x = prey.astype(float, copy=True)
    y = predator.astype(float, copy=True)
    dt = config.integration_interval / config.substeps
    dx = np.pi / max(x.shape)
    wx, wy = wind

    for _ in range(steps):
        padded_x = np.pad(x, 1, mode="reflect")
        padded_y = np.pad(y, 1, mode="reflect")
        lap_x = (
            padded_x[2:, 1:-1]
            + padded_x[:-2, 1:-1]
            + padded_x[1:-1, 2:]
            + padded_x[1:-1, :-2]
            - 4.0 * x
        ) / (dx * dx)
        lap_y = (
            padded_y[2:, 1:-1]
            + padded_y[:-2, 1:-1]
            + padded_y[1:-1, 2:]
            + padded_y[1:-1, :-2]
            - 4.0 * y
        ) / (dx * dx)

        if wx >= 0.0:
            grad_x = (padded_x[1:-1, 1:-1] - padded_x[1:-1, :-2]) / dx
            grad_y_for_x = (padded_y[1:-1, 1:-1] - padded_y[1:-1, :-2]) / dx
        else:
            grad_x = (padded_x[1:-1, 2:] - padded_x[1:-1, 1:-1]) / dx
            grad_y_for_x = (padded_y[1:-1, 2:] - padded_y[1:-1, 1:-1]) / dx
            grad_x[:, -1] = (x[:, -2] - x[:, -1]) / dx
            grad_y_for_x[:, -1] = (y[:, -2] - y[:, -1]) / dx
        if wy >= 0.0:
            grad_y = (padded_x[1:-1, 1:-1] - padded_x[:-2, 1:-1]) / dx
            grad_predator_y = (padded_y[1:-1, 1:-1] - padded_y[:-2, 1:-1]) / dx
        else:
            grad_y = (padded_x[2:, 1:-1] - padded_x[1:-1, 1:-1]) / dx
            grad_predator_y = (padded_y[2:, 1:-1] - padded_y[1:-1, 1:-1]) / dx
            grad_y[-1, :] = (x[-2, :] - x[-1, :]) / dx
            grad_predator_y[-1, :] = (y[-2, :] - y[-1, :]) / dx

        advection_x = -(wx * grad_x + wy * grad_y)
        advection_y = -(wx * grad_y_for_x + wy * grad_predator_y)

        reaction_x = x * (1.0 - config.beta * x) - (
            config.m * x * y / (x + 1.0 + 1e-10)
        )
        safe_x = np.maximum(x, 1e-8)
        reaction_y = config.s * y * (1.0 - y / safe_x)
        reaction_y = np.where(
            x < config.prey_extinction_threshold,
            -config.predator_low_prey_decay * y,
            reaction_y,
        )
        reaction_x = np.clip(reaction_x, *config.reaction_clip_bounds)
        reaction_y = np.clip(reaction_y, *config.reaction_clip_bounds)

        x, y = (
            np.clip(
                x
                + dt
                * (
                    config.d1 * lap_x
                    + reaction_x
                    + config.prey_advection_multiplier * advection_x
                ),
                0.0,
                1.0 / config.beta,
            ),
            np.clip(
                y
                + dt
                * (
                    config.d2 * lap_y
                    + reaction_y
                    + config.predator_advection_multiplier * advection_y
                ),
                0.0,
                2.0 / config.beta,
            ),
        )
    return x, y


def test_reaction_terms_use_holling_tanner_and_low_prey_fallback() -> None:
    prey = np.array([[0.0, 0.2], [1.0 / CONFIG.beta, 0.4]])
    predator = np.array([[1.0, 0.5], [2.0 / CONFIG.beta, 0.2]])
    expected_prey = prey * (1.0 - CONFIG.beta * prey) - (
        CONFIG.m * prey * predator / (prey + 1.0 + 1e-10)
    )
    safe_prey = np.maximum(prey, 1e-8)
    expected_predator = CONFIG.s * predator * (1.0 - predator / safe_prey)
    expected_predator[0, 0] = -0.1 * predator[0, 0]
    expected_prey = np.clip(expected_prey, -0.5, 0.5)
    expected_predator = np.clip(expected_predator, -0.5, 0.5)

    observed_prey, observed_predator = dynamics.reaction_terms(
        prey, predator, CONFIG
    )
    assert np.allclose(observed_prey, expected_prey, rtol=0.0, atol=1e-12)
    assert np.allclose(observed_predator, expected_predator, rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("steps", [1, CONFIG.substeps])
def test_holling_tanner_matches_independent_reference(
    steps: int,
) -> None:
    prey = np.array(
        [[0.0, 0.05, 0.2], [0.6, 0.3, 1.0 / CONFIG.beta]], dtype=float
    )
    predator = np.array(
        [[1.0, 0.4, 0.1], [0.2, 2.0 / CONFIG.beta, 0.8]], dtype=float
    )
    wind = (-0.31, 0.17)
    expected = _independent_reference_advance(prey, predator, wind, CONFIG, steps)

    if steps == 1:
        observed = dynamics.holling_tanner_substep(prey, predator, wind, CONFIG)
    else:
        observed = dynamics.advance_holling_tanner(prey, predator, wind, CONFIG)
    assert np.allclose(observed[0], expected[0], rtol=0.0, atol=1e-12)
    assert np.allclose(observed[1], expected[1], rtol=0.0, atol=1e-12)


def test_advance_preserves_inputs_and_enforces_output_clips() -> None:
    prey = np.array([[0.0, 1.0 / CONFIG.beta], [0.4, 0.2]])
    predator = np.array([[2.0 / CONFIG.beta, 0.0], [0.1, 0.8]])
    prey_before = prey.tobytes()
    predator_before = predator.tobytes()

    next_prey, next_predator = dynamics.advance_holling_tanner(
        prey, predator, (0.2, -0.2), CONFIG
    )

    assert prey.tobytes() == prey_before
    assert predator.tobytes() == predator_before
    assert np.all((0.0 <= next_prey) & (next_prey <= 1.0 / CONFIG.beta))
    assert np.all((0.0 <= next_predator) & (next_predator <= 2.0 / CONFIG.beta))


def test_one_substep_exactly_clips_raw_updates_above_both_upper_bounds() -> None:
    prey = np.full((2, 2), 2.0)
    predator = np.full((2, 2), 2.0)
    dt = CONFIG.integration_interval / CONFIG.substeps

    # Uniform fields have zero diffusion and advection, so these raw values
    # are independently derived from the clipped reaction equations.
    raw_prey_reaction = np.clip(
        2.0 * (1.0 - CONFIG.beta * 2.0)
        - CONFIG.m * 2.0 * 2.0 / (2.0 + 1.0 + 1e-10),
        -0.5,
        0.5,
    )
    raw_predator_reaction = np.clip(
        CONFIG.s * 2.0 * (1.0 - 2.0 / 2.0), -0.5, 0.5
    )
    raw_prey = 2.0 + dt * raw_prey_reaction
    raw_predator = 2.0 + dt * raw_predator_reaction
    assert raw_prey > 1.0 / CONFIG.beta
    assert raw_predator > 2.0 / CONFIG.beta

    observed_prey, observed_predator = dynamics.holling_tanner_substep(
        prey, predator, (0.0, 0.0), CONFIG
    )
    assert np.array_equal(observed_prey, np.full((2, 2), 1.0 / CONFIG.beta))
    assert np.array_equal(observed_predator, np.full((2, 2), 2.0 / CONFIG.beta))


def test_density_validation_rejects_shape_nonfinite_and_negative_values() -> None:
    valid = np.ones((2, 2), dtype=float)
    with pytest.raises(ValueError):
        dynamics.validate_density_pair(valid, np.ones((2, 3)))
    with pytest.raises(ValueError):
        dynamics.validate_density_pair(np.array([[np.nan, 0.0]]), valid[:1])
    with pytest.raises(ValueError):
        dynamics.validate_density_pair(np.array([[-1.0]]), np.array([[0.0]]))
    with pytest.raises(ValueError):
        dynamics.validate_density_pair(np.array([[np.inf]]), np.array([[0.0]]))


def test_reflected_laplacian_rejects_one_cell_axis_and_invalid_spacing() -> None:
    with pytest.raises(ValueError):
        reflected_laplacian(np.ones((1, 3)), 1.0)
    with pytest.raises(ValueError):
        reflected_laplacian(np.ones((2, 2)), 0.0)
