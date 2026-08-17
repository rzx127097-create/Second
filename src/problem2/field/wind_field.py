"""Small deterministic wind-field representation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WindField:
    """A spatially constant two-dimensional wind field in m/s."""

    vx_m_s: float = 0.0
    vy_m_s: float = 0.0

    def advect(
        self,
        values: np.ndarray,
        dt_s: float,
        *,
        cell_size_m: tuple[float, float] = (1.0, 1.0),
        boundary: str = "open",
    ) -> np.ndarray:
        """Advance a scalar field with a conservative first-order upwind step.

        The boundary is an open boundary with zero inflow.  The caller must
        choose a decision interval satisfying the CFL condition in each
        direction; otherwise a large jump would silently violate stability.
        """
        if dt_s < 0:
            raise ValueError("dt_s must be non-negative")
        if boundary not in {"open", "closed", "periodic"}:
            raise ValueError("boundary must be open, closed or periodic")
        result = np.asarray(values, dtype=float).copy()
        if result.ndim != 2:
            raise ValueError("values must be two-dimensional")
        if dt_s == 0:
            return result
        dy, dx = (float(cell_size_m[0]), float(cell_size_m[1]))
        if dy <= 0 or dx <= 0:
            raise ValueError("cell_size_m must contain positive values")
        c_x = abs(float(self.vx_m_s)) * dt_s / dx
        c_y = abs(float(self.vy_m_s)) * dt_s / dy
        if c_x > 1.0 + 1e-12 or c_y > 1.0 + 1e-12:
            raise ValueError("wind advection violates the CFL condition")
        if boundary == "periodic":
            if result.shape[1] > 1 and self.vx_m_s != 0:
                shift_x = 1 if self.vx_m_s > 0 else -1
                result = (1.0 - c_x) * result + c_x * np.roll(
                    result, shift_x, axis=1,
                )
            if result.shape[0] > 1 and self.vy_m_s != 0:
                shift_y = 1 if self.vy_m_s > 0 else -1
                result = (1.0 - c_y) * result + c_y * np.roll(
                    result, shift_y, axis=0,
                )
            return np.maximum(result, 0.0)
        if result.shape[1] == 1:
            # A degenerate column has no internal x-face.  A closed boundary
            # therefore has zero net x-flux and must leave the column intact.
            pass
        elif self.vx_m_s > 0:
            c = float(self.vx_m_s) * dt_s / dx
            out = result.copy()
            out[:, 0] = (1.0 - c) * result[:, 0]
            if result.shape[1] > 1:
                out[:, 1:-1] = (1.0 - c) * result[:, 1:-1] + c * result[:, :-2]
                if boundary == "open":
                    out[:, -1] = (1.0 - c) * result[:, -1] + c * result[:, -2]
                else:
                    out[:, -1] = result[:, -1] + c * result[:, -2]
            result = out
        elif self.vx_m_s < 0:
            c = -float(self.vx_m_s) * dt_s / dx
            out = result.copy()
            out[:, -1] = (1.0 - c) * result[:, -1]
            if result.shape[1] > 1:
                out[:, 1:-1] = (1.0 - c) * result[:, 1:-1] + c * result[:, 2:]
                if boundary == "open":
                    out[:, 0] = (1.0 - c) * result[:, 0] + c * result[:, 1]
                else:
                    out[:, 0] = result[:, 0] + c * result[:, 1]
            result = out
        if result.shape[0] == 1:
            # A degenerate row has no internal y-face; closed boundaries keep
            # its mass unchanged rather than applying a phantom outflow.
            pass
        elif self.vy_m_s > 0:
            c = float(self.vy_m_s) * dt_s / dy
            out = result.copy()
            out[0, :] = (1.0 - c) * result[0, :]
            if result.shape[0] > 1:
                out[1:-1, :] = (1.0 - c) * result[1:-1, :] + c * result[:-2, :]
                if boundary == "open":
                    out[-1, :] = (1.0 - c) * result[-1, :] + c * result[-2, :]
                else:
                    out[-1, :] = result[-1, :] + c * result[-2, :]
            result = out
        elif self.vy_m_s < 0:
            c = -float(self.vy_m_s) * dt_s / dy
            out = result.copy()
            out[-1, :] = (1.0 - c) * result[-1, :]
            if result.shape[0] > 1:
                out[1:-1, :] = (1.0 - c) * result[1:-1, :] + c * result[2:, :]
                if boundary == "open":
                    out[0, :] = (1.0 - c) * result[0, :] + c * result[1, :]
                else:
                    out[0, :] = result[0, :] + c * result[1, :]
            result = out
        return np.maximum(result, 0.0)


def diffuse(
    values: np.ndarray,
    diffusion_rate_m2_s: float,
    dt_s: float,
    *,
    cell_size_m: tuple[float, float] = (1.0, 1.0),
) -> np.ndarray:
    """Apply one explicit no-flux diffusion step on a rectangular grid."""

    if diffusion_rate_m2_s < 0 or dt_s < 0:
        raise ValueError("diffusion_rate_m2_s and dt_s must be non-negative")
    result = np.asarray(values, dtype=float)
    if result.ndim != 2:
        raise ValueError("values must be two-dimensional")
    if dt_s == 0 or diffusion_rate_m2_s == 0:
        return result.copy()
    dy, dx = (float(cell_size_m[0]), float(cell_size_m[1]))
    if dy <= 0 or dx <= 0:
        raise ValueError("cell_size_m must contain positive values")
    coefficient = float(diffusion_rate_m2_s) * dt_s * (1.0 / dx**2 + 1.0 / dy**2)
    if coefficient > 0.5 + 1e-12:
        raise ValueError("diffusion step violates the explicit stability condition")
    padded = np.pad(result, 1, mode="edge")
    laplacian = (
        (padded[1:-1, 2:] - 2.0 * result + padded[1:-1, :-2]) / dx**2
        + (padded[2:, 1:-1] - 2.0 * result + padded[:-2, 1:-1]) / dy**2
    )
    return np.maximum(result + float(diffusion_rate_m2_s) * dt_s * laplacian, 0.0)
