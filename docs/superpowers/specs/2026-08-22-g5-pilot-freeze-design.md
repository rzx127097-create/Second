# G5 Fair-Pilot and Method-Freeze Design

## Status

The G5-G7 architecture was approved in chat on 2026-08-22. This document is
the written G5 specification submitted for user review. It defines the code,
pilot, fairness, tuning, statistics, and freeze boundary that must exist before
G6 formal jobs may start. It is not an implementation plan and does not
authorize G6 or G7 execution.

## Purpose and Gate Boundary

G5 converts the verified G2/G3/G4 foundation into one complete, testable
experiment system. All scientific code needed by the requested comparisons is
implemented or adapted here, exercised by development and validation pilots,
and then frozen with machine-readable hashes.

G5 includes:

1. five heterogeneous learning algorithms;
2. the required Problem-2 comparison family;
3. three classical vehicle-dispatch heuristics;
4. SR-MAPPO remove-one ablations;
5. algorithmic and mechanism sensitivity support;
6. shared training, evaluation, checkpoint, recovery, validation, and
   statistics code;
7. fair development/validation pilots and the final method/statistics freeze.

G5 excludes immutable formal jobs, sealed-test access, formal superiority
claims, figure/table generation for thesis conclusions, and Word-file edits.
The highest permitted result wording is "pilot results indicate" and only
after a complete multi-seed pilot passes. Training reward remains diagnostic.

The public flagship name remains `SR-MAPPO`. Problem 2 is its air-ground
heterogeneous extension. HAPPO and `AG-SR-MAPPO` are not methods. Pesticide is
the only replenished resource; battery replenishment remains inactive. OSM is
an offline simulation input rather than deployment evidence.

## G5 Entry Reconciliation

No pilot may start until the accepted G4 record is internally consistent.
Fresh inspection on 2026-08-22 found two concrete discrepancies:

- short commit `4e81567` resolves to
  `4e8156712986a28f81315968fd7640b6e7ed5ad6`, while `HANDOFFG4.md` and
  `docs/PROJECT_STATE.md` record the nonexistent object
  `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5`;
- canonical `outputs/problem2_sr_mappo_v1/g4/provenance.json` binds source
  commit `09d361994100741a9ae834b63ba07c9b5db953e7` and tree
  `5a61825001e92fae112579ae05f5c778deedcab3`, whereas the handoff claims
  generator commit `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` and tree
  `78d3d146b06f191998853ef7070b167a5df64a5c`.

G5 must first determine which source tree actually generated the accepted
artifacts. If the current artifacts are valid, the documents must be corrected
to their true lineage. If `ee0d3faf...` is the intended generator, the bundle
must be regenerated from a clean source tree and re-audited. The chosen repair
must produce one exact commit/tree/hash tuple across the G4 provenance,
manifest, audit, handoff, and project state. Historical files must not be
silently overwritten. The repair and its verification must be committed and
pushed before any G5 pilot record is accepted.

The entry audit must also confirm:

- G2 deterministic tests and G3 heterogeneous-MARL acceptance tests still
  pass;
- G4 remains pesticide-only diagnostic evidence and is not relabeled as a
  learned-policy result;
- the sealed lock still reports maximum unlock count `1` and actual count `0`;
- protected first-problem and external OSM assets are unchanged.

## Controlled Extension of Problem 1

Problem 2 inherits algorithmic mathematics and tested implementation ideas
from Problem 1, but its runtime and evidence chain are self-contained in this
repository. The protected first-problem source is read only at commit
`1ca9e5ccc5f77ed775cd2b607dd70d635720accf`; current uncommitted user work in
that repository is excluded.

G5 creates a lineage registry with the source commit, path, Git blob ID,
adopted concept, required Problem-2 modification, and destination path. The
initial source set includes the following immutable blobs:

