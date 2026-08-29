# G6 Readiness Handoff: Phase 3 Continuation

Date: 2026-08-29

This is the current no-context handoff for the second thesis problem. Read it
together with `AGENTS.md` and `docs/PROJECT_STATE.md`. If an older handoff
conflicts with `docs/PROJECT_STATE.md`, the project state is authoritative.
This document supersedes the Phase 1 entry instructions for the next session;
older handoffs remain historical records.

## 1. Task And Research Identity

Repository: `C:/Users/RZX/Documents/ChatGPT/Second`

Branch: `codex/problem2-dynamic-pest-model`

Remote: `https://github.com/rzx127097-create/Second.git`

The thesis problem is road-constrained air-ground heterogeneous cooperative
pesticide spraying with multiple UAVs and a mobile pesticide replenishment
vehicle. The public flagship algorithm name is **SR-MAPPO**. Problem 2 is an
air-ground heterogeneous extension of SR-MAPPO.

The current engineering task is **G6 readiness Phase 3 continuation**:
revalidate the dynamic physical execution path, preserve executable controller
semantics, and build bounded development-pilot evidence for a future
replacement G5 freeze. This is not formal G6 execution.

All new evidence belongs under:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
```

The mandatory ecology is `dynamic_pest_v1`. Historical static-ecology output
under `outputs/problem2_sr_mappo_v1/g5/` is read-only diagnostics.

## 2. Current Gate Boundary

- Maturity remains `M2`.
- G6 readiness Phase 0, Phase 1, and Phase 2 are persisted milestones.
- Phase 3 is controlled continuation after controller remediation; no
  replacement G5 freeze exists yet.
- Phase 4 preflight and formal G6 jobs are blocked.
- G7 sealed-test unlock count is `0` (maximum `1`).
- Validation scenarios are `20000-20049`; sealed scenarios are `30000-30099`.
  Do not access either payload range during this continuation.
- Pesticide is the only replenished resource. Battery replenishment is false.

At `M2`, say proposes, defines, implements, revalidates, or verifies bounded
engineering behavior. Do not claim efficacy, superiority, significance, real
deployment, or universal optimality.

## 3. Completed Work

### 3.1 Executable controller semantics

The physical path now executes the selected condition rather than passing
`sr_mappo_mobile` internally and relabeling it:

| condition | vehicle controller | training mode | vehicle trainable |
|---|---|---|---:|
| `sr_mappo_mobile` | `learned` | `joint` | true |
| `sr_mappo_fixed` | `fixed_support` | `uav_only` | false |
| `sr_mappo_astar` | `rolling_astar` | `uav_only` | false |
| `sr_mappo_nearest` | `nearest_feasible` | `uav_only` | false |
| `sr_mappo_urgency` | `urgency_priority` | `uav_only` | false |
| `sr_mappo_two_stage` | `learned_two_stage` | `two_stage` | true |

The remediation covers selected-refit provenance, fixed-support initialization,
request/slot/node/reachability/distance checks, vehicle actor/replay/optimizer
isolation for non-learned conditions, executed-controller logging, current
rolling-A* route distance, and retention of an active locked service node.

### 3.2 Development revalidation

Five non-mobile paths were run for 8 physical interactions using
`method=sr_mappo_mobile`, `candidate_id=c01`, `scale=g20x20_d2`,
`training_seed=51001`, and development panel `10000-10019`. All completed.
Artifacts are under:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-controller-checks/
```

The first A* and nearest attempts failed before artifact writes. Their empty
attempt directories remain local markers; successful reruns use separate
`astar-after-route-fix` and `nearest-after-node-fix` directories.

The original mobile pilot identity was rerun after source changes under:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-first-revalidated/
```

```text
method=sr_mappo_mobile
condition_id=sr_mappo_mobile
vehicle_controller=learned
training_mode=joint
candidate_id=c01
scale=g20x20_d2
training_seed=51001
scenario_id=10000
interactions=128
dynamic episodes=1
dynamic ecology steps=128
accepted spray actions=25
sprayed pesticide=0.48750000000000016 L
completion_validated=true
validation_accessed=false
sealed_accessed=false
battery_replenishment_enabled=false
evidence_status=noncanonical_test_only
```

This is descriptive engineering evidence only, not a formal result.

### 3.3 Audits And Commits

Dynamic audit:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation-phase3-post-controller.json
```

Detailed audit: `docs/audits/g6-readiness-phase3.md`

The important pushed commits are recorded in `docs/PROJECT_STATE.md`; the
latest content commit is `3f70603` and the latest state commit is `3a6e2e4`.
The current full commit is:

```text
3a6e2e4fc438e3e5ee20c1484e373270bf9dd88b
```

Local HEAD, upstream, and the remote branch matched this hash at handoff.

## 4. Fresh Verification

Fresh checks after the content commit:

