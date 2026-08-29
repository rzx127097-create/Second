# G6 Readiness Handoff: Phase 1 Complete, Phase 2 Next

Date: 2026-08-29

This document is written for a new conversation with no prior context. It is
the current session handoff after G6 readiness Phase 1. Read it together with
`AGENTS.md` and `docs/PROJECT_STATE.md`; `docs/PROJECT_STATE.md` remains the
authority if any older handoff conflicts with it.

## 1. What This Project Is Doing

Repository:

```text
C:/Users/RZX/Documents/ChatGPT/Second
```

Current branch:

```text
codex/problem2-dynamic-pest-model
```

Remote:

```text
https://github.com/rzx127097-create/Second.git
```

Phase 2 implementation baseline and current pushed state commit at the end of
Phase 1:

```text
1e29bc3647852eedba7219ca149ca334e066cb29
```

The thesis problem is road-constrained air-ground heterogeneous cooperative
pesticide spraying with multiple UAVs and a mobile pesticide replenishment
vehicle. The flagship public algorithm name is **SR-MAPPO**. Problem 2 is an
air-ground heterogeneous extension of SR-MAPPO.

The immediate engineering task is **G6 readiness Phase 2**: implement the
minimum real runner, recovery, condition execution, validation selection,
dynamic manifest generation, and complete read-only preflight needed to turn
the focused G6 readiness tests GREEN.

This is not formal G6 execution. Phase 2 must not start training, validation
evaluation, or G7 sealed evaluation.

## 2. Current Scientific And Gate Boundary

- Highest maturity: `M2`.
- G6 readiness Phase 0: complete and pushed.
- G6 readiness Phase 1: complete and pushed as a RED test milestone.
- Next authorized work: G6 readiness Phase 2 implementation and testing.
- Formal G6 jobs: blocked.
- G7 sealed-test unlock count: `0`; maximum allowed unlock count: `1`.
- Validation scenario IDs: `20000-20049` only.
- Sealed-test scenario IDs: `30000-30099`; do not access their payloads,
  locators, manifests, or results during Phase 2.

At `M2`, it is permitted to say that the system proposes, defines, implements,
or verifies a bounded engineering contract. It is not permitted to claim
efficacy, superiority, statistical significance, real deployment, or universal
optimality.

Training reward is diagnostic only. Later thesis conclusions must use
fixed-scenario evaluation and the locked paired statistical summary.

## 3. Non-Negotiable Research Decisions

1. Use the public name `SR-MAPPO`.
2. Do not introduce HAPPO as an implementation or baseline.
3. Do not rename the method to `AG-SR-MAPPO` or another public name.
4. Every future primary, formal, ablation, sensitivity, and sealed experiment
   uses the dynamic ecology environment `dynamic_pest_v1`.
5. New evidence belongs below:

   ```text
   outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
   ```

6. Historical static-ecology G5 outputs remain read-only diagnostics. They are
   not valid dynamic evidence and must never be moved, modified, or relabeled.
7. Ablation and sensitivity jobs are restricted to exactly
   `sr_mappo_mobile`.
8. Pesticide is the only replenished resource. Battery replenishment remains
   disabled unless a separate activation audit is authorized, passed, and
   recorded.
9. OSM road data is simulation input for road-constrained modeling, not
   evidence of real field deployment.

## 4. Gate Names: Do Not Confuse Them

The research gates are:

```text
G0 -> G1 -> G2 -> G3 -> G4 -> G5 -> G6 -> G7 -> G8
```

The internal G6 readiness phases are:

| Readiness phase | Status | Purpose | Experiments allowed |
|---|---|---|---|
| Phase 0 | Complete | Preserve/isolate state and audit entry conditions | No |
| Phase 1 | Complete | Add focused failing readiness tests | No |
| Phase 2 | Next | Implement runner/recovery/evaluator/preflight contracts | No |
| Phase 3 | Blocked | Revalidate affected dynamic G3-G5 work and create replacement freeze | Controlled pilots only, sequentially |
| Phase 4 | Blocked | Run full preflight, then the first formal job | Only after all earlier phases pass |

Completing Phase 2 does not authorize a G6 job. A replacement dynamic G5
freeze and a passing Phase 4 preflight are still required.

## 5. What Has Already Been Completed

### 5.1 Earlier implementation evidence

The repository already contains bounded `M2` implementation evidence for:

- G2 deterministic road topology, scale conversion, service state machine,
  resource conservation, and replay checks;