| First-problem path | Blob ID | Intended use |
|---|---|---|
| `source/locust_rl_selected/agents/sr_mappo_agent.py` | `fe3479f0a86f7957f3329650f24da1f561f40759` | SR-MAPPO mathematics and stability logic |
| `source/locust_rl_selected/agents/mappo_agent.py` | `e73a1be28469afc410ffadca7a48dbf9992e1a94` | MAPPO baseline semantics |
| `source/locust_rl_selected/agents/ippo_agent.py` | `e46b1dc8f673310587d2a1888d5cb77a322d906a` | independent PPO semantics |
| `source/locust_rl_selected/agents/maddpg_agent.py` | `4371654da593b6d69e8e5853113fd6dbdbc2181f` | MADDPG update semantics |
| `source/locust_rl_selected/agents/iql_agent.py` | `0327d210e6d9c2fd21c48324963e4a4d0dd80953` | IQL update semantics |
| `source/locust_rl_selected/training/trainer.py` | `935aed90b16a897f4449673f530f0aa31a1536e3` | training-loop lineage only |
| `scripts/run_sr_mappo_ablation.py` | `bfda945b554f3a299765aeef2a5df23b7b2d88d1` | ablation orchestration lineage |
| `scripts/run_sr_mappo_sensitivity.py` | `9281a0dc76647e4ed534d36f165b058cd8a354a8` | sensitivity orchestration lineage |

No Problem-1 module is imported at runtime. No Problem-1 checkpoint, output,
log, or reported result is admissible as Problem-2 evidence. The verified
Problem-2 environment, role observations, action masks, service state machine,
resource ledger, logging, and checkpoint contracts take precedence whenever
the two problems differ.

## Unified Heterogeneous Algorithm Contract

Every learning algorithm must explicitly model both roles. "Heterogeneous" is
not reserved for MADDPG or IQL.

All methods must expose a common protocol that accepts:

- one shared UAV policy for the homogeneous UAV fleet and one separate vehicle
  policy;
- UAV observations of dimension $43 + 68N$, where $N$ is the number of UAVs,
  vehicle observations of dimension $28$, and the exact verified G3 dimensions
  for the frozen primary count;
- six UAV actions and five vehicle candidate-slot actions;
- role-specific legal-action masks stored with every transition;
- a shared team reward and explicitly declared value/Q conditioning;
- deterministic evaluation that cannot update normalization or exploration
  state;
- complete serializable training and RNG state.

The common interfaces cover algorithm construction, masked action selection,
rollout/replay ingestion, update, evaluation mode, checkpoint state, and
diagnostic counters. A method-specific adapter may use on-policy trajectories
or off-policy replay, but it may not bypass the environment, observation,
mask, resource, logging, or evaluation contracts.

### Five-Algorithm Family

| Display name | Method ID | Heterogeneous implementation |
|---|---|---|
| SR-MAPPO | `sr_mappo_mobile` | separate UAV/vehicle actors, structured centralized value critic, GAE/PPO, all five SR stability groups enabled |
| MAPPO | `mappo_mobile` | same actors, critic, rollout, budget, and optimizer interface as SR-MAPPO; only the frozen SR stability groups are disabled |
| PPO | `ippo_mobile` | independent role-local PPO, exposed as PPO in thesis output; shared UAV actor/local critic and separate vehicle actor/local critic, with no centralized critic input |
| MADDPG | `maddpg_mobile` | separate discrete role actors, centralized role Q critics, target networks, replay, and straight-through masked Gumbel-Softmax during actor updates |
| IQL | `iql_mobile` | shared UAV Q network and separate vehicle Q network, role-local observations, masked $\varepsilon$-greedy actions, replay, and target networks |

`ippo_mobile` is the unambiguous code identifier because PPO is applied
independently to multiple decentralized agents. Figures and prose may label it
"PPO (IPPO implementation)" on first use and "PPO" thereafter.

For MADDPG, stored behavior masks are applied before both environment sampling
and differentiable action relaxation. Actor gradients cannot create mass on
illegal actions. Each role critic receives the structured global state and
joint one-hot/relaxed actions; the UAV actor/critic parameters are shared
across UAV identities without being shared with the vehicle.

For IQL, unavailable actions have `-inf` selection score and are excluded from
the bootstrap maximum. The UAV and vehicle networks, optimizers, target
networks, replay rows, exploration schedules, and checkpoint sections are
role-specific. Team reward is used consistently with the cooperative task.

### Fairness Across Different Learning Families

All five methods receive the same environment transitions, episode horizon,
training scenes, training seeds, observations available to their declared
execution policy, action masks, reward, and evaluation scenarios. Neural
capacity is matched by declared hidden width and depth where architectures are
comparable. Because on-policy and replay algorithms cannot have identical
gradient semantics, fairness is reported in three budgets:

1. environment interactions, the primary training budget;
2. optimizer updates and trainable parameter count;
3. wall-clock and decision runtime, reported rather than forced equal.