```text
python -m pytest tests/g6 -q --tb=short
50 passed in 32.10s

python -m pytest tests/ecology tests/g3 tests/g4 tests/g5/test_heuristics.py tests/g5/test_physical_candidate_training.py tests/g5/test_environment_metrics.py tests/g5/test_end_to_end_smoke.py tests/g5/test_experiment_matrix.py -q --tb=short
381 passed in 462.35s

python -m compileall -q src scripts
exit 0

git diff --check
pass
```

Six manifests were checked; every referenced artifact existed with matching
byte count and SHA-256. A prior run gave `377 passed, 4 failed` only because an
uncommitted tracked `PROJECT_STATE.md` edit correctly triggered the matrix
dirty-tree guard. After the content commit, the matrix subset passed `8` and
the full affected suite passed `381`. Do not weaken that guard.

## 5. Immediate Next Plan

Run another controlled dynamic development pilot, one job at a time, using a
new uncovered development identity toward a complete replacement G5 pilot
matrix.

For each pilot:

1. Use `dynamic_pest_v1` and the dynamic output root only.
2. Use development scenarios only; do not read validation or sealed payloads.
3. Keep pesticide as the only replenished resource and battery disabled.
4. Preserve method, candidate, scale, seed, horizon, budget, and condition
   semantics unless a replacement decision is documented before evaluation.
5. Write raw logs, checkpoint, summary, manifest, and completion/audit evidence.
6. Validate identity, ecology, controller semantics, conservation, completion,
   and access flags before starting the next job.
7. Preserve failed attempts and diagnostics; never silently retry or overwrite.
8. Update audit/state, commit, and push before moving to the next gate.

After the pilot/refit evidence is complete:

1. Generate and persist a replacement dynamic G5 freeze.
2. Run the full read-only Phase 4 preflight against that exact pushed freeze.
3. Only a passing preflight can authorize the first formal G6 job; stop and
   inspect diagnostics after that first job.
4. G7 remains later and may use the single sealed unlock only after its gate.

Do not jump directly to formal G6, validation selection, or G7.

## 6. Absolute Do-Not-Repeat Rules

- Do not run formal G6, validation selection/evaluation, or sealed evaluation.
- Do not access, inspect, copy, hash, or manufacture payloads for `20000-20049`
  or `30000-30099`.
- Do not unlock G7; actual unlock count stays `0`.
- Do not modify, move, relabel, or overwrite historical static G5 outputs.
- Do not write new evidence outside the dynamic output root.
- Do not introduce HAPPO, rename SR-MAPPO, or use `AG-SR-MAPPO` publicly.
- Do not claim treatment efficacy, superiority, significance, deployment, or
  optimality from M2 development evidence.
- Do not pass mobile internally and relabel fixed/A*/nearest/urgency/two-stage.
- Do not enable battery replenishment or broaden ablation/sensitivity beyond
  exactly `sr_mappo_mobile`.
- Do not alter budgets, ranges, statistics, or selection rules after validation
  access; issue a replacement freeze instead.
- A Windows checkpoint `PermissionError` is a failed attempt, not success.
  Record it and recover only the identical identity while preserving the prior
  valid checkpoint.
- Do not use `git add .`, `git add -A`, `git clean`, force-push,
  `git reset --hard`, or destructive checkout commands.
- Do not stage, delete, or clean pre-existing untracked directories.
- Do not create another worktree or touch detached `Second-tdd-clean`.
- Do not modify protected first-problem, base-project/OSM, planning-evidence,
  or external Word thesis files.

## 7. Pre-existing Untracked Directories

Leave these untouched and unstaged:

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

Inspect any additional status entries at startup; never auto-revert or clean.

## 8. Startup Checklist

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

Expected current state is HEAD/upstream/remote
`3a6e2e4fc438e3e5ee20c1484e373270bf9dd88b`, clean tracked files, preserved
untracked temporary directories, and `50 passed`. If the baseline differs,
stop and reconcile against `docs/PROJECT_STATE.md`.

## 9. Evidence Chain

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

Training completion, a smoke test, a dry-run, a preflight printout, or one
development pilot is not a thesis efficacy result. G6 readiness and Phase 3
development evidence do not authorize method ranking or superiority claims.

## 10. Matrix Contract Update

The historical dynamic audit for
`phase3-matrix-002-fixed` retains the manually recorded label
`05202683b9a9add68cc7e72c8ae6e9adf7fb44dd7d0e47be9ba121ae7c9acb4b`. The
historical and current `PilotJob.identity` serializer independently produce
the canonical identity
`05202683b9a9dd60c693b1ab0eb3662ff3dd3731baba7ca45596508273f005b1` for the
same tuple. Treat the former as a byte-preserved historical audit-label typo;
do not modify or relabel its output artifacts.

