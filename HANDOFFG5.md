# HANDOFF G5

Date: 2026-08-22
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g5-pilot-freeze`
Current HEAD: `877c4660d17f5c14451b83727248d67f70a2b8d4`
Remote: `origin/codex/problem2-g5-pilot-freeze`

## Read This First

This document is a self-contained handoff for a new conversation with no
prior context. Read it together with `docs/PROJECT_STATE.md` before making
changes. The authoritative project is the `Second` repository above.

The current state is **G4 accepted at M2; G5 has only a written design and has
not started implementation**. The next authorized work is:

1. obtain/confirm the user's review and approval of the three written G5-G7
   specifications;
2. use the `writing-plans` workflow to write the separate executable G5
   implementation plan;
3. execute that plan only after the plan exists and is reviewed as required.

Do not start G6 formal jobs, do not access validation or sealed scenarios, and
do not claim that any method is superior. Do not assume that the old G4
handoff's source-commit narrative is correct; the discrepancy below is a hard
G5 entry blocker.

## Project Identity and Non-Negotiable Rules

- Scientific problem: road-constrained air-ground heterogeneous cooperative
  pesticide spraying with a mobile pesticide replenishment vehicle.
- Public flagship algorithm name: **SR-MAPPO**.
- Problem 2 wording: the air-ground heterogeneous extension of SR-MAPPO.
- Forbidden public algorithm names: HAPPO and `AG-SR-MAPPO`.
- Replenished resource: pesticide only.
- Battery replenishment: inactive unless a separate activation audit is passed
  and recorded; no such activation exists now.
- OSM/GraphML roads: offline simulation input for road-constrained modeling,
  not evidence of real field deployment.
- Protected first-problem repository:
  `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`.
- Protected base project and OSM inputs: `D:/Pycharm/Locust_rl`.
- Protected planning evidence:
  `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析`.
- Do not modify external Word files unless explicitly requested.
- All Problem-2 output evidence belongs below
  `outputs/problem2_sr_mappo_v1`.
- Preserve user changes in protected repositories. Never force-push or reset
  unrelated work.

## Maturity and Claim Boundary

Current highest maturity is `M2`: implementation and scoped mechanism evidence.
The following wording is currently permitted:

- G2/G3 implementation tests verify deterministic and heterogeneous MARL
  interfaces and invariants.
- G4 diagnostic support probes exercised the frozen onboard-pesticide scarcity
  mechanism and emitted paired descriptive deltas.
- The G5-G7 workflow is designed and specifies later pilots and experiments.

The following claims are not permitted yet:

- mobile support improves treatment;
- SR-MAPPO outperforms MAPPO, PPO, MADDPG, IQL, A*, or any heuristic;
- formal experiments show a result;
- a result is statistically significant or deployment-verified;
- the simulation demonstrates real agricultural deployment;
- any method is universally optimal.

Maturity rules remain:

| Level | Evidence | Permitted result wording |
|---|---|---|
| M0 | concept only | planned/proposed |
| M1 | frozen specification | design completed |
| M2 | implementation plus tests | implementation verified |
| M3 | independent multi-seed pilot | pilot results indicate |
| M4 | frozen formal matrix and sealed paired evidence | formal experiments show, within stated scope |

## Completed Gates

### G0/G1: repository isolation and evidence registration

`Second` is the authoritative repository. G1 registered parameter, literature,
experiment, scenario, job-identity, raw-table, validated-table,
artifact-manifest, sealed-lock, and output-root contracts under
`docs/evidence/g1/`. Candidate code from
`origin/feature/problem2-code-framework` was audited read-only and was not
accepted automatically.

Important frozen registries:

- formal methods in the original G1 matrix:
  `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`,
  `sr_mappo_two_stage`;
- training seeds: `42`, `123`, `2024`, `3407`, `7919`;
- validation scenario IDs: `20000-20049`, tuning/checkpoint selection allowed;
- sealed scenario IDs: `30000-30099`, tuning forbidden and locked;
- job identity serialization:
  `method|scale|training_seed|config_hash|git_commit`, hashed with SHA-256;
- sealed lock: maximum unlock count `1`, actual unlock count `0`, unlock gate
  `G7`.

### G2: deterministic physical foundation

G2 validates offline GraphML loading, metric projection, road rasterization,
four-connected topology, physical motion, service state transitions, resource
ledger conservation, deterministic replay, and artifact provenance.

Key G2 values:

- source GraphML SHA-256:
  `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`;
- projection: `EPSG:4326` to `EPSG:32643`;
- physical step: `1.0 s`;
- UAV speed: `5.0 m/s`;
- vehicle speed: `8.0 m/s`;
- UAV nominal capacity: `1.2 L`;
- usable fraction: `0.9`;
- usable UAV capacity/service cap: `1.08 L`;
- spray flow: `1.2 L/min`;
- vehicle pesticide inventory: `20.0 L`;
- transfer rate: `4.0 L/min`;
- setup time: `10.0 s`;
- request margin: `10.0 s`;
- rendezvous radius: `15.0 m`;
- battery replenishment: `false`.

G2 scale/horizon protocol:

| Scale | Maximum physical decision steps |
|---|---:|
| `g20x20_d2` | 150 |
| `g20x30_d3` | 180 |
| `g20x40_d3` | 220 |
| `g30x30_d3` | 220 |
| `g30x40_d4` | 280 |
| `g30x50_d4` | 350 |

G2 verification recorded in project state: `python -m pytest tests/g2 -q`
returned `102 passed`; full historical regression returned `158 passed` at
the G2 checkpoint; compile and deterministic road/audit checks passed.

### G3: heterogeneous MARL interface

G3 passed at M2. The current verified interface is:

- `N=2` homogeneous UAVs sharing one UAV actor;
- one separate vehicle actor;
- structured centralized team critic during training;
- UAV observation dimension `179`;
- vehicle observation dimension `28`;
- critic state dimension `185`;
- UAV actions: `up`, `down`, `left`, `right`, `stay`, `spray`;
- vehicle action contract: `hold` plus candidate slots `slot-0..slot-3`;
- exact stored masks and old masked log-probabilities;
- team GAE and valid-sample filtering;
- role-separated normalization and frozen evaluation statistics;
- checkpoint round trip including optimizer/scheduler/RNG state.

G3 config SHA-256:
`421eff64d1161f78c9029dfc6d133b9b66247f3cf905b9577e55965584195f93`.
Implementation commit bound to the canonical smoke:
`092b7f3e965a24979bac65c8304cd9d7dc142f73`.
G3 acceptance was `17/17`; `python -m pytest tests/g3 -q` returned
`63 passed`; full historical regression returned `221 passed` at the G3
checkpoint.

The G3 smoke is engineering evidence only. It is not a treatment pilot or
formal endpoint result.

### G4: onboard-pesticide scarcity diagnostic

G4 passed at M2 as a diagnostic support-probe mechanism gate. It used:

- scarcity axis `initial_uav_pesticide_l` at `0.05`, `0.2875`, and `0.525 L`;
- fixed vehicle inventory `20.0 L`, not a vehicle-inventory scarcity sweep;
- `fixed_support_probe` versus `mobile_support_probe`;
- probe scales `g20x20_d2`, `g20x30_d3`, `g30x30_d3`;
- probe seeds `42`, `123`, `2024`;
- no G3 actor/checkpoint execution;
- no validation or sealed scenario access;
- waiting metric `started_service_waiting_time_s` for requests reaching service
  start;
- distance metric `euclidean_service_start_distance_m`, explicitly not road
  route distance.

Canonical output root:
`outputs/problem2_sr_mappo_v1/g4`.
The accepted diagnostic claim is only mechanism activation and paired
descriptive deltas under G2 semantics.

## G4 Entry Reconciliation Blocker

The old G4 handoff and parts of `docs/PROJECT_STATE.md` contain inconsistent
source identifiers. Do not silently choose one identifier.

Observed facts on the current Git history:

- short hash `4e81567` resolves to
  `4e8156712986a28f81315968fd7640b6e7ed5ad6`;
- the recorded string
  `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5` is not a Git object;
- the canonical G4 `outputs/.../g4/provenance.json` currently binds source
  commit `09d361994100741a9ae834b63ba07c9b5db953e7` and source tree
  `5a61825001e92fae112579ae05f5c778deedcab3`;
- the G4 handoff instead names generator commit
  `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` and source tree
  `78d3d146b06f191998853ef7070b167a5df64a5c`;
- `ee0d3faf...` is an existing Git commit, but that alone does not prove it
  generated the canonical output.

**Required G5 first action:** audit the source bundle, provenance, artifact
manifest, G4 contract, handoff, and Git trees; determine the true generator
for the accepted artifacts; then either correct the narrative to the actual
provenance or regenerate the bundle from the intended clean generator. Produce
one exact commit/tree/file-hash/bundle-hash tuple across all records. Commit,
push, and record the reconciliation before any G5 pilot is accepted.

## Written G5-G7 Design Already Persisted

The three specifications were authored and pushed for user review. They are
design artifacts, not an implementation pass and not a G5 plan.

| Specification | SHA-256 | Scope |
|---|---|---|
| `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md` | `1F6C4A8ECC90D63D9D81A0858286F555BA3E3365342A26BF77423E72C53EC0FD` | algorithms, baselines, pilots, freezes, statistics |
| `docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md` | `958975DAA4F8875DFC59280B5B4A03A1F11AD922683A4CCCC7FA45F48CB11B20` | immutable formal jobs, recovery, validation, checkpoint selection |
| `docs/superpowers/specs/2026-08-22-g7-sealed-analysis-design.md` | `CD6BC6EE8F7A2BFE9C2ED6829CEFC36B813558B2FA8FAF9BFAFAED5A2E276005` | one-time sealed unlock, paired statistics, mechanism audit |

Design content commit:
`a12cbdd0bf479d93bd1788497d82447313933d39`.
State persistence commit:
`877c4660d17f5c14451b83727248d67f70a2b8d4`.
Both were pushed to `origin/codex/problem2-g5-pilot-freeze`.

The user has not yet explicitly approved the written specifications in this
handoff context. A new conversation should ask for that review before invoking
`writing-plans` or writing `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`.

## G5 Frozen Design Intent

### Five algorithms: all explicitly heterogeneous

Every algorithm must support both UAVs and the vehicle. Heterogeneous action
spaces are not special handling reserved only for MADDPG/IQL.

| Public name | Code method ID | Required role handling |
|---|---|---|
| SR-MAPPO | `sr_mappo_mobile` | shared UAV actor, separate vehicle actor, structured centralized value critic, PPO/GAE, SR stability groups enabled |
| MAPPO | `mappo_mobile` | same heterogeneous source framework; only declared SR stability groups disabled |
| PPO | `ippo_mobile` | independent role-local PPO actors/critics; no centralized critic state in actors |
| MADDPG | `maddpg_mobile` | separate role actors, centralized role Q critics, target networks, replay, masked discrete relaxation |
| IQL | `iql_mobile` | separate role Q networks, role-local masked epsilon-greedy behavior, replay, target networks |

All five share environment transitions, observations, masks, reward, physical
horizon, training/evaluation scenario identities, and declared interaction
budget. Their method-specific update mathematics may differ, but no method may
receive future demand, hidden pest state, or illegal unmasked actions.

Problem 1 is lineage only. The first-problem source commit is
`1ca9e5ccc5f77ed775cd2b607dd70d635720accf`; current dirty user changes there
are protected. G5 must register source paths and blob IDs, inherit tested
mathematics where appropriate, and implement a controlled Problem-2 extension
inside `Second`. No first-problem runtime import, checkpoint, log, result, or
output is admissible as Problem-2 evidence.

### Required Problem-2 comparison family

The primary five-condition family is:

1. `sr_mappo_mobile`;
2. `sr_mappo_fixed`;
3. `sr_mappo_astar`;
4. `mappo_mobile`;
5. `sr_mappo_two_stage`.

`sr_mappo_fixed` is a resource-matched stationary causal control, not a
heuristic. `sr_mappo_astar` retains the learned UAV policy and uses a rolling,
road-constrained A* vehicle controller. `sr_mappo_two_stage` uses a frozen,
versioned two-stage schedule with the same total interaction budget as joint
training.

Recommended classical vehicle controllers are:

- rolling A* with urgency and service feasibility;
- nearest feasible request by road distance;
- urgency/waiting/pesticide-endurance priority dispatch.

All heuristic policies must use current observable state only, deterministic
tie-breaking, frozen replan rules, and no future information. A* route lengths
must agree with Dijkstra on test graphs.

### Experiment families

G5 must implement and test support for:

1. five-algorithm convergence speed and stability;
2. five-algorithm six-scale endpoint comparison;
3. the required Problem-2 family above;
4. SR-MAPPO versus classical heuristics;
5. full SR-MAPPO versus five remove-one stability groups;
6. algorithmic and mechanism sensitivity/boundary analysis.

Remove-one conditions are exactly:

- no observation normalization;
- no return normalization;
- no network stabilization (orthogonal initialization and layer normalization
  together);
- no robust value update (value clipping and Huber value loss together);
- no learning-rate decay.

Sensitivity center is deduplicated with the primary job. Algorithmic axes use
`g30x30_d3` and the five formal training seeds. Mechanism axes use frozen
nominal checkpoints and registered levels for initial onboard pesticide,
vehicle speed, transfer rate, setup time, and rendezvous radius. Sensitivity
cannot select a new primary configuration after sealed access.

### Exact G5/G6/G7 workload declared by the design

The written design declares this deduplicated formal training count:

```text
150 base five-algorithm jobs
+ 90 fixed/A*/two-stage Problem-2 jobs
+ 60 nearest/urgency heuristic jobs
+ 25 remove-one ablation jobs
+ 50 noncenter algorithmic-sensitivity jobs
= 375 unique training jobs
```

G7 declares `42,500` unique sealed episode rows after deduplication:

- `37,500` nominal rows from `375` trained cells x `100` sealed scenarios;
- `5,000` mechanism-sensitivity rows from ten noncenter conditions across
  five nominal SR-MAPPO checkpoints and `100` scenarios.

These counts are design assertions that G5 code must generate and audit. They
are not completed experiment results.

### Statistics and evidence chain

Primary outcomes:

- reduction rate;
- probability of `reduction_rate >= 0.85`.

Training seed is the independent replication level. Scenarios are paired
within seed, not independent training replications. The locked design uses
10,000 hierarchical paired-bootstrap replicates with RNG seed `20260822`:
resample training seeds, then shared scenarios within selected seeds. Report
observed paired differences and percentile 95% intervals.

Practical-equivalence margins:

- `0.02` reduction-rate units;
- `0.05` success-probability units.

Holm correction is pre-registered by comparison family. Technical exclusions
are limited to identity/hash mismatch, non-finite/corrupt/truncated artifacts,
wrong partitions, impossible conservation, invalid termination, or failed
deterministic replay. Poor performance, failure to reach 0.85, or an
unfavorable ranking is never an exclusion reason.

Evidence must flow only as:

```text
source parameter/literature
-> frozen configuration and Git commit
-> run ID and raw episode log
-> validated long-format table
-> paired statistical summary
-> figure/table artifact manifest
-> thesis statement
```

## G5 Gate Work Packages

The G5 implementation plan must decompose at least these packages:

1. reconcile G4 provenance and write the reconciliation audit;
2. register first-problem lineage with source commit/blob IDs;
3. extend shared algorithm protocols and role-specific observation/action/mask
   handling;
4. implement/adapt all five algorithm families with role-specific networks,
   optimizers, replay/rollout transitions, target networks where needed, and
   checkpoints;
5. implement fixed support, rolling A*, nearest, urgency, and two-stage
   controllers with tests;
6. implement shared job identity, config hashing, matrix generation,
   deduplication, atomic checkpointing, recovery, and output-root confinement;
7. implement raw episode, validated long-table, metric-semantic, and artifact
   validators;
8. implement convergence/stability summaries, ablation flags, sensitivity
   matrices, hierarchical bootstrap, Holm correction, and negative-result
   diagnostics;
9. run development-only smoke tests, then small/largest-scale pilots;
10. freeze validation tuning rules and run validation scenarios only after
    candidate configs and tie-break rules are hashed;
11. freeze all G6/G7 manifests without sealed access;
12. produce `HANDOFFG5.md` update, gate report, commit, push, and state record.

## G5 Pilot Protocol

The written design declares this order:

1. unit/integration smoke for every method and condition;
2. short end-to-end smoke;
3. development pilots on `g20x20_d2` and `g30x50_d4`;
4. freeze candidate configurations and tuning rule;
5. validation tuning on `20000-20049` with sealed access disabled;
6. rerun selected configurations on the development pilot matrix;
7. freeze code, methods, configs, checkpoint selection, statistics,
   exclusions, manifests, and hashes.

Development-only pilot IDs in the design are training seeds `51001`, `51002`,
`51003` and scenario IDs `10000-10019`. They must be registered as disjoint
from formal training, validation, and sealed IDs. Formal seeds remain
`42, 123, 2024, 3407, 7919`.

G5 may produce M3 pilot evidence only if the complete independent pilot and
its evidence chain pass. It cannot produce formal sealed conclusions.

## Planned Repository Ownership

The design proposes these G5 ownership boundaries:

```text
src/problem2/
  algorithms/protocol.py
  algorithms/common/
  algorithms/sr_mappo/
  algorithms/mappo/
  algorithms/ippo/
  algorithms/maddpg/
  algorithms/iql/
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

