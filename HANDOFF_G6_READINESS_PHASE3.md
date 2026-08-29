# G6 Readiness Phase 3 Handoff

Date: 2026-08-30

This document is the no-context startup record for the next conversation. Read
it together with `AGENTS.md` and `docs/PROJECT_STATE.md` before doing any work.
`AGENTS.md` contains repository instructions, `docs/PROJECT_STATE.md` is the
authoritative record of the current gate and maturity, and this file is a
handoff summary. If they conflict, `AGENTS.md` and then
`docs/PROJECT_STATE.md` take precedence.

## 1. What The User Asked For

The user asked to continue the approved plan for reducing the time spent on
the remaining development pilots. The 30-job draft was revised to the valid
48-job replacement contract, while repeated G3/G4 reacceptance work was
reduced to source-scope reuse plus targeted dynamic checks. The user did not
authorize bypassing G5, Phase 4 preflight, formal G6, validation access, or G7.

The replacement contract and tests are committed and pushed in
`c92b70678727511e8ac19d0531d9b81a54277295`; dynamic reacceptance evidence is
committed and pushed in `b0ab4cd5719e7fab93a810fdb9f7717b9796cb4a`.

## 2. Research Identity And Hard Boundary

Repository: `C:/Users/RZX/Documents/ChatGPT/Second`

Branch: `codex/problem2-dynamic-pest-model`

Remote: `https://github.com/rzx127097-create/Second.git`

Public algorithm identity: **SR-MAPPO**. Problem 2 is a road-constrained
air-ground heterogeneous cooperative pesticide-spraying extension with a
mobile pesticide replenishment vehicle.

The only replenished resource is pesticide. Battery replenishment must remain
`false`. OSM data is simulation input for road-constrained modeling, not field
deployment evidence.