The replacement executable pilot matrix is now an explicit condition-to-method
mapping with 20 conditions, five learning methods, two scales, three
development seeds, and 120 jobs (2,400 scenario-reference rows). The first
three canonical identities are stable for the mobile, fixed-support, and
rolling-A* tuples. Subsequent pilot indices must be resolved from this new
matrix, and the old static 510-job pilot/refit remains historical diagnostics
only. Persist and review the repair before running the next development job;
replacement freeze, Phase 4 preflight, formal G6, validation selection, and
G7 remain blocked.

## 11. Matrix Identity 004 Result

The first pilot from the repaired matrix was zero-based index `3`:
`mappo_mobile + mappo_mobile`, identity
`c88c56866c9d7db3ea7059233019c2f014fe39375d736a0de14d8c5a7f2f51de`.
It completed one 128-interaction dynamic development episode with 11 accepted
spray actions and 0.22 L sprayed pesticide. The strict checkpoint and artifact
audit passed; validation, sealed, and battery flags remained false. The output
is under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-004-mappo/`
and is descriptive `M2` evidence only. An audit-wrapper field mismatch was
recovered by reusing the completed files; training was not rerun.

The next authorized identity is zero-based index `4`,
`sr_mappo_mobile + sr_mappo_two_stage`, still one dynamic development pilot at
a time. No replacement freeze or formal G6 action is authorized.

## 12. Matrix Identity 005 Result

The next uncovered identity from the repaired matrix was zero-based index `4`:

```text
identity=31837fe943ba86c6d03dd9ab1cb122e6bfefa08e3d61733d313c741ac5b493b2
method=sr_mappo_mobile
condition_id=sr_mappo_two_stage
vehicle_controller=learned_two_stage
vehicle_trainable=true
training_mode=two_stage
candidate_id=c01
scale=g20x20_d2
training_seed=51001
partition=development
scenario_ids=10000-10019
scenario_id=10000
interactions=128
```

It completed one dynamic development episode under source commit
`492de00c8fe4c12ea09eb0cd7d74dda6481d0320`, with `128` ecology steps, `25`
accepted spray actions, and `0.48750000000000016 L` sprayed pesticide. Team
reward was `0.3913904742247592`; total pest changed from
`9.088605068072038` to `5.531411620437773`. These remain descriptive `M2`
engineering observations only and support no efficacy, superiority,
significance, ranking, or deployment claim.

The strict checkpoint reload and artifact audit passed. The machine audit is
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-005-two-stage/pilot-audit.json`;
the physical checkpoint, manifest, episode log, and summary are under the same
pilot directory. `completion_validated=true`,
`validation_accessed=false`, `sealed_accessed=false`, and
`battery_replenishment_enabled=false` remain recorded. The persistence commit
is `61fc3649a5dbfab730f9af84db2b0f881ad38d03` (`data: record fifth dynamic
phase3 pilot`), pushed to `origin/codex/problem2-dynamic-pest-model`.

The highest maturity remains `M2`; the replacement G5 freeze, Phase 4
preflight, formal G6, validation selection, and G7 remain blocked. The next
authorized identity is zero-based matrix index `5`,
`sr_mappo_mobile + sr_mappo_nearest`, and it may be run only as one controlled
dynamic development pilot after this handoff state is persisted. No validation
or sealed payload access is permitted, and the G7 unlock count remains `0`.

## 13. Matrix Identity 006 Result

The next uncovered identity from the repaired matrix was zero-based index `5`:

```text
identity=411f2fdd00a89b1d024ec4560dfeb35d08bf841ad7d90ec504e403d50a28b3b8
method=sr_mappo_mobile
condition_id=sr_mappo_nearest
vehicle_controller=nearest_feasible
vehicle_trainable=false
training_mode=uav_only
candidate_id=c01
scale=g20x20_d2
training_seed=51001
partition=development
scenario_ids=10000-10019
scenario_id=10000
interactions=128
```

It completed one dynamic development episode under source commit
`53e2238ab36d25c2c8c1fd1be24f74772507d060`, with `128` ecology steps, `25`
accepted spray actions, and `0.48750000000000016 L` sprayed pesticide. Team
reward was `-0.035699709362087946`; total pest changed from
`9.088605068072038` to `9.41306562750901`. These remain descriptive `M2`
engineering observations only and support no efficacy, superiority,
significance, ranking, or deployment claim.

The strict checkpoint reload and artifact audit passed. The machine audit is
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-006-nearest/pilot-audit.json`;
the physical checkpoint, manifest, episode log, and summary are under the same
pilot directory. `completion_validated=true`,
`validation_accessed=false`, `sealed_accessed=false`, and
`battery_replenishment_enabled=false` remain recorded. The persistence commit
for this result is to be recorded after the audit/state files are committed and
pushed.

The highest maturity remains `M2`; the replacement G5 freeze, Phase 4
preflight, formal G6, validation selection, and G7 remain blocked. The next
authorized identity is zero-based matrix index `6`,
`sr_mappo_mobile + sr_mappo_urgency`, and it may be run only as one controlled
dynamic development pilot after this handoff state is persisted. No validation
or sealed payload access is permitted, and the G7 unlock count remains `0`.
