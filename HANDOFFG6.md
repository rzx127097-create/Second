# HANDOFF G5 -> TASK 6

Date: 2026-08-25
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g5-pilot-freeze`
Remote: `origin/codex/problem2-g5-pilot-freeze`
Current local/upstream/remote HEAD: `59877f6b440da53b83647a6715390a02c6e06372`
Current gate: G5 implementation phase, Task 6 next
Highest maturity: M2 implementation and scoped mechanism evidence

## Purpose

This is the context-free continuation record for the next conversation. The
only authorized next work is **G5 Task 6: implement the physical training and
evaluation adapter, formal metrics, and support controllers** from
`docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`.

Do not redo G5 Tasks 1-5. Do not start Task 7, G6 formal jobs, G7 sealed
evaluation, G5 pilots, validation tuning, or thesis efficacy/superiority
analysis. Stop after Task 6 is implemented, reviewed, verified, committed,
pushed, and recorded in `docs/PROJECT_STATE.md`.

`HANDOFFG5.md` is the preceding historical handoff for Task 5. It is retained
for provenance but is not the current instruction. `docs/PROJECT_STATE.md` is
the authoritative dynamic state record.

## Mandatory Startup

Read these files completely before editing:

1. `AGENTS.md`;
2. `docs/PROJECT_STATE.md`;
3. this handoff;
4. `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, especially Task 6;
5. `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md`;
6. applicable local skills, including `using-superpowers`,
   `sr-mappo-problem2`, `executing-plans`, `test-driven-development`,
   `requesting-code-review`, and `verification-before-completion` when
   available.

Use PowerShell from the repository root and inspect state before changes:

```powershell
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote --heads origin codex/problem2-g5-pilot-freeze
git diff --check
```

The current local, upstream, and remote branch heads must match before Task 6
starts. The only known unrelated working-tree item is the user-owned
untracked directory `_tmp_docx_assets/`; do not inspect, stage, modify, delete,
or clean it. Stop if other unexplained changes overlap Task 6.

## Instruction Precedence And Maturity Note

The repository `AGENTS.md` contains a static default sentence saying that
maturity remains M1 until a later state record says otherwise. The current
`docs/PROJECT_STATE.md` explicitly records accepted G2-G5 implementation
evidence at M2, so the dynamic project-state record governs this continuation.
Task 6 remains implementation/test work at M2 and does not authorize any M3
pilot or M4 formal claim.

Permitted wording remains limited to implementation and verification. Do not
claim that mobile support improves treatment, that SR-MAPPO is superior, that
formal experiments show an effect, that a result is statistically significant,
or that simulation verifies real deployment.

## Research Identity And Protected Boundaries

- Public flagship name: **SR-MAPPO**.
- Problem 2 is the air-ground heterogeneous extension of SR-MAPPO.
- Do not introduce HAPPO or rename the method to `AG-SR-MAPPO`.
- Pesticide is the only replenished resource. Battery replenishment remains
  inactive unless a separate activation audit passes.
- OSM/GraphML and GeoJSON are read-only simulation inputs, not field-deployment
  evidence.
- Keep all Problem-2 outputs below
  `outputs/problem2_sr_mappo_v1`; Task 6 generated outputs, if any, belong
  below `outputs/problem2_sr_mappo_v1/g5`.
- Do not modify the protected first-problem repository
  `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`.
- Do not modify `D:/Pycharm/Locust_rl`, its OSM inputs, the planning evidence
  directory, or external Word files.
- Do not import first-problem runtime modules or reuse first-problem logs,
  checkpoints, outputs, or results as Problem-2 evidence.

## Completed Work

The following work is accepted and must be treated as the current foundation:

- G0-G1: project isolation, evidence registries, source/parameter lineage,
  partition contracts, output-root rules, and fail-closed registry audits.
- G2: deterministic offline road source, metric projection/topology, physical
  motion, explicit request/reservation/service states, pesticide ledger,
  transactional replay, deterministic caches, and audit CLIs.
- G3: heterogeneous role actors, centralized critic contract, action masks,
  GAE, normalization, checkpoint round trip, and development-only MARL
  acceptance.
- G4: pesticide-only onboard scarcity activation and diagnostic support-probe
  counterfactual. It is not learned-policy efficacy evidence and does not
  establish vehicle-inventory scarcity.