No baseline may receive future demand, hidden pest state, or an unmasked action
unless that information is also available to SR-MAPPO. Algorithm-specific
hyperparameters may differ only through the frozen, equally budgeted tuning
procedure.

## Required Problem-2 and Heuristic Methods

The required Problem-2 family remains:

- `sr_mappo_mobile`;
- `sr_mappo_fixed`;
- `sr_mappo_astar`;
- `mappo_mobile`;
- `sr_mappo_two_stage`.

`sr_mappo_fixed` is a resource-matched causal control, not a heuristic.
`sr_mappo_two_stage` first trains the UAV policy with the frozen support
controller and then trains/adapts the vehicle stage under a frozen, explicitly
versioned schedule. The two stages together receive the same total environment
interaction budget as the joint method.

The classical comparison asks whether the learned vehicle policy adds value
over auditable dispatch logic while retaining the same SR-MAPPO UAV learning
interface. It includes:

- `sr_mappo_astar`: urgency-aware rolling A* with service feasibility;
- `sr_mappo_nearest`: nearest feasible pending request by road distance;
- `sr_mappo_urgency`: waiting-time and pesticide-endurance priority dispatch.

Each hybrid trains its UAV policy against its own frozen vehicle controller;
the vehicle has no optimizer. All controllers use only current observable
requests and road state. A* path lengths must match Dijkstra on test graphs,
tie-breaking must be deterministic, replan frequency must be frozen, and
decision runtime must be logged. The resulting conclusion is limited to the
vehicle-control comparison; it is not a claim against every possible fully
hand-engineered spraying system.

## Experiment Families and Deduplication

G5 registers six experiment families:

| Family | Required conditions | Main question |
|---|---|---|
| `algorithm_convergence` | five learning algorithms | convergence speed and stability under equal interaction budgets |
| `algorithm_scale` | five learning algorithms x six scales | endpoint scalability |
| `problem2_required` | five required Problem-2 methods x six scales | mobility, joint learning, same-source stability, and two-stage effects |
| `vehicle_heuristics` | SR-MAPPO mobile plus A*, nearest, and urgency hybrids | learned versus classical vehicle control |
| `sr_mappo_ablation` | full SR-MAPPO plus five remove-one variants | contribution of SR stability groups |
| `sr_mappo_sensitivity` | frozen algorithmic and mechanism axes | parameter robustness and operating boundaries |

The base five-algorithm six-scale matrix contains `5 x 6 x 5 = 150` formal
training jobs in G6. Shared jobs, such as `sr_mappo_mobile` and
`mappo_mobile`, are referenced by multiple families and executed once.

The existing base job identity remains:

```text
method|scale|training_seed|config_hash|git_commit
```

G5 adds a full experiment identity containing `family`, `condition_id`, and
`protocol_hash`. A family manifest points to the canonical base job when the
scientific configuration is identical. Deduplication is allowed only when all
base identity fields and the checkpoint-selection protocol match exactly.

The heuristic family uses all six frozen scales. After cross-family
deduplication, the formal training workload is exactly `375` unique jobs:

```text
150 base five-algorithm jobs
+ 90 fixed/A*/two-stage Problem-2 jobs
+ 60 nearest/urgency heuristic jobs
+ 25 remove-one ablation jobs
+ 50 noncenter algorithmic-sensitivity jobs
= 375 unique training jobs
```

## Convergence and Stability Contract

Checkpoints are emitted on an equal environment-interaction schedule. At each
scheduled point, deterministic evaluation uses the same frozen validation
panel and frozen normalization state. Training reward is plotted only as a
diagnostic.

Pre-registered convergence summaries are:

- validation reduction-rate area under the learning curve, normalized by the
  common maximum interaction budget;
- earliest interaction count at which mean reduction rate reaches the `0.85`
  success threshold;
- restricted mean time to threshold when a run never reaches the threshold;
- final-window reduction mean and within-run standard deviation;
- across-training-seed median, interquartile range, and standard deviation at
  every scheduled checkpoint;
- invalid-update, NaN/Inf, gradient-clipping, action-mask rejection, and
  catastrophic-regression counts.

Interpolation between checkpoints is prohibited for time-to-threshold.
Unreached thresholds are right-censored at the frozen budget rather than
deleted. Curve summaries are validation evidence; final endpoint claims use
G7 sealed scenarios.