- G3 heterogeneous role actors, centralized critic, masks, GAE,
  normalization, checkpoint round trip, and development smoke;
- G4 pesticide-only scarcity and mobile/fixed support mechanism probes;
- G5 pilot, validation-tuning, refit, and freeze infrastructure.

Problem 2 was subsequently required to inherit the full dynamic pest ecology.
The dynamic implementation uses Holling-Tanner reaction-diffusion, dynamic wind
advection, and a persistent decaying pesticide-effect field. The old linear
local-decrease G5 evidence is therefore historical only.

The latest recorded dynamic checks before G6 readiness included:

```text
targeted ecology/G3/G4/G5 suite: 707 passed
G5 suite:                         434 passed
repository-wide suite:           865 passed
G4 mechanism audit:              pass
G4 lineage audit:                pass
compileall src/scripts:           exit 0
git diff --check:                 pass
```

These are engineering and bounded development checks, not formal treatment
results.

### 5.2 G6 readiness Phase 0

Phase 0 audited the checkout, protected existing assets, and confirmed that
the old G6 scripts were not executable formal infrastructure.

Key persistence commits:

```text
fc12e389754b2017c53ebed4704d2fd370b718e8  Phase 0 audit/state
0993b2574996ca2653b74f58c1228b028f375a0c  Phase 0 handoff
2b6edad410a8cb455ceee0ec5b04cda502b31e68  Phase 0 persistence record
```

The detailed prior handoff is `HANDOFF_G6_READINESS_PHASE0.md`.

### 5.3 G6 readiness Phase 1

Phase 1 added test-first RED contracts under `tests/g6/` without changing
production source or running an experiment.

Files added in the Phase 1 content commit:

```text
docs/audits/g6-readiness-phase1-red.md
tests/g6/conftest.py
tests/g6/test_condition_semantics.py
tests/g6/test_preflight_readiness.py
tests/g6/test_runtime_readiness.py
tests/g6/test_validation_readiness.py
```

Persistence commits:

```text
340c834dd1f42ea15efac1b4f0e4e874848f3bb0  test: define g6 readiness red contracts
1e29bc3647852eedba7219ca149ca334e066cb29  docs: record g6 readiness phase 1
```

At the end of Phase 1, local HEAD, upstream HEAD, and the remote branch all
matched `1e29bc3647852eedba7219ca149ca334e066cb29`.

Relevant G5 regression before the RED tests:

```text
120 passed
```

Fresh Phase 1 reproduction in the closing session:

```text
python -m pytest tests/g6 -q --tb=short
30 failed, 10 passed in 23.68s
```

The failing result is expected and is the correct Phase 2 starting point. Do
not mark the current repository as generally broken, and do not weaken the
tests to hide these failures.

## 6. What The 30 RED Failures Mean

The failures are grouped as follows.

### 6.1 Condition execution and dispatch: 11 failures

The selected-refit path currently receives an outer condition such as
`sr_mappo_fixed` but calls the physical job internally as
`sr_mappo_mobile`, then effectively relabels the output. There is also no
`problem2.training.conditions` module implementing executable condition
resolution.

The required mapping is:

| Condition | Vehicle controller | Learn vehicle | Training mode |
|---|---|---:|---|
| `sr_mappo_mobile` | `learned` | true | `joint` |
| `sr_mappo_fixed` | `fixed_support` | false | `uav_only` |
| `sr_mappo_astar` | `rolling_astar` | false | `uav_only` |
| `sr_mappo_nearest` | `nearest_feasible` | false | `uav_only` |
| `sr_mappo_urgency` | `urgency_priority` | false | `uav_only` |
| `sr_mappo_two_stage` | `learned_two_stage` | true | `two_stage` |

Changing only `condition_id`, filenames, or report labels is not an
implementation.

### 6.2 Entry, freeze, preflight, and resource contract: 9 failures

Missing behavior includes:

- the complete G6 read-only preflight contract;
- common frozen source-scope binding;
- deterministic `scheduler_order`;
- positive `expected_storage_bytes` and `expected_gpu_hours`;
- disk headroom for the frozen estimate plus atomic checkpoint replacement;
- import-safe `main()` entry points for run, resume, and preflight scripts.

The current preflight can print `all_pass=true` while checking only the older,
limited static contract. That output is not G6 authorization.

### 6.3 Ledger and checkpoint recovery: 2 failures

Ledger events are missing complete UTC time, host, process, attempt, and
artifact provenance fields. Checkpoint recovery cannot yet verify an expected
SHA-256 while retaining the previous valid copy.

