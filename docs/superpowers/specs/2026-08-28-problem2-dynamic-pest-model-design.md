# Problem-2 Dynamic Pest Model Integration Design

## Status

The user approved this architecture in chat on 2026-08-28. This document is
the written design submitted for final review before an implementation plan is
created. It does not authorize G6 formal execution, G7 sealed access, or any
efficacy or superiority claim.

## Purpose

Problem 2 currently couples the verified air-ground pesticide service system
to a validation adapter that subtracts a fixed amount of pest intensity only
at the sprayed cell. That adapter omits the dynamic ecological environment used
by Problem 1: Holling-Tanner reaction-diffusion, wind advection, a spatial
pesticide-effect field, and pesticide decay.

Problem 2 must inherit that complete dynamic-pest design while remaining a
self-contained, auditable repository. After this change, every future primary
experiment uses the same dynamic ecological environment by default:

- five-algorithm convergence and scale comparisons;
- mobile versus fixed support;
- learned vehicle control versus rolling A*, nearest, and urgency controllers;
- joint versus two-stage SR-MAPPO training;
- SR-MAPPO ablations;
- SR-MAPPO sensitivity experiments;
- G6 formal jobs and G7 sealed evaluation.

A static pest field may remain only as an explicitly named development
diagnostic or counterfactual. It is not admissible as the environment for a
primary, formal, or sealed result.

## Research and Gate Boundary

- The public algorithm name remains `SR-MAPPO`.
- Problem 2 remains the air-ground heterogeneous extension of SR-MAPPO.
- Pesticide remains the only replenished resource.
- Battery replenishment remains inactive.
- OSM remains a road-constrained simulation input, not deployment evidence.
- The current highest maturity remains M2.
- Existing G5 validation and refit artifacts are historical static-adapter
  evidence. They must remain byte-preserved and must not be relabeled as
  dynamic-environment evidence.
- G6 remains blocked. The ecological transition changes training data,
  observation meaning, reward meaning, scenario hashes, checkpoint selection,
  and every experimental estimand. G3-G5 acceptance must therefore be rerun
  before G6 can be authorized.
- The sealed-test lock remains at maximum unlock count `1` and actual unlock
  count `0` throughout implementation and renewed pilot work.

## Source Lineage

The protected Problem-1 repository is a read-only design source:

```text
C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper
```

Only the committed snapshot at
`1ca9e5ccc5f77ed775cd2b607dd70d635720accf` is admissible as source lineage.
Current uncommitted Problem-1 reward-sensitivity work is excluded. No
Problem-1 module is imported at runtime and no Problem-1 file is modified.

| Problem-1 committed path | Git blob | Adopted design |
|---|---|---|
| `source/locust_rl_selected/models/holling_tanner.py` | `3cd829a907d6931206a4045c3436a941bc1cacfc` | reflected-boundary Laplacian, upwind advection, Holling-Tanner reactions, bounded pesticide mortality, three-substep integration |
| `source/locust_rl_selected/models/subsystems.py` | `245e9c46cb977629e3e22e09841693be7095db38` | dynamic wind and radius-weighted persistent pesticide-effect field |
| `source/locust_rl_selected/envs/locust_env.py` | `dcc1527be19667daca41e310c69dde8775b6eb83` | ecological update order and Gaussian prey/predator initialization |
| `source/locust_rl_selected/config/settings.py` | `25bbd3afb90b5be1e0d267d3aabf938526ef5ae2` | committed model defaults and parameter names |

The Problem-2 implementation is formula-equivalent rather than a direct file
copy. It removes global RNG coupling, validates domains strictly, records
scenario state hashes, and maps accepted physical spray volume to pesticide
effect without enabling battery replenishment.

## Chosen Integration Approach

The model is implemented inside this repository under a dedicated ecological
ownership boundary. Runtime import from Problem 1 is rejected because it would
make Problem-2 reproduction depend on a protected dirty worktree. Immediate
conversion to fully calibrated SI ecology is also deferred: the Problem-1
reaction time, diffusion, advection, and pesticide parameters are normalized
simulation parameters, not verified field coefficients.

The first implementation therefore provides a lineage-compatible normalized
simulation model. Every parameter remains explicitly marked as a provisional
simulation assumption. A later physical-calibration audit may replace those
values only by reopening the experiment freeze and recording literature or
equipment evidence.