Area under the learning curve uses trapezoidal integration over the frozen
checkpoint grid and is divided by the common maximum interaction budget. The
final window is the last 20% of scheduled checkpoints. A catastrophic
regression is a drop of at least `0.10` reduction-rate units from the run's
previous best validation checkpoint; the threshold is not changed per method.

## Formal Metric Semantics

G5 closes the metric ambiguity before pilots:

- `rendezvous_distance_m` is the shortest feasible road-network route length
  from the support location at reservation to the selected service road node;
  it is not G4's Euclidean service-start separation;
- `vehicle_service_travel_m` is the actual road distance traveled for service,
  including replanning detours;
- `waiting_steps` is total per-request waiting exposure accumulated while a
  request is pending or reserved, including exposure from unresolved requests
  through the terminal step;
- `completed_request_waiting_steps` separately records creation-to-service
  start waiting for requests that actually start service;
- `pesticide_disabled_steps` is the sum of UAV-time steps in which a UAV cannot
  execute a positive spray because usable onboard pesticide is insufficient;
- `return_steps` is the sum of UAV-time steps spent following the declared
  rendezvous/return behavior rather than treating the pest field;
- `effective_spray_steps` counts legal spray actions that apply a positive
  pesticide amount to the field;
- `decision_runtime_s` uses synchronized wall-clock timing around policy or
  heuristic decision computation only, excluding environment advancement and
  file I/O.

Unreachable requests, unresolved terminal waits, partial service, and zero
transfer are explicit event outcomes rather than missing values. The G1 raw
and validated schemas are versioned in G5 to carry these meanings and any new
fields; old G4 field names are never silently reinterpreted.

## SR-MAPPO Remove-One Ablation

The full configuration is compared with exactly five remove-one conditions:

1. `no_observation_normalization`;
2. `no_return_normalization`;
3. `no_network_stabilization`, disabling orthogonal initialization and layer
   normalization as one pre-registered group;
4. `no_robust_value_update`, disabling value clipping and Huber value loss as
   one group;
5. `no_learning_rate_decay`.

All other flags, seeds, budgets, checkpoints, scenarios, and environment
parameters must match the full method. Configuration-diff validation rejects
any undeclared difference. No combinatorial ablation is required.

## Sensitivity Contract

Sensitivity is one-factor-at-a-time around the frozen primary configuration.
The center point is deduplicated with the primary job.

Algorithmic training sensitivity uses the representative scale
`g30x30_d3`, all five formal training seeds in G6, and these levels:

| Axis | Levels |
|---|---|
| learning rate | `1e-4`, `3e-4`, `5e-4` |
| PPO clipping radius ($\epsilon_{\mathrm{clip}}$) | `0.10`, `0.20`, `0.30` |
| entropy coefficient | `0.005`, `0.010`, `0.020` |
| discount factor | `0.95`, `0.99`, `0.995` |
| GAE trace parameter ($\lambda$) | `0.90`, `0.95`, `0.98` |

Mechanism sensitivity evaluates the fixed nominal SR-MAPPO checkpoints without
retraining at `g30x30_d3`. The primary comparison starts each UAV with
`0.2875 L` usable pesticide, the center of the accepted G4 activation band;
the physical tank capacity remains `1.2 L` with a `1.08 L` usable capacity.
This deliberately scarce starting load is a frozen simulation condition, not
an equipment-capacity claim. Mechanism sensitivity uses the G1 engineering
bounds and center values:

| Axis | Levels and unit |
|---|---|
| initial onboard pesticide | `0.05`, `0.2875`, `0.525 L` from the accepted G4 activation band |
| vehicle speed | `4`, `8`, `12 m/s` |
| transfer rate | `2`, `4`, `8 L/min` |
| setup time | `5`, `10`, `30 s` |
| rendezvous radius | `5`, `15`, `30 m` |

The onboard-pesticide levels are explicitly simulation mechanism levels, not
empirical equipment capacities. Road-detour ratio is analyzed by frozen
scenario strata rather than by editing OSM topology. Sensitivity results are
trend and boundary evidence; they cannot be used after G7 unlock to select a
new primary configuration.

## Pilot and Validation-Tuning Sequence

The sequence is fixed:

1. unit and integration smoke tests with development-only IDs;
2. short end-to-end smoke for every method and condition type;
3. development pilots on `g20x20_d2` and `g30x50_d4` to expose small/large
   scale failures;
