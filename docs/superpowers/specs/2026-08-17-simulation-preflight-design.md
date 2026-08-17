# Controlled-Simulation Preflight Design

## 1. Research Position

Problem 2 is a controlled simulation study of road-constrained air-ground
cooperative spraying with finite onboard pesticide and a mobile replenishment
vehicle. The environment uses public reference ranges, documented scene-scale
conversions, and explicit simulation assumptions. It does not claim field
deployment, field measurement, or equipment-specific calibration.

The flagship algorithm remains **SR-MAPPO**. No HAPPO implementation and no
new public algorithm name are introduced.

## 2. Decision

Remove field-calibration readiness as a runtime blocker. Replace the current
formal-readiness gate in training, matrix execution, evaluation, and validation
freeze with one controlled-simulation preflight.

The preflight has two types of findings:

- `error`: a technical fault that can invalidate, corrupt, mix, or leak
  experimental evidence; execution stops.
- `warning`: an evidence limitation that constrains thesis wording but does
  not prevent a controlled simulation from running.

Missing real equipment tests, crop-specific field measurements, pesticide
bioassays, or expert records are warnings. They are not execution errors.

## 3. What Remains Blocking

The simulation preflight stops execution only for the following conditions:

1. A required runtime parameter, value, unit, finite range, conversion, or
   explicit assumption rationale is missing.
2. A runtime value differs from the frozen simulation profile.
3. A parameter lies outside its declared simulation range.
4. Unit conversion, pesticide conservation, service-state, or action-mask
   invariants fail.
5. Wind advection or explicit diffusion violates the implemented numerical
   stability bound.
6. The frozen road file or metadata hash does not match the configuration, the
   graph is unusable, or vehicle-on-road enforcement is disabled.
7. Train, validation, and sealed-test scenario identifiers overlap, a scale is
   absent, or a scenario references the wrong scale.
8. A non-smoke run uses a dirty source tree, mismatched configuration/protocol
   hash, incompatible checkpoint, non-finite training state, or damaged log.
9. Deterministic evaluation attempts to update normalization statistics.
10. A sealed-test request lacks a matching validation freeze and consumable
    unlock record.

These checks protect reproducibility and experimental validity; they do not
require real-world calibration.

## 4. What Becomes Advisory

The following findings are emitted as warnings and preserved in run metadata:

- `source_type: assumption`;
- a public product reference that is not the exact simulated device;
- a scene-scale conversion rather than a one-to-one physical value;
- an ecological coefficient lacking crop- or compound-specific calibration;
- an OSM road graph used as representative simulation input rather than a
  surveyed experimental farm;
- absence of field or deployment validation.

Warnings must never be silently removed. They define the claim boundary, but
they do not reject the run.

## 5. Frozen Simulation Profile

Add `configs/simulation_profile.yaml` as the controlled-simulation evidence
manifest. Authoritative runtime values remain in the existing configuration
files; the profile cross-checks them.

```yaml
schema_version: 1
status: frozen_for_controlled_simulation
evidence_mode: controlled_simulation
claim_boundary: >-
  Results are produced in a controlled simulation and do not constitute field
  validation or measured deployment effectiveness.
engineering_parameters: {}
field_parameters: {}
derived_regimes: {}
```

Each parameter record contains:

- `runtime_path`, `value`, `unit`, `min`, and `max`;
- `source_type`, `source_id`, and any available reference value or range;
- a reproducible `conversion`;
- `assumption_rationale` and `selection_rule`;
- `sensitivity_required` plus levels, or a documented exclusion rationale.

The engineering group contains all 11 runtime quantities:

```text
uav_onboard_pesticide, uav_spray_flow, uav_usable_fraction, uav_speed,
vehicle_inventory, vehicle_transfer_rate, vehicle_service_capacity,
service_setup_time, rendezvous_radius, vehicle_speed, decision_dt
```

The main scene-scale values remain:

| Parameter | Value | Unit |
|---|---:|---|
| UAV onboard pesticide | 1.0 | L |
| UAV spray flow | 0.01 | L/s |
| UAV usable fraction | 0.8 | 1 |
| UAV speed | 1.0 | m/s |
| Vehicle inventory | 5.0 | L |
| Vehicle transfer rate | 0.02 | L/s |
| Vehicle service capacity | 5.0 | L |
| Service setup time | 10.0 | s |
| Rendezvous radius | 5.0 | m |
| Vehicle speed | 1.0 | m/s |
| Decision interval | 1.0 | s |