## Planned Module Boundary

```text
src/problem2/ecology/
  __init__.py
  config.py
  dynamics.py
  pesticide.py
  scenario.py
  system.py
```

- `config.py` owns immutable validated parameter records.
- `dynamics.py` owns pure numerical operators and one ecological transition.
- `pesticide.py` owns concentration, duration, radial deposition, and decay.
- `scenario.py` owns deterministic initial prey, predator, and wind generation
  plus canonical scenario hashing.
- `system.py` owns state, step order, summaries, snapshots, and restoration.

The physical road, vehicle, request, service, and pesticide-conservation state
machine remains owned by existing Problem-2 modules. The ecological system
consumes accepted `spray` events; it never changes whether a spray is legal or
how many litres were consumed.

## Frozen Formula Semantics

Let `x` be pest/prey density and `y` predator density. For each ecological
substep, the adopted reaction terms are:

```text
f(x, y) = x * (1 - beta * x) - m * x * y / (x + 1)
g(x, y) = s * y * (1 - y / max(x, epsilon))
```

When prey is below `1e-6`, predator reaction uses the Problem-1 fallback
`-0.1 * y`. Reaction terms are clipped to `[-0.5, 0.5]` before integration.
Spatial diffusion uses a five-point Laplacian with reflected padding. Wind
transport uses the same sign-dependent first-order upwind differences as
Problem 1. Prey and predator advection multipliers remain `0.05` and `0.01`.

The normalized model parameters initially remain:

| Parameter | Value |
|---|---:|
| `beta` | `1.5` |
| `m` | `2.0` |
| `s` | `0.25` |
| prey diffusion `d1` | `0.3` |
| predator diffusion `d2` | `0.3` |
| ecological integration interval | `0.005` |
| substeps per physical decision | `3` |
| spatial normalization `dx` | `pi / max(grid_shape)` |

The ecological integration interval is not interpreted as five physical
seconds. One ecological transition is coupled to one Problem-2 decision step;
the normalized ecological interval remains a simulation assumption until a
separate calibration gate is passed.

Prey is clipped to `[0, 1 / beta]` after each substep. Predator density is
clipped to `[0, 2 / beta]`. Every input and output array must be finite,
two-dimensional, shape-identical, and nonnegative.

## Wind Contract

Dynamic wind is enabled for all primary experiments. Each scenario owns an
independent NumPy `Generator` whose state is separate from policy, replay,
training, and global NumPy RNG state. The scenario seed fixes initial wind and
all later perturbations.

The initial dynamic contract inherits the Problem-1 full-stage range and noise
semantics:

| Parameter | Value |
|---|---:|
| strength range | `[0.0, 0.5]` |
| direction noise standard deviation | `0.1` |
| strength noise standard deviation | `0.05` |
| slow direction term | `0.005 * sin(step / 50)` |

Initial direction is sampled uniformly on `[0, 2*pi)` and initial strength is
sampled within the frozen range. Strength is clipped to that range after every
update. Wind state and RNG state are included in checkpoints and deterministic
replay snapshots.

## Pesticide-Effect Contract

The ecological pesticide field is separate from the conserved physical litre
ledger. It contains concentration, remaining duration, and spray-count arrays.
Only a positive, accepted Problem-2 `spray` event may deposit effect.

The inherited normalized parameters are:

| Parameter | Value |
|---|---:|
| full-step center effect | `0.85` |
| effect duration | `15` decision steps |
| concentration decay | `0.92` per decision step |
| spray radius | `4` grid cells |
| predator sensitivity | `0.1` |

The existing Problem-2 `spray_per_step_l` is the reference full-step volume.
For an accepted event with physical volume `delta_l`, center effect is
`0.85 * delta_l / spray_per_step_l`, capped through the inherited
concentration rule. This preserves a one-full-action correspondence with
Problem 1 while ensuring partial physical sprays cannot receive a full effect.

At a cell whose grid distance from the spray center is `r <= 4`, deposited
effect is multiplied by `1 - r / 5`. Concentration is capped at `1.0`.
Duration takes the maximum of its prior value and `15`. Before reaction-
diffusion integration, prey mortality is
`min(concentration * 2.0, 0.98)` and predator mortality is
`min(concentration * 0.1, 0.3)`. After ecological integration, duration is
decremented, concentration is multiplied by `0.92`, and expired concentration
is set to zero.