- G5 Task 1: G4 lineage reconciled to one exact generator commit/tree/source
  bundle tuple.
- G5 Task 2: methods, candidates, fairness, budget, partitions, metrics,
  statistics, exclusions, dependency, and Problem-1 lineage contracts frozen.
- G5 Task 3: shared behavior-bound protocol, replay, diagnostics, and atomic
  checkpoint/resume support implemented while preserving G3 behavior.
- G5 Task 4: `sr_mappo_mobile`, `mappo_mobile`, and `ippo_mobile` implemented
  with on-policy envelopes, validity-aware GAE, deterministic evaluation,
  transactional updates, and exact resume.
- G5 Task 5: heterogeneous discrete MADDPG and IQL implemented with the
  strict off-policy envelope, role-specific networks/optimizers/targets,
  behavior masks, replay, checkpoint state, deterministic evaluation, and
  legacy IQL trainer-state migration.

## Task 5 Evidence And Commits

Task 5 was completed at M2. No pilot, validation tuning, formal job, sealed
scenario access, efficacy claim, superiority claim, external protected write,
or Word-file edit occurred.

Implementation and review chain:

- `caf4277ed1c178565f8bf3995d60871e24fe02d4`:
  `feat: implement heterogeneous maddpg and iql`;
- `9c617d3fcc302c323cd1bcd4e348f902f6f36c5c`:
  `docs: record task 5 implementation report`;
- `9b2518bf8795a071a909812f201a535a1e2979aa`:
  `fix: harden g5 off-policy validity and target cadence`;
- `52baca35f2c8d6dd3892445fe686b8fa6cf95522`:
  `fix: preserve g5 iql checkpoint compatibility`;
- `59877f6b440da53b83647a6715390a02c6e06372`:
  `docs: record g5 task 5 persistence`.

Two independent review rounds closed all Critical/Important findings. Three
Minor observations remain explicitly deferred in the SDD ledger:

- exact-type validation for replay capacity;
- a stronger non-constant objective in the Gumbel gradient test;
- explicit replay ring/wrap and resume-sampling test coverage.

Fresh final verification recorded in `docs/PROJECT_STATE.md`:

```text
G5 off-policy focused: 22 passed
G5 protocol/checkpoint: 27 passed
G3 suite: 65 passed
G5 suite: 187 passed
host full regression: 486 passed in 187.37s
compileall: exit 0
G5 contract audit: status=pass, validation_accessed=false,
  sealed_accessed=false, actual_unlock_count=0
git diff --check: exit 0
```

## Exact Task 6 Scope

Create only the planned Task 6 files:

```text
src/problem2/training/cooperative_env.py
src/problem2/evaluation/metrics.py
src/problem2/evaluation/runner.py
src/problem2/evaluation/partitions.py
src/problem2/heuristics/__init__.py
src/problem2/heuristics/fixed.py
src/problem2/heuristics/astar.py
src/problem2/heuristics/nearest.py
src/problem2/heuristics/urgency.py
src/problem2/heuristics/two_stage.py
tests/g5/test_environment_metrics.py
tests/g5/test_heuristics.py
```

Narrowly necessary shared changes are allowed only when a failing Task 6 test
proves they are required. Do not change frozen registries, candidate values,
algorithm mathematics, G2 source inputs, or Task 5 behavior without a written
state-recorded ruling and regression evidence.

Required interfaces and semantics:

1. `Problem2CooperativeEnv` wraps the accepted G2 road, motion, service, and
   pesticide-ledger components. It emits the verified G3 role observations and
   masks and never replaces a sampled UAV or vehicle action inside the
   environment.
2. `EpisodeMetrics` directly accumulates road-route rendezvous distance,
   realized service travel, pending/reserved waiting exposure including
   unresolved terminal waits, completed-request waiting, pesticide-disabled
   UAV-time, return UAV-time, effective positive spray steps, service
   outcomes, transfer/inventory, resource residual, and decision-only runtime.
3. `evaluate_episode(environment, policy, partition, scenario_id,
   deterministic=True) -> EpisodeRecord` freezes learning, normalization, and
   exploration state. It returns a before/after byte identity proof and uses
   the declared partition guard.
