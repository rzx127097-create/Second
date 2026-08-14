from __future__ import annotations

import numpy as np
import pytest

from problem2.field.pest_dynamics import PestDynamics
from problem2.field.pesticide_field import PesticideField
from problem2.field.wind_field import WindField


def test_wind_advection_moves_mass_in_the_declared_direction_without_negative_values() -> None:
    field = np.zeros((3, 5), dtype=float)
    field[1, 1] = 1.0

    moved = WindField(vx_m_s=1.0, vy_m_s=0.0).advect(
        field, dt_s=0.5, cell_size_m=(1.0, 1.0)
    )

    assert moved[1, 1] == pytest.approx(0.5)
    assert moved[1, 2] == pytest.approx(0.5)
    assert np.all(moved >= 0.0)


def test_reaction_diffusion_advection_preserves_bounds_and_responds_to_exposure() -> None:
    density = np.zeros((3, 3), dtype=float)
    density[1, 1] = 0.8
    pesticide = PesticideField(np.zeros_like(density))
    pesticide.deposit((1, 1), 1.0)
    model = PestDynamics(
        growth_rate_s=0.0,
        carrying_capacity=1.0,
        mortality_per_exposure=0.5,
        diffusion_rate_m2_s=0.1,
        wind=WindField(vx_m_s=0.2, vy_m_s=0.0),
    )

    updated = model.step(density, pesticide, dt_s=0.5, cell_size_m=(1.0, 1.0))

    assert updated.shape == density.shape
    assert np.all(updated >= 0.0)
    assert np.all(updated <= 1.0)
    assert updated[1, 1] < density[1, 1]
    assert updated[1, 2] > 0.0


def test_pesticide_field_decay_is_deterministic_and_nonnegative() -> None:
    pesticide = PesticideField(
        np.zeros((2, 2), dtype=float),
        decay_rate_s=np.log(2.0),
        wind=WindField(),
    )
    pesticide.deposit((0, 0), 1.0)

    updated = pesticide.step(dt_s=1.0, cell_size_m=(1.0, 1.0))

    assert updated[0, 0] == pytest.approx(0.5)
    assert np.all(updated >= 0.0)