## Scenario Generation and Identity

The current gamma field normalized to a fixed total of `100` is replaced for
new dynamic runs by the committed Problem-1 hotspot design:

- one or two prey sources;
- source centers within the middle half of the grid;
- prey Gaussian sigma `min(height, width) / 5`;
- prey peak `0.10` per source and final clip at `0.5`;
- one or two predator sources;
- predator Gaussian sigma `6.0` cells;
- predator peak `0.30` per source.

All methods paired on one scenario receive byte-identical initial prey,
predator, pesticide, wind, and RNG states. Scenario generation does not use
training randomness. The canonical scenario hash includes:

```text
partition
scenario_id
scale_id
dynamic-ecology contract hash
grid shape
initial prey bytes
initial predator bytes
initial pesticide concentration and duration bytes
initial wind state
ecology RNG bit-generator name and state
source commit and implementation version
```

Changing any dynamic parameter, step order, numerical operator, initial field,
or RNG algorithm creates a new scenario identity and invalidates checkpoint
reuse.

## Environment Data Flow

One Problem-2 decision step executes in this exact order:

1. Validate and execute UAV and vehicle actions in the existing physical
   environment.
2. Apply physical pesticide consumption and service/resource events.
3. Convert each accepted positive `spray` event to a radial ecological
   pesticide deposit at the spraying UAV's action-complete position.
4. Update dynamic wind from the scenario-owned RNG.
5. Apply pesticide mortality to prey and predator fields.
6. Execute three Holling-Tanner reaction-diffusion-advection substeps.
7. Decay and expire the pesticide-effect field.
8. Compute action-complete ecological summaries and rebuild role observations
   and centralized critic state from the same completed state.
9. Compute the signed team reward and append ecological diagnostics.

No learner or heuristic may bypass this wrapper. Training, development pilot,
validation, formal evaluation, and sealed evaluation construct the environment
through one factory whose default and formal-only mode is dynamic.

## Observation Contract

The existing G3 tensor dimensions remain unchanged:

- UAV observation: `43 + 68N`;
- vehicle observation: `28`;
- centralized critic state: `45 + 70N`.

Previously padded slots are assigned explicit ecological semantics rather than
changing network shapes.

The eight existing field-summary slots contain the six Problem-1 prey global
statistics (normalized total, mean, maximum, standard deviation, high-density
ratio, and nonzero coverage) plus mean and maximum pesticide concentration.

Nine new ecological-context values occupy existing UAV/critic padding: six
predator global statistics and normalized wind direction x/y plus strength.
Each UAV also receives six action-time local values in its existing base
padding: local prey, local predator, local pesticide concentration, prey
gradient x/y, and neighborhood mean prey. The critic receives the same global
context and per-UAV local values. Vehicle dimensions stay unchanged; the
vehicle acts on observable service requests and road state and receives no
privileged future ecology.

All dimensions, index ranges, normalization rules, and actor-versus-critic
visibility are added to the heterogeneous-interface registry. Existing
checkpoints are semantically incompatible even though tensor shapes match.

## Reward and Outcome Contract

Problem 2 retains one shared team reward across roles. The ecological reward
becomes the signed normalized one-step pest change:

```text
team_reward = (total_pest_before - total_pest_after) / initial_total_pest
```

No `max(0, ...)` clamp is allowed. Natural growth or adverse transport can
therefore produce negative reward. The reward remains a training diagnostic;
thesis conclusions use fixed-scenario endpoint metrics.

`reduction_rate` remains:

```text
1 - final_total_pest / initial_total_pest
```

Dynamic growth means `final_total_pest` may exceed `initial_total_pest` and
reduction rate may be negative. Validators must accept that physically valid
case. A positive reduction no longer logically requires a spray because
predation may reduce prey without spraying; validators instead verify direct
ecological provenance, action/event counts, and exact metric derivation.

Raw episode rows add direct ecology fields including model/version hash,
initial/final predator totals, cumulative deposited effect, mean/max terminal
concentration, wind summary, and dynamic-step count. Every formal result must
remain traceable from source parameters through scenario and run hashes.

## Fairness and Experiment Defaults