4. `fixed`, rolling `astar`, `nearest`, and `urgency` controllers use only
   current observable requests and road state, deterministic tie-breaking,
   frozen replanning/service-feasibility rules, and no future pest/demand
   state. A* path lengths must agree with Dijkstra on sampled graphs.
5. `two_stage` training consumes exactly the same total environment
   interaction budget as joint SR-MAPPO and records both stage budgets in
   checkpoint ancestry.

## Required Task 6 TDD Order

1. Write failing metric tests for unresolved terminal wait, zero transfer,
   partial service, actual road detour, positive effective spray, and exact
   pesticide conservation.
2. Write failing controller tests for fixed-resource matching, A* versus
   Dijkstra, deterministic ties, unreachable requests, service feasibility,
   no-future-state signatures, and two-stage budget equality.
3. Run both focused suites and record RED caused by missing adapters.
4. Implement the environment adapter and direct event metrics over the
   accepted G2 state machine.
5. Implement fixed, A*, nearest, urgency, and two-stage adapters; time only
   controller decision computation.
6. Run focused tests plus all G2/G3/G4 regressions.
7. Request independent review, fix every Critical/Important finding with a
   reproducing test, then run final verification.

## Frozen Comparisons And Metric Rules

The primary comparison family remains:

- `sr_mappo_mobile`;
- `sr_mappo_fixed`;
- `sr_mappo_astar`;
- `mappo_mobile`;
- `sr_mappo_two_stage`.

Task 6 only builds the adapters. It does not execute this family as a pilot or
formal matrix. Keep total pesticide, vehicle inventory, service capability,
horizon, scenario IDs, observability, and evaluation budgets equal where the
causal comparison requires equality.

The metric meanings are frozen:

- `rendezvous_distance_m`: shortest feasible road route from support location
  at reservation to selected service road node, not Euclidean separation;
- `vehicle_service_travel_m`: realized road distance including replanning
  detours;
- `waiting_steps`: all pending/reserved exposure, including unresolved
  terminal requests;
- `completed_request_waiting_steps`: creation to service-start wait only for
  requests that actually start service;
- `pesticide_disabled_steps`: UAV-time unable to execute positive spray due to
  insufficient usable onboard pesticide;
- `return_steps`: UAV-time spent in declared rendezvous/return behavior;
- `effective_spray_steps`: legal spray actions applying a positive pesticide
  amount;
- `decision_runtime_s`: synchronized timing around policy/controller decisions
  only, excluding environment advancement and file I/O.

## Stop Conditions

Stop and record the blocker without advancing to Task 7 if:

- local/upstream/remote history differs or unexplained overlapping changes
  appear;
- a Task 6 metric cannot be derived directly from G2 event/state semantics;
- the adapter overrides sampled actions or leaks future demand/pest state;
- waiting, partial transfer, zero transfer, terminal unresolved requests, or
  resource conservation are ambiguous or untested;
- A* disagrees with Dijkstra on the required sampled graph checks;
- deterministic evaluation mutates policy, normalization, exploration, or
  identity state;
- two-stage interaction budgets differ from joint SR-MAPPO;
- any focused Task 6, G2, G3, or G4 verification fails;
- implementation requires pilot execution, validation access, formal job
  queueing, sealed access, registry drift, protected external writes, or
  Word-file edits.

## Completion And Persistence Contract

At Task 6 completion, report the highest maturity actually supported, changed
files, RED/GREEN evidence, review findings and fixes, failed or unverified
gates, protected paths left untouched, and permitted wording. Then:

1. commit content with the exact plan subject:
   `feat: add g5 environment metrics and support controllers`;
2. push `codex/problem2-g5-pilot-freeze`;
3. verify local HEAD, upstream HEAD, and `git ls-remote` parity;
4. update `docs/PROJECT_STATE.md` with Task 6 scope, verification, pushed
   hash, maturity boundary, access statement, and next authorized task;
5. commit the state record separately with a descriptive `docs:` subject;
6. push again and verify parity again.

The next authorized task after a clean Task 6 persistence record is Task 7,
which generates experiment families and the deduplicated training graph. Do
not begin Task 7 in the same continuation.

## Current Working-Tree Note

`_tmp_docx_assets/` is user-owned, untracked, and protected. It must remain
untouched and unstaged. No other current working-tree change is authorized at
handoff creation.
