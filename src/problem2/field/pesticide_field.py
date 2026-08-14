"""Pesticide deposition and first-order decay on the field grid."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .wind_field import WindField, diffuse


@dataclass
class PesticideField:
    active: np.ndarray
    decay_rate_s: float = 0.0
    efficacy_per_l: float = 1.0
    diffusion_rate_m2_s: float = 0.0
    wind: WindField = field(default_factory=WindField)

    def __post_init__(self) -> None:
        self.active = np.asarray(self.active, dtype=float).copy()
        if self.active.ndim != 2:
            raise ValueError("active pesticide field must be two-dimensional")
        if self.decay_rate_s < 0 or self.efficacy_per_l < 0 or self.diffusion_rate_m2_s < 0:
            raise ValueError("decay and efficacy parameters must be non-negative")

    def deposit(self, position: tuple[int, int], amount_l: float) -> None:
        if amount_l < 0:
            raise ValueError("deposition amount must be non-negative")
        row, col = position
        if not (0 <= row < self.active.shape[0] and 0 <= col < self.active.shape[1]):
            return
        self.active[row, col] += amount_l * self.efficacy_per_l

    def step(
        self,
        dt_s: float,
        *,
        cell_size_m: tuple[float, float] = (1.0, 1.0),
    ) -> np.ndarray:
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        self.active = self.wind.advect(self.active, dt_s, cell_size_m=cell_size_m)
        self.active = diffuse(
            self.active,
            self.diffusion_rate_m2_s,
            dt_s,
            cell_size_m=cell_size_m,
        )
        self.active *= float(np.exp(-self.decay_rate_s * dt_s))
        self.active = np.maximum(self.active, 0.0)
        return self.active.copy()
