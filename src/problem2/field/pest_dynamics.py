"""Deterministic pest-growth and pesticide-response dynamics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .pesticide_field import PesticideField


@dataclass(frozen=True)
class PestDynamics:
    growth_rate_s: float = 0.0
    carrying_capacity: float = 1.0
    mortality_per_exposure: float = 0.02

    def step(
        self,
        density: np.ndarray,
        pesticide: PesticideField,
        dt_s: float,
    ) -> np.ndarray:
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        density = np.asarray(density, dtype=float)
        if density.shape != pesticide.active.shape:
            raise ValueError("density and pesticide fields must have the same shape")
        capacity = max(float(self.carrying_capacity), 1e-12)
        growth = self.growth_rate_s * density * (1.0 - density / capacity)
        mortality = self.mortality_per_exposure * pesticide.active
        updated = density + dt_s * (growth - mortality)
        return np.clip(updated, 0.0, capacity)