4. freeze candidate hyperparameter sets and the tuning selection rule;
5. equally budgeted tuning on validation scenarios `20000-20049`;
6. rerun selected configurations on the development pilot matrix;
7. freeze methods, configurations, statistics, checkpoint selection, and all
   G6/G7 manifests.

Development pilot training seeds are `51001`, `51002`, and `51003`; development
scenario IDs are `10000-10019`. These IDs are added to the seed registry and
must not overlap training, validation, or sealed identities. Formal training
seeds remain `42`, `123`, `2024`, `3407`, and `7919`.

Each of the five learning algorithms receives four pre-registered tuning
candidates, identical pilot training seeds, identical validation scenarios,
and equal environment interactions. Candidate manifests are hashed before the
first validation evaluation. The selected candidate maximizes mean validation
reduction rate; ties are resolved by success probability, then lower
interaction count, then lexicographically smaller configuration hash. No
candidate is created or edited after validation results are inspected.

The final training budget and checkpoint interval are chosen from development
runtime/resource measurements through a rule recorded before validation. G5
acceptance requires exact numeric values in the frozen protocol; G6 cannot
begin while either remains implicit.

## Statistical Freeze

The training seed is the independent replication level and scenario is the
paired within-seed level. Point estimates average scenario-level paired
differences within training seed and then summarize across seeds.

The locked inference procedure uses `10,000` hierarchical paired-bootstrap
replicates with RNG seed `20260822`:

1. resample the five matched training seeds;
2. within each selected seed, resample shared scenario IDs;
3. compute the paired method difference;
4. report the observed difference and percentile 95% interval.

For Holm adjustment, the unadjusted two-sided bootstrap tail probability is
computed as