On Windows, a checkpoint rename/replace `PermissionError` is a failed attempt.
It must be recorded and recovered only with the identical frozen identity. Do
not treat it as success and do not silently skip the checkpoint.

### 6.4 Validation, evaluator, dynamic manifests, and selection: 8 failures

Missing behavior includes:

- deterministic-policy binding;
- `dynamic_pest_v1` ecology binding;
- dynamic output-root confinement;
- a new evaluator hash after replacing the blocking runner/evaluator path;
- replacement manifest placement under
  `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/`;
- frozen checkpoint selection;
- exact and complete `20000-20049` validation-row coverage;
- retention of every candidate row used by checkpoint selection.

The frozen selection order is:

1. higher mean validation reduction rate;
2. higher validation success probability;
3. earlier interaction count;
4. lexicographically smaller checkpoint hash.

No sealed scenario may participate in selection.

### 6.5 What the 10 passing tests already protect

The passing tests confirm reusable enforcement for:

- exact source-commit propagation by the freeze builder;
- dirty tracked-tree and local/upstream/remote mismatch rejection;
- unique canonical training identities and duplicate rejection;
- append-only replay, same-identity retry, and stale-input denial;
- validation range and sealed-input rejection;
- `sr_mappo_mobile`-only ablation and sensitivity restrictions.

Reuse these contracts. Do not rewrite working components without a failing
test or a concrete Phase 2 need.

## 7. Exact Next Plan: Phase 2

Implement in small dependency order and run the relevant focused tests after
each slice.

### Step 1: Implement executable condition semantics

- Add `src/problem2/training/conditions.py` with one explicit resolver for the
  six condition mappings above.
- Fix selected-refit dispatch in `scripts/run_g5_validation_tuning.py` so the
  actual inner job receives the selected condition.
- Connect fixed, rolling A*, nearest-feasible, urgency-priority, joint learned,
  and two-stage behavior to the physical execution path.
- Make `tests/g6/test_condition_semantics.py` pass without weakening its
  assertions.

### Step 2: Implement frozen checkpoint selection

- Add `src/problem2/evaluation/selection.py` or the equivalent shared module.
- Require exactly 50 rows for scenario IDs `20000-20049` for every candidate.
- Reject missing, duplicate, out-of-range, sealed, or mixed-identity rows.
- Keep all candidate rows in the selection record and apply the frozen
  tie-break order exactly.

### Step 3: Complete ledger and checkpoint recovery metadata

- Extend `src/problem2/experiments/ledger.py` with the required event fields.
- Extend `src/problem2/experiments/recovery.py` to accept and validate
  `expected_sha256` while preserving the previous valid checkpoint.
- Keep retries limited to the identical frozen identity; input drift must mark
  the job `stale`.

### Step 4: Extend freeze and dynamic manifest generation

- Update `src/problem2/training/selection.py` and `scripts/freeze_g5.py`.
- Bind the common source scope, scheduler order, storage estimate, GPU-hours
  estimate, `dynamic_pest_v1`, dynamic output root, deterministic evaluation,
  validation panel, and new evaluator hash.
- Generate Phase 2 development/replacement manifests only under:

  ```text
  outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/
  ```

- Do not call them the final G5 freeze. Phase 3 must revalidate affected work
  and persist the actual replacement freeze after source/evaluator changes are
  settled.

### Step 5: Implement the complete read-only preflight

- Put shared logic in a reusable source module, not in three duplicated CLI
  scripts.
- Verify the gate-critical frozen source, source scope, runner/recovery/
  checkpoint-validator/evaluator availability, dynamic ecology/root,
  scheduler/resource estimates, disk headroom, validation range, restricted
  experiment families, sealed lock, and runtime/hardware inventory.
- A failed preflight must start no process and create no queue.
- Preflight must remain read-only with respect to validation and sealed data.

### Step 6: Replace the three blocking/import-unsafe entry scripts

Replace these with thin, import-safe wrappers over the shared code:

```text
scripts/run_g6_jobs.py
scripts/resume_g6_jobs.py
scripts/preflight_g6.py
```

Importing a script must not run preflight, print gate output, mutate the sealed
lock, or raise `SystemExit`. Each script must expose callable `main()` and use
the normal `if __name__ == "__main__"` guard.

Phase 2 may implement and test orchestration paths, but it must not invoke them
for a real training or validation job.

### Step 7: Turn focused tests GREEN and run scoped regression

Required Phase 2 verification sequence:

```powershell
python -m pytest tests/g6 -q --tb=short
python -m pytest <affected G3-G5 test paths> -q --tb=short
python -m compileall -q src scripts
git diff --check
```

Choose the affected G3-G5 paths from the modules actually changed. Do not run
unrelated expensive checks after every small edit. Run a broader relevant
regression once after the focused suite is GREEN.

### Step 8: Review, persist, and update state

- Review the final diff against the Phase 1 tests and G6 design.
- Record unresolved limitations honestly.
- Commit the Phase 2 content with an explicit message and push the branch.
- Update `docs/PROJECT_STATE.md` with the test evidence, pushed content commit,
  and next authorized work.
- Push the state record before starting Phase 3.

Do not start Phase 3 pilots automatically. The next conversation should stop
after Phase 2 is implemented, reviewed, tested, pushed, and recorded unless the
user explicitly asks it to continue.

## 8. Likely Files For Phase 2

Prefer existing boundaries and small shared modules:

```text
src/problem2/training/conditions.py             new condition resolver
src/problem2/training/selection.py              formal freeze payloads
src/problem2/training/physical_training.py      real condition execution
src/problem2/experiments/ledger.py               event metadata/state replay
src/problem2/experiments/recovery.py             expected hash/recovery
src/problem2/experiments/orchestrator.py         shared job lifecycle
src/problem2/evaluation/selection.py             frozen checkpoint selection
src/problem2/evaluation/runner.py                deterministic validation
src/problem2/evaluation/validator.py             complete-row validation
scripts/run_g5_validation_tuning.py              selected-refit dispatch fix
scripts/freeze_g5.py                             dynamic replacement payloads
scripts/run_g6_jobs.py                           thin entry point
scripts/resume_g6_jobs.py                        thin entry point
scripts/preflight_g6.py                          thin entry point
```

This is a map, not permission for a broad rewrite. Touch only what the focused
contracts and their direct integration require.

## 9. Verification Economy: Required, Not Excessive

The user explicitly prefers fewer unnecessary hashes and less defensive
overengineering. Apply that preference without removing evidence-chain or gate
requirements.

Keep these checks because they are gate-critical:

- one source commit/source-scope binding for the frozen workload;
- the evaluator hash after evaluator/runner code changes;
- checkpoint hash validation for atomic recovery and selected evidence;
- frozen manifest/config/protocol hashes required by canonical identity;
- one local/upstream/remote parity check before a gate is recorded;
- validation-range and sealed-lock checks.

Avoid these patterns:

- hashing every temporary file or recomputing the same unchanged hash at every
  helper boundary;
- repeating identical Git parity checks after every small edit;
- adding multiple overlapping validators for one already-covered invariant;
- broad fail-closed abstractions unrelated to a Phase 1 failure;
- adding fallback/retry layers that conceal a real failed attempt;
- rerunning the full repository suite after every small change;
- preserving an old hash merely to avoid regenerating the correct dynamic
  freeze.

The right Phase 2 shape is a small shared implementation whose focused tests
prove the required behavior, followed by one proportionate regression pass.

## 10. Absolute Do-Not-Repeat Rules

1. Do not run a formal G6 job in Phase 2.
2. Do not run validation scenarios to manufacture selection evidence in Phase
   2; implement and test the behavior with test fixtures only.
3. Do not access any sealed scenario ID or content in `30000-30099`.
4. Do not unlock G7. Actual unlock count must remain `0`.
5. Do not modify or relabel historical
   `outputs/problem2_sr_mappo_v1/g5/` evidence.
6. Do not write new dynamic evidence outside
   `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/`.
7. Do not retain the evaluator hash currently bound to the blocking runner
   stub after replacing that path.
8. Do not treat old preflight `all_pass=true`, a dry-run, import success, or a
   smoke test as formal authorization.
9. Do not pass `sr_mappo_mobile` internally and relabel the result as fixed,
   A*, nearest, urgency, or two-stage.
10. Do not weaken, skip, mark xfail, or rewrite the Phase 1 tests merely to
    obtain GREEN.
11. Do not enable battery replenishment.
12. Do not run ablation or sensitivity for methods other than exactly
    `sr_mappo_mobile`.
13. Do not alter budgets, scenario ranges, checkpoint-selection rules, or
    statistics after validation access. Issue a replacement freeze instead.
14. Do not delete, average away, overwrite, or silently retry unfavorable or
    failed artifacts.
15. Do not treat a Windows checkpoint `PermissionError` as success. Record it
    as failure and recover only the same identity.
16. Do not create another worktree and do not touch the existing detached
    `Second-tdd-clean` worktree.