All new evidence must be under:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
```

Historical static-ecology G5 output is read-only diagnostic material. Do not
modify or relabel it.

## 3. Current State At Handoff

- Highest maturity: `M2` implementation and scoped mechanism evidence.
- Current work: G6 readiness Phase 3, dynamic development-pilot continuation.
- Formal G6: blocked.
- Replacement dynamic G5 freeze: not generated.
- Phase 4 preflight: not run or not authorized yet.
- G7 sealed-test unlock count: `0` of maximum `1`.
- Validation scenarios: `20000-20049`; sealed scenarios: `30000-30099`.
  Neither range may be accessed, copied, inspected, hashed, or generated during
  this work.
- Development panel used by the pilots below: `10000-10019`.

Persisted repository state at the time of this handoff:

```text
HEAD       c976d62 (state record; full hash recorded below)
upstream   c976d62 (state record; full hash recorded below)
remote     c976d62 (state record; full hash recorded below)
```

The latest content commit is `5b6d3ef83135d0965b4b438319adc3b46c7baabc`
(`data: record seventh dynamic phase3 pilot`); the latest state-record commit
is `c976d62` (`docs: record refreshed g6 handoff state`), whose full hash is
`c976d628fda86647efd14be83f7eee274459d99b`.
The preceding handoff content commit is `4cb579c`.
Local, upstream, and GitHub remote matched at handoff. The worktree is not
clean because the replacement-matrix draft and pre-existing untracked
artifacts are present; inspect them, do not clean them.

## 4. Completed Work

### 4.1 Dynamic execution and controller remediation

The dynamic ecology implementation is `dynamic_pest_v1`, with the inherited
Holling-Tanner reaction-diffusion pest dynamics, wind advection, and persistent
decaying pesticide-effect field. The Phase 3 controller work now:

- preserves the selected outer condition through physical refit dispatch;
- executes the actual controller for each condition rather than passing the
  mobile controller and relabeling it;
- checks slot/request identity, allowed primary-component node, reachability,
  and distance before reservation or service;
- starts fixed support at the frozen support node;
- isolates vehicle replay/optimizer updates for non-learned conditions;
- records the executed controller slot in the physical envelope;
- refreshes rolling-A* current route distance between replans; and
- retains the active locked service node after UAV movement.

The validated controller semantics are:

| condition | controller | training mode | vehicle trainable |
|---|---|---|---:|
| `sr_mappo_mobile` | `learned` | `joint` | true |
| `sr_mappo_fixed` | `fixed_support` | `uav_only` | false |
| `sr_mappo_astar` | `rolling_astar` | `uav_only` | false |
| `sr_mappo_nearest` | `nearest_feasible` | `uav_only` | false |
| `sr_mappo_urgency` | `urgency_priority` | `uav_only` | false |
| `sr_mappo_two_stage` | `learned_two_stage` | `two_stage` | true |

### 4.2 Phase 3 development pilots already completed

These are seven zero-based identities from the old repaired 120-job matrix.
They are dynamic, development-only, descriptive `M2` evidence. They must not
be silently counted as rows in a new replacement aggregate.

| index | method / condition | controller | interactions | result |
|---:|---|---|---:|---|
| 0 | `sr_mappo_mobile` / `sr_mappo_mobile` | learned | 128 | completion validated |
| 1 | `sr_mappo_mobile` / `sr_mappo_fixed` | fixed_support | 128 | completion validated |
| 2 | `sr_mappo_mobile` / `sr_mappo_astar` | rolling_astar | 128 | completion validated |
| 3 | `mappo_mobile` / `mappo_mobile` | learned | 128 | completion validated |
| 4 | `sr_mappo_mobile` / `sr_mappo_two_stage` | learned_two_stage | 128 | completion validated |
| 5 | `sr_mappo_mobile` / `sr_mappo_nearest` | nearest_feasible | 128 | completion validated |
| 6 | `sr_mappo_mobile` / `sr_mappo_urgency` | urgency_priority | 128 | completion validated |

All seven used `candidate_id=c01`, `scale=g20x20_d2`,
`training_seed=51001`, `partition=development`, scenario panel
`10000-10019`, start scenario `10000`, and `ecology=dynamic_pest_v1`.
Each has raw episode log, checkpoint, summary, manifest, identity/provenance,
completion validation, and per-pilot artifact audit. The latest identity is:

```text
identity=56a1f99f7b0ac8512dab8cfff2fe5c7cd6c1485053d92f2cfb2869ef227f729c
method=sr_mappo_mobile
condition_id=sr_mappo_urgency
vehicle_controller=urgency_priority
vehicle_trainable=false
training_mode=uav_only
interactions=128
dynamic_ecology_steps=128
accepted_spray_actions=25
sprayed_pesticide_l=0.48750000000000016
completion_validated=true
validation_accessed=false
sealed_accessed=false
battery_replenishment_enabled=false
```

The latest pilot audit is
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-007-urgency/pilot-audit.json`.
Its recorded size is `3670` bytes and its SHA-256 is
`1ab070f0d41b182c0155717ca3ac41d49887fabc82751f84eaadb816b03529b4`.

The seven pilots and all controller checks are engineering evidence only.
They do not support claims of efficacy, superiority, statistical
significance, ranking, deployment, or universal optimality.

### 4.3 Verification already recorded

The latest persisted checks recorded in project state include:

```text
python -m pytest tests/g6 -q --tb=short       64 passed
python -m compileall -q src scripts           exit 0
git diff --check                              pass
```

The Phase 3 dynamic implementation audit passed, strict completion and
checkpoint reloads passed for the completed pilots, and referenced artifact
byte counts and SHA-256 values matched. Do not weaken the dirty-tree and
provenance guards because a later test is inconvenient.

## 5. Current Uncommitted Material

The 48-job replacement contract, tests, design, plan, and dynamic reacceptance
audit are now committed. The worktree contains only pre-existing untracked
temporary directories and the preserved old-matrix IPPO artifact listed below;
do not stage, delete, or merge them automatically.

