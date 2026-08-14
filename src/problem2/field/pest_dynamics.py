"""Deterministic pest-growth and pesticide-response dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .pesticide_field import PesticideField
from .wind_field import WindField, diffuse


@dataclass(frozen=True)
class PestDynamics:
    growth_rate_s: float = 0.0
    carrying_capacity: float = 1.0
    mortality_per_exposure: float = 0.02
    diffusion_rate_m2_s: float = 0.0
    wind: WindField = field(default_factory=WindField)

    def step(
        self,
        density: np.ndarray,
        pesticide: PesticideField,
        dt_s: float,
        *,
        cell_size_m: tuple[float, float] = (1.0, 1.0),
    ) -> np.ndarray:
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        density = np.asarray(density, dtype=float)
        if density.shape != pesticide.active.shape:
            raise ValueError("density and pesticide fields must have the same shape")
        capacity = max(float(self.carrying_capacity), 1e-12)
        if self.growth_rate_s < 0 or self.diffusion_rate_m2_s < 0:
            raise ValueError("growth and diffusion rates must be non-negative")
        growth = self.growth_rate_s * density * (1.0 - density / capacity)
        mortality = self.mortality_per_exposure * pesticide.active
        updated = density + dt_s * (growth - mortality)
        updated = diffuse(
            updated,
            self.diffusion_rate_m2_s,
            dt_s,
            cell_size_m=cell_size_m,
        )
        updated = self.wind.advect(updated, dt_s, cell_size_m=cell_size_m)
        return np.clip(updated, 0.0, capacity)