17. Do not use `git add .`, `git add -A`, `git clean`, force-push,
    `git reset --hard`, or destructive checkout commands.
18. Do not modify the protected first-problem repository, base project/OSM
    inputs, planning evidence, or external Word thesis files.
19. Do not stage, delete, or clean the pre-existing untracked directories.
20. Do not claim Phase 2 complete until its content and state record are pushed
    and `docs/PROJECT_STATE.md` names the next authorized action.

## 11. Protected External Assets

Do not modify these without a later explicit user instruction:

```text
C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper
D:/Pycharm/Locust_rl
C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析
existing Word thesis files outside this repository
OSM source files
```

The first-problem repository contains protected user work related to SR-MAPPO
reward sensitivity. Never mix it into Problem 2.

## 12. Existing Untracked Directories To Preserve

At the Phase 2 baseline, `git status --short --branch` reported a clean tracked
tree plus these pre-existing untracked directories:

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
tmp-res2/
tmp-smoke-review-fix-resume/
tmp-smoke-review/
tmp-smoke/
tmp-task11-cli/
tmp-task12-repro/
```

Treat them as user/generated state. Leave them untouched and unstaged. If the
status contains additional changes at the start of the next conversation,
inspect them and work with them; never revert them automatically.

## 13. Startup Checklist For The Next Conversation

Read these first:

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw docs/PROJECT_STATE.md
Get-Content -Raw HANDOFF_G6_READINESS_PHASE1.md
Get-Content -Raw docs/audits/g6-readiness-phase1-red.md
Get-Content -Raw docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md
```

Then inspect the checkout:

```powershell
git status --short --branch
git log -3 --oneline --decorate
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/codex/problem2-dynamic-pest-model
```

Run the focused baseline:

```powershell
python -m pytest tests/g6 -q --tb=short
```

Expected baseline before Phase 2 edits:

```text
30 failed, 10 passed
```

Stop and reconcile against `docs/PROJECT_STATE.md` if:

- the branch or tracked files differ unexpectedly;
- Phase 2 production implementation already exists but is not recorded;
- validation or sealed content appears to have been accessed;
- the RED failure groups materially differ from this handoff;
- the authoritative state names a different next action.

Otherwise, begin Phase 2 at Step 1: executable condition semantics.

## 14. Phase 2 Definition Of Done

Phase 2 is complete only when all of the following are true:

- all six conditions execute their intended controller/training semantics;
- selected refit forwards the real condition rather than relabeling mobile;
- frozen checkpoint selection uses complete `20000-20049` rows and the exact
  tie-break rule;
- ledger/recovery contains required attempt metadata and validates the
  expected checkpoint hash;
- dynamic replacement manifests contain source scope, scheduler order,
  storage/GPU estimates, ecology/root, deterministic evaluation, validation
  panel, and a new evaluator hash;
- run/resume/preflight scripts are import-safe thin entry points;
- the complete G6 read-only preflight contract exists;
- `tests/g6` is GREEN;
- affected G3-G5 regression, compileall, and diff checks pass;
- no experiment, validation payload, sealed payload, or protected external
  asset was accessed;
- review found no blocking runner/recovery/evaluator defect;
- Phase 2 content and state commits are pushed and recorded in
  `docs/PROJECT_STATE.md`.

After Phase 2, the project remains at `M2`. The next gate is Phase 3 dynamic
G3-G5 revalidation and replacement freeze, not formal execution.

## 15. Later Work, Not Authorized Yet

After Phase 2 is complete and recorded:

1. Phase 3 reruns affected dynamic G3-G5 validation/pilot/refit work.
2. Actual pilot jobs run one at a time; show each completed result to the user
   before starting the next.
3. Phase 3 generates and persists the replacement dynamic G5 freeze with the
   final source/evaluator bindings, scheduler order, storage estimate, GPU
   estimate, statistics, and checkpoint-selection rule.
4. Phase 4 runs the full read-only preflight on the exact pushed freeze.
5. Only after that preflight passes may the first formal job be considered:

   ```text
   sr_mappo_mobile / g20x20_d2 / training seed 42
   ```

6. Stop after that one job and show the user the diagnostics before any next
   formal job.

The known target matrix after a valid replacement freeze is `375` unique
training jobs, but the number is not permission to queue them now.

## 16. Evidence Chain To Preserve

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

Training completion alone is not a thesis result. G6 does not authorize method
ranking or superiority claims; sealed evaluation and locked paired inference
belong to G7.