There is also an important pre-existing untracked artifact directory:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-008-ippo/
```

It belongs to the old 120-job matrix and has:

```text
matrix_index_zero_based=7
matrix_job_count=120
identity=16edaea51bee952905a5089c2793a800895ffc27f4e53f07a00fb699efd818fe
method=ippo_mobile
condition_id=ippo_mobile
source_commit=9f0336391304b727cb4a7b0bc9fb3439ae68e5d2
completion_validated=true
validation_accessed=false
sealed_accessed=false
```

Preserve it. Do not overwrite, rename, delete, or automatically merge it into
the replacement aggregate. Audit and persistence decisions for it must be
explicit.

The following pre-existing untracked directories are also to be left untouched
and unstaged:

```text
_tmp_docx_assets/
outputs/problem2_sr_mappo_v1/g5/_debug/
outputs/problem2_sr_mappo_v1/g5/quarantine/
tmp-bench-cpu/
tmp-bench-cuda/
tmp-bench-loop/
tmp-bench-opt/
tmp-bench-opt128/
tmp-full2/
tmp-pilot-bench/
tmp-refit-provenance-review/
tmp-res2/
tmp-smoke-review-fix-resume/
tmp-smoke-review/
tmp-smoke/
tmp-task11-cli/
tmp-task12-repro/
```

## 6. Approved Replacement Matrix Direction

The 30-job primary-only scope is too small for the existing budget and refit
contracts. The replacement should be:

```text
8 conditions x 2 representative scales x 3 development seeds = 48 jobs
```

The eight executable condition-to-learning-method pairs are:

| condition | learning method | controller/training path |
|---|---|---|
| `sr_mappo_mobile` | `sr_mappo_mobile` | learned, joint |
| `sr_mappo_fixed` | `sr_mappo_mobile` | fixed_support, UAV-only |
| `sr_mappo_astar` | `sr_mappo_mobile` | rolling_astar, UAV-only |
| `mappo_mobile` | `mappo_mobile` | learned, joint |
| `sr_mappo_two_stage` | `sr_mappo_mobile` | learned_two_stage, two-stage |
| `ippo_mobile` | `ippo_mobile` | IPPO mobile path |
| `maddpg_mobile` | `maddpg_mobile` | MADDPG mobile path |
| `iql_mobile` | `iql_mobile` | IQL mobile path |

This preserves runtime evidence for all five required learning methods:
`sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`, `maddpg_mobile`, and
`iql_mobile`. It also retains the five required primary comparison paths.

The following twelve conditions become diagnostic-only and must be explicitly
excluded from primary selection:

```text
sr_mappo_nearest
sr_mappo_urgency
no_observation_normalization
no_return_normalization
no_network_stabilization
no_robust_value_update
no_learning_rate_decay
learning_rate
clip_range
entropy_coef
gamma
gae_lambda
```

This is a G5 development replacement only. It does not change the formal G6
scales, formal training seeds, validation/test partitions, evaluation
horizons, statistics, or sealed-test lock. All replacement jobs remain
development-only, use `dynamic_pest_v1`, pesticide-only replenishment, and
one-job-at-a-time execution.

## 7. Exact Next Steps

1. At startup, read `AGENTS.md`, `docs/PROJECT_STATE.md`, this file, and
   `docs/audits/g6-readiness-phase3.md`. Run `git status --short --branch` and
   verify that local, upstream, and remote still agree with the state record.

2. Confirm the pushed 48-job contract and its source-scope-bound dynamic
   reacceptance evidence. Keep `LEARNING_METHODS`, the budget coverage check,
   and selected-candidate/refit rules intact.

3. The TDD contract is now persisted: exactly 48 unique jobs, eight executable
   conditions, twelve excluded diagnostics, all five learning methods covered,
   excluded conditions rejected, incomplete matrices fail closed, and
   deterministic identities/development panels.

4. The simplified reacceptance has passed focused pilot/condition/controller/
   physical tests, dynamic ecology audit, CPU smoke, `compileall`, and
   `git diff --check`. Rerun the full repository suite only if the source-scope
   gate identifies a G3/G4 implementation or configuration change.

5. Matrix and dynamic reacceptance content are committed and pushed in
   `c92b706` and `b0ab4cd`; record these hashes and the fresh verification in
   `docs/PROJECT_STATE.md` before running the first replacement identity.

6. Only after the 48-job replacement contract is committed and pushed, execute
   its development identities one at a time. For every job, mechanically
   resolve the identity, preserve failed attempts, validate completion,
   provenance, ecology, controller semantics, conservation, artifact bytes and
   SHA-256 values, and confirm validation/sealed access remain false.

7. After all 48 identities pass their audit, generate a new dynamic G5 freeze
   with `matrix_complete=true`. Persist it and run the read-only Phase 4
   preflight against that exact pushed freeze.

8. Only a passing replacement freeze and Phase 4 preflight may authorize the
   first formal G6 job. Run that first formal job under the locked six-scale,
   five-seed protocol, stop to inspect recovery and validation immediately
   afterward, and do not jump to G7.

## 8. When Formal G6 Is Allowed

Formal G6 is not allowed merely because seven development pilots completed, a
smoke test passed, or the 30-job draft exists. The minimum chain is:

```text
48-job dynamic development matrix complete and audited
-> replacement dynamic G5 freeze committed and pushed
-> read-only Phase 4 preflight passes against that exact freeze
-> first immutable formal G6 job authorized
```

Until the chain is recorded in `docs/PROJECT_STATE.md`, remain at `M2` and use
only descriptive engineering language: implements, defines, revalidates,
checks, or provides a specification. Do not write proves, significantly
outperforms, formal experiments show, real deployment verified, or universally
optimal.

## 9. Absolute Do-Not-Repeat Rules

- Do not treat 30 jobs as 120 jobs, or any partial matrix as complete.
- Do not weaken or delete the five `LEARNING_METHODS` runtime and refit guards.
- Do not fabricate IPPO, MADDPG, or IQL runtime rows.
- Do not merge the seven old 120-matrix pilots or the untracked index-7 IPPO
  artifact into the new replacement aggregate without an explicit, audited
  decision.
- Do not use historical static-ecology G5 artifacts as dynamic evidence.
- Do not access, copy, hash, inspect, or manufacture validation payloads
  `20000-20049` or sealed payloads `30000-30099`.
- Do not unlock G7; its actual unlock count must remain `0`.
- Do not enable battery replenishment.
- Do not introduce HAPPO or rename the public method to `AG-SR-MAPPO`.
- Do not pass `sr_mappo_mobile` internally and relabel fixed, A*, nearest,
  urgency, or two-stage conditions.
- Do not run batch or parallel pilots; the current boundary is one job at a
  time.
- A Windows checkpoint `PermissionError` or an audit-wrapper failure is a
  failed attempt/diagnostic, not success. Preserve the attempt and recover
  only the identical frozen identity.
- Do not alter budgets, seeds, scenario ranges, horizons, statistics, or
  selection rules after any validation access. Any legitimate change requires
  a new replacement freeze.
- Do not use `git add .`, `git add -A`, `git clean`, force-push,
  `git reset --hard`, or destructive checkout. Do not stage, delete, or clean
  existing untracked directories.
- Do not modify protected assets in the first-problem repository, base project
  or OSM inputs, planning-evidence directory, or external Word thesis files.

## 10. Startup Commands

Run these commands before making changes:

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw docs/PROJECT_STATE.md
Get-Content -Raw HANDOFF_G6_READINESS_PHASE3.md
Get-Content -Raw docs/audits/g6-readiness-phase3.md

git status --short --branch
git log -5 --oneline --decorate
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/codex/problem2-dynamic-pest-model

python -m pytest tests/g6 -q --tb=short
```

Expected baseline is HEAD/upstream/remote
`c976d628fda86647efd14be83f7eee274459d99b`,
with the tracked draft modifications and preserved untracked directories
listed above, and the recorded G6 suite passing. If the baseline differs,
reconcile against `docs/PROJECT_STATE.md` before running or editing pilots.

## 11. Evidence Chain Reminder

Every later formal result must remain traceable through:

```text
source parameter/literature
-> frozen configuration and Git commit
-> canonical run identity and raw episode log
-> validated long-format table
-> paired statistical summary
-> figure/table artifact manifest
-> thesis statement
```

Training completion, a smoke test, a dry run, a preflight printout, or one
development pilot is not a thesis efficacy result. Keep all conclusions
inside the currently authorized maturity gate.
