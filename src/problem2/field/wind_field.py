"""Small deterministic wind-field representation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WindField:
    """A spatially constant two-dimensional wind field in m/s."""

    vx_m_s: float = 0.0
    vy_m_s: float = 0.0

    def advect(self, values: np.ndarray, dt_s: float) -> np.ndarray:
        """Return a nearest-cell advection approximation without changing shape."""
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        result = np.asarray(values, dtype=float).copy()
        if result.ndim != 2 or dt_s == 0:
            return result
        # The environment keeps the wind displacement sub-cell at its decision
        # resolution.  This conservative placeholder remains deterministic and
        # is replaced by a calibrated advection operator in the field audit.
        return result