Existing G2/G3/G4 code remains the base. Extend it in place where the tested
contracts already exist; do not duplicate five training scripts or import the
protected first-problem project at runtime.

## Required Verification Before G5 Acceptance

At minimum, test:

- all five algorithms with both role observations, actions, masks, updates,
  and checkpoints;
- gradient/optimizer isolation and critic-information isolation;
- masked log-prob replay, GAE, normalization freeze, and checkpoint round trip;
- MADDPG masked discrete relaxation, target/replay behavior;
- IQL masked bootstrap, epsilon-greedy behavior, target/replay behavior;
- heuristic A* versus Dijkstra, deterministic ties, feasibility, and no future
  leakage;
- exact ablation and one-factor sensitivity diffs;
- job matrix count `375`, dependency references, and no unsafe deduplication;
- atomic interrupted-run resume equivalence;
- raw/validated schema, metric semantics, conservation, partition, hash, and
  artifact audits;
- bootstrap reproducibility and Holm correction on hand-computable fixtures;
- sealed-test denial in every G5 executable;
- source cleanliness and protected-asset preservation.

Before claiming G5 complete, run at least:

```powershell
python -m pytest -q
python -m compileall -q src scripts
git diff --check
```

Also run the new G5 registry/job/algorithm/audit CLIs and record their exact
outputs. A passing pre-existing test suite alone does not pass G5.