$$
p = \min\!\left\{
1,
2\min\!\left[
\frac{1 + \#\{\Delta_b \le 0\}}{B+1},
\frac{1 + \#\{\Delta_b \ge 0\}}{B+1}
\right]
\right\},
$$

where $B=10{,}000$ and $\Delta_b$ is bootstrap replicate $b$. The estimate,
interval, and practical margin remain primary for interpretation; the adjusted
tail probability is not reported alone.

Primary outcomes are reduction rate and the probability of reaching the
`0.85` reduction threshold. Design-level practical-equivalence margins are
`0.02` reduction-rate units and `0.05` success-probability units. These are
simulation interpretation margins, not externally validated agronomic
minimum-important differences.

A result is called practically equivalent only when the complete 95% interval
lies inside the corresponding symmetric margin. An interval entirely above or
below the margin supports a practically directional difference. All other
cases are inconclusive with respect to practical equivalence.

Holm correction is applied separately to pre-registered confirmatory families:

- SR-MAPPO versus MAPPO, PPO, MADDPG, and IQL across six scales and two primary
  outcomes;
- mobile versus fixed, A*, and two-stage SR-MAPPO across six scales and two
  primary outcomes; the SR-MAPPO/MAPPO result is referenced from the first
  family rather than tested twice;
- SR-MAPPO versus nearest and urgency heuristics across all six frozen scales
  and two primary outcomes;
- full SR-MAPPO versus five remove-one variants at `g30x30_d3` for two primary
  outcomes.

The mobility mechanism chain is secondary confirmatory evidence for the
mobile-versus-fixed comparison. Holm correction is applied to its four
pre-registered intermediate contrasts: rendezvous distance, waiting exposure,
pesticide-disabled time, and effective spray time. Reduction and success are
referenced from the primary mobile-versus-fixed family rather than tested a
second time. Sensitivity trends, runtime, additional mechanism metrics, and
post hoc diagnostics are exploratory and labeled as such.

Runs are excluded only for pre-registered technical invalidity: identity/hash
mismatch, non-finite output, corrupt/truncated artifact, impossible resource
conservation, wrong scenario partition, incomplete horizon without a valid
termination reason, or failed deterministic replay. Poor performance, long
waiting, failure to reach 0.85, or an unfavorable method ranking is never an
exclusion reason. A technical failure is retried under the identical identity.

## Planned Repository Architecture

G5 implementation is confined to the authoritative repository and uses the
following ownership boundaries:

```text
src/problem2/
  algorithms/
    protocol.py
    common/
    sr_mappo/
    mappo/
    ippo/
    maddpg/
    iql/
  heuristics/
  training/
  evaluation/
  experiments/
  statistics/
configs/problem2/g5/
docs/evidence/g5/
scripts/
tests/g5/
outputs/problem2_sr_mappo_v1/g5/
```

The current `src/problem2/algorithms/sr_mappo` implementation is extended
rather than duplicated. Shared code owns masks, network blocks, replay/rollout
schemas, RNG state, checkpoint serialization, run identity, metrics, and
validators. Each algorithm package owns only method-specific networks and
updates. Experiment-family configuration is data, not branches of copied
training scripts.

All G6 and G7 executables, including job generation, resume, deterministic
evaluation, long-table validation, hierarchical bootstrap, Holm correction,
and sealed-lock enforcement, must be implemented and tested in G5. Later gates
execute frozen code only.

## Checkpoint, Logging, and Failure Contract

Every checkpoint is written to a temporary file, flushed, hashed, and renamed
atomically. It contains, as applicable:

- UAV and vehicle online networks;
- centralized, local-value, or Q critics;
- optimizers and learning-rate schedulers;
- target networks and target-update counters;
- observation/return normalization states and versions;
- rollout position or replay-buffer content/index;
- exploration and Gumbel-temperature state;
- episode, interaction, update, and checkpoint counters;
- Python, NumPy, CPU Torch, and CUDA RNG states;
- configuration, protocol, source commit, and source-bundle hashes.

Raw logs use the G1 episode schema extended with experiment family,
condition, checkpoint ID, partition, environment-interaction count, and direct
mechanism mediators. Validators reject duplicate identities, schema drift,
nonmonotonic counters, stale hashes, non-finite values, illegal actions,
resource mismatch, wrong partitions, or missing terminal records.

## Verification Requirements

G5 must provide tests for:

- every algorithm's UAV and vehicle observation/action/mask paths;
- role-parameter and optimizer isolation;
- PPO masked log-prob replay and GAE gold cases;
- MADDPG masked discrete relaxation, actor gradients, targets, and replay;
- IQL masked bootstrap, $\varepsilon$-greedy behavior, targets, and replay;
- deterministic evaluation with byte-identical normalization/exploration
  states;
- full checkpoint round trips and interrupted-run equivalence for all methods;
- A* versus Dijkstra, deterministic ties, feasibility, and no future leakage;
- exact remove-one configuration diffs;
- sensitivity one-factor-only diffs;
- experiment-job deduplication and complete matrix counts;
- statistics on hand-computable paired fixtures, bootstrap reproducibility,
  and Holm correction;
- sealed-test denial in every G5 executable;
- output-root confinement and protected-asset preservation.

Each algorithm must complete an end-to-end CPU smoke. CUDA preflight and one
bounded GPU smoke must pass on the available 8 GB RTX 4060 Laptop GPU without
silently changing scientific configuration.

## G5 Deliverables

G5 produces:

- G4 lineage-reconciliation report;
- Problem-1 source-lineage registry;
- method and heterogeneous-interface registries;
- fairness matrix and configuration-diff reports;
- experiment-family, condition, seed, budget, and job manifests;
- heuristic, ablation, and sensitivity manifests;
- checkpoint-selection and validation-tuning contract;
- statistical estimand, multiplicity, exclusion, and equivalence contract;
- pilot raw logs, validated pilot long tables, audit reports, and manifests;
- frozen G6 training-job and validation-evaluation manifests;
- frozen G7 sealed-evaluation and analysis manifests without accessing any
  sealed scenario;
- `HANDOFFG5.md` and a project-state persistence record.

## Acceptance and Transition to G6

G5 passes only when all of the following are true:

1. G4 lineage discrepancies are resolved and pushed.
2. All five algorithms and both roles pass the shared acceptance suite.
3. All required Problem-2, heuristic, ablation, and sensitivity paths complete
   bounded pilots with finite, validated artifacts.
4. Validation candidates were frozen before validation access and received
   equal declared budgets.
5. Final method, budget, checkpoint, statistics, exclusion, and manifest files
   contain exact values and immutable hashes.
6. The sealed lock remains actual count `0`; no sealed scenario was opened.
7. The full test suite, compile checks, registry audits, artifact audits, and
   clean-source checks pass on the frozen commit.
8. Content and persistence commits are pushed and recorded in
   `docs/PROJECT_STATE.md`.

G5 may establish M3 pilot evidence if the pilot matrix is complete, but it
cannot establish a formal ranking. Any later scientific-code, configuration,
estimand, exclusion, or checkpoint-selection change invalidates the freeze and
returns the project to G5 before G6 can continue.