These are explicit controlled-simulation values. Their public source values
and scaling formulae remain visible; they are not described as a physical T40
deployment with a 1 L tank.

The field group contains every parameter in
`configs/field_dynamics.yaml`. Dominant uncertain ecological and pesticide
coefficients receive pre-registered sensitivity levels. The profile also
reports joint operating regimes, including usable liquid, spray endurance,
nominal refill time, vehicle-to-UAV inventory ratio, travel per decision,
Courant number, and diffusion numbers.

## 6. Runtime Interface

The supported execution profiles are:

| Profile | Purpose | Network and horizon |
|---|---|---|
| `smoke` | Interface, recovery, and wiring checks | reduced |
| `simulation` | Thesis controlled-simulation experiments | full |

Add `--simulation` to the training, matrix, evaluation, matrix-evaluation, and
validation-freeze entry points. `--simulation` and `--smoke` are mutually
exclusive. A full run records `execution_profile=simulation` in its immutable
job identity.

The existing field-readiness audit may remain available as a standalone
diagnostic command, but no controlled-simulation execution path calls it and
its result cannot block a simulation job.

Every simulation run stores:

- simulation-profile hash;
- configuration and protocol hashes;
- Git commit and source-tree hash;
- warnings and claim boundary;
- method, scale, seed, family, condition, horizon, and target update budget.

## 7. Preflight Output

Add `src/problem2/experiments/simulation_preflight.py` and
`scripts/audit_simulation_preflight.py`.

The machine-readable result is:

```json
{
  "ready": true,
  "evidence_mode": "controlled_simulation",
  "errors": [],
  "warnings": [],
  "derived_regimes": {},
  "claim_boundary": "Results are produced in a controlled simulation and do not constitute field validation or measured deployment effectiveness."
}
```

An optional resource-pilot report is checked when supplied. If the report is
missing, the preflight warns that mechanism activation is unconfirmed. If a
supplied report is malformed or contradicts pesticide conservation, execution
stops. If it is valid but reports `activated=false`, the preflight warns and
allows diagnostic/pilot work; the result cannot be promoted to a mechanism or
superiority claim.

## 8. Validation And Sealed Test

Simulation validation and sealed-test isolation remain mandatory:

1. Train and tune only with train/validation scenarios.
2. Freeze the exact simulation profile, configurations, protocol, checkpoints,
   validation artifacts, statistics, and source identity.
3. Create an unlock record whose evidence mode is `controlled_simulation`.
4. Evaluate the sealed scenarios once under the frozen identity.

This is not a real-data gate. It prevents test-set tuning and result selection.

## 9. Tests And Acceptance Criteria

Implementation follows red-green-refactor. Required behavior tests cover:

- a complete controlled-simulation profile passes despite assumption sources;
- missing real calibration creates warnings, not errors;
- a missing rationale, invalid range, or profile/runtime mismatch creates an
  error;
- unstable Courant/diffusion settings create an error;
- road hash or split isolation faults create an error;
- missing resource pilot warns, malformed or conservation-inconsistent pilot
  fails, and inactive valid pilot warns;
- `simulation` job identities are isolated from `smoke` identities;
- CLI mode flags are mutually exclusive;
- simulation mode uses full configured dimensions and horizon;
- matrix child processes receive `--simulation`;
- checkpoint, configuration, protocol, and source hashes must match;
- deterministic evaluation freezes normalization state;
- sealed-test evaluation still requires a matching freeze and unlock;
- the preflight CLI emits deterministic machine-readable output.

Completion requires targeted tests, the full test suite,
`python -m compileall -q src scripts`, `git diff --check`, a clean post-commit
worktree, and a successful push to
`origin/feature/problem2-code-framework`.

## 10. Research Maturity And Claims

Passing the preflight means the project can start controlled-simulation pilots.
It does not itself prove algorithm performance. The evidence sequence is:

```text
simulation preflight
-> resource activation and counterfactual pilot
-> validation-only parameter and method freeze
-> multi-seed matrix
-> sealed-test evaluation
-> paired statistics and traceable thesis artifacts
```

Before the multi-seed pilot, use "the implementation was verified". After a
valid pilot, use "pilot simulation results indicate". Only after the frozen
matrix and sealed-test evidence chain is complete may the thesis state that the
controlled simulation experiments support a result. No stage permits a field
validation or real deployment claim.

## 11. Non-Goals

This change does not tune parameters to force SR-MAPPO to win, weaken rolling
A*, fabricate missing evidence, merge smoke and full checkpoints, modify a Word
document, or modify the first-problem repository.