## G5 Acceptance and G6 Transition

G5 passes only when:

1. G4 lineage is reconciled and pushed;
2. all five algorithms and both roles pass the shared acceptance suite;
3. Problem-2, heuristic, ablation, and sensitivity paths complete bounded
   pilots with finite validated artifacts;
4. validation candidates and selection rules were frozen before validation
   access;
5. code, configs, methods, checkpoint selection, statistics, exclusions, and
   G6/G7 manifests have immutable hashes;
6. sealed lock remains actual count `0` and no sealed scenario was accessed;
7. full tests, compile checks, audits, and clean-source checks pass;
8. content and persistence commits are pushed and recorded in
   `docs/PROJECT_STATE.md`.

Any scientific code, configuration, estimator, exclusion, or checkpoint rule
change after a freeze returns the project to G5 and invalidates dependent G6
manifests.

## Current Unfinished Work

- G4 provenance/hash discrepancy has not been reconciled.
- User review/approval of the three written G5-G7 specifications is pending.
- The separate executable G5 implementation plan does not yet exist.
- The five new algorithm implementations (PPO/IPPO, MADDPG, IQL, and the
  complete cross-method experiment adapters) are not yet implemented in this
  branch.
- Heuristic, ablation, sensitivity, job orchestration, formal validation, and
  paired-statistics code are not yet accepted.
- No formal second-problem raw logs, validated tables, paired statistics, or
  locked figures exist.
- Engineering parameter source records remain provisional/pending where noted
  in the G1 registry.

## Immediate Next Action for a New Conversation

1. Read this file, `docs/PROJECT_STATE.md`, and the three linked G5-G7 specs.
2. Confirm whether the user approves the written specifications or requests
   edits.
3. If approved, invoke `writing-plans` and author the separate executable
   G5 plan at:
   `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`.
4. Do not write implementation code until that plan and its review gate are
   complete.
5. Start implementation with G4 lineage reconciliation, not with formal
   training.

## Persistence of This Handoff

This handoff must be committed and pushed as its own content commit. Then
`docs/PROJECT_STATE.md` must record its path, commit, verification, and remote
hash in a second persistence commit. Do not report the handoff as persisted
until both checks are complete.