Every condition within a paired scenario uses identical dynamic inputs,
decision horizon, pesticide budget, scenario seed, and information timing.
The following are prohibited:

- dynamic ecology for SR-MAPPO but static ecology for a baseline;
- different wind streams or initial predator fields across methods;
- controller access to future wind or future pest states;
- disabling growth, diffusion, advection, predators, or pesticide decay for a
  primary ablation or sensitivity run unless that ecological mechanism itself
  is a separately registered exploratory experiment;
- selecting favorable ecology seeds after validation or sealed evaluation.

SR-MAPPO algorithmic ablations and sensitivity vary only their registered
SR-MAPPO component or hyperparameter. They do not vary ecology. Static ecology
is restricted to a clearly labeled non-primary development diagnostic used to
verify causal behavior.

## Historical Evidence and Output Migration

Existing files below `outputs/problem2_sr_mappo_v1/g5` are preserved as the
historical linear-local-decrease evidence set. They are not overwritten,
rehashed, or silently migrated.

Renewed dynamic evidence is written below:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
  g3/
  g4/
  g5/
  g6/
  g7/
  g8/
```

`docs/PROJECT_STATE.md` identifies this namespace as canonical for all future
Problem-2 experiment work after the renewed freeze passes. Old artifacts keep
their original claim boundary and provenance.

## Verification Strategy

Implementation follows test-driven development. Required tests include:

1. hand-computable reflected Laplacian cases;
2. positive- and negative-wind upwind-advection cases;
3. independent one-substep and three-substep Holling-Tanner gold values;
4. prey/predator clipping, finite-domain, and shape rejection;
5. radial pesticide deposition, partial-volume scaling, overlap capping,
   duration, decay, and expiration;
6. deterministic wind and complete ecology-state/RNG round trips;
7. scenario replay equality and paired-method initial-state byte equality;
8. no-spray growth/spread and spray-versus-no-spray counterfactual behavior;
9. accepted versus rejected physical spray-event integration;
10. action-complete observation rebuilding with exact unchanged dimensions;
11. signed reward and negative reduction-rate validation;
12. dynamic-by-default guards for every experiment family and CLI;
13. static-primary and static-sealed fail-closed tests;
14. checkpoint interruption/resume equivalence including ecology RNG/state;
15. all existing G2-G5 regression tests.

Numerical golden fixtures are computed independently in tests and do not call
the implementation under test. Property checks alone are insufficient.

## Gate Reopening and Acceptance

Implementation proceeds in this order and stops at the first failed gate:

1. Freeze the dynamic-ecology contract and source-lineage registry.
2. Pass numerical unit tests and deterministic scenario replay.
3. Integrate accepted physical spray events and revalidate pesticide
   conservation independently from ecological effect.
4. Revalidate G3 observation, normalization, checkpoint, and deterministic
   evaluation contracts under the new observation semantics.
5. Rerun G4 scarcity/mobile-fixed mechanism probes in dynamic ecology.
6. Repair condition semantics so fixed, A*, nearest, urgency, two-stage,
   SR-MAPPO ablation, and SR-MAPPO sensitivity conditions execute real
   behavior rather than labels.
7. Rerun fair G5 development pilots and validation-only tuning in the new
   output namespace, then freeze new G6/G7 manifests.
8. Implement and verify the real G6 runner/recovery/evaluator before any
   formal job starts.

Code plus unit/integration tests can restore M2 only. M3 requires a complete
multi-seed pilot on independent validation scenarios. M4 requires immutable
formal jobs, one sealed unlock, paired statistics, and a complete evidence
chain.

## Design Acceptance Criteria

This design is ready for an implementation plan only if it explicitly ensures:

- complete Holling-Tanner, wind, and pesticide-decay semantics are present;
- all future primary experiments default to dynamic ecology;
- no runtime dependency or write occurs in the protected Problem-1 repository;
- static ecology cannot enter primary or sealed results;
- current G5 evidence is preserved rather than overwritten;
- observations and checkpoints cannot silently reuse old ecological semantics;
- dynamic growth and predation are valid in reward and endpoint validators;
- G3-G5 are reopened and G6/G7 remain blocked until renewed verification;
- all phase commits, pushes, hashes, and verification results are recorded in
  `docs/PROJECT_STATE.md`.
