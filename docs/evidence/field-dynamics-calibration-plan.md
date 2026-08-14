# Field-Dynamics Calibration Plan

The repository now contains a mechanistic pilot model, but its coefficients are
not treated as universal constants. The state variables are normalized pest
density `N`, pesticide exposure `C`, and a declared wind vector `u` in SI
coordinates. The implemented operator splitting is:

```text
dN/dt = r N (1 - N/K) + D_N Laplacian(N) - mu C
N(t + dt) = UpwindAdvection(dN/dt, u, dt)

dC/dt = D_C Laplacian(C) - lambda C
C(t + dt) = UpwindAdvection(C, u, dt)
```

Spray deposition adds `alpha * amount_l` to `C` at the UAV cell before the
field step. The implementation uses no-flux diffusion, open-boundary upwind
advection and non-negativity clipping. `configs/field_dynamics.yaml` records
the provisional values and units.

## Required evidence before formal use

1. **Pest growth**: obtain at least two independent pest-density time series
   without treatment and fit `r` and `K` with a declared observation model.
2. **Spatial spread**: track hotspot centroids or gridded density at multiple
   time points and estimate `D_N`; compare a no-wind and wind-stratified fit.
3. **Wind**: pair field anemometer measurements with the time interval used by
   the simulator; do not substitute UAV downwash measurements for regional
   wind.
4. **Pesticide persistence**: use the actual compound and crop, fit a
   first-order or better-supported residue curve, and convert its half-life to
   `lambda = ln(2) / half_life` in seconds.
5. **Deposition and efficacy**: measure deposited liquid per cell and combine
   it with a pest bioassay to estimate `alpha` and `mu`. UAV droplet-deposition
   studies in the source ledger justify the mechanism, not the coefficient.
6. **Numerical convergence**: rerun representative scenes at `dt`, `dt/2` and
   `dt/4`; record endpoint and mediator differences and use the pre-registered
   tolerance to decide whether `decision_dt` is admissible.

Until these records exist, the correct thesis wording is “mechanistic pilot
model with provisional coefficients”. It is not “field-calibrated ecosystem
model”.
