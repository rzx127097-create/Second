# Handoff: G5 Task12 Complete, G6 Execution Not Ready

Date: 2026-08-28

Repository: `C:/Users/RZX/Documents/ChatGPT/Second`

Branch: `codex/problem2-g5-pilot-freeze`

Remote: `origin/codex/problem2-g5-pilot-freeze`

Current local HEAD, upstream HEAD, and remote branch HEAD:
`93fa732c60196e3ffb3b59d035a80edb1a7db138`

## 1. Read This First

This handoff is for a new conversation with no prior context. The project is
the thesis second problem: road-constrained air-ground heterogeneous
cooperative pesticide spraying with multiple UAVs and one mobile pesticide
replenishment vehicle. The public flagship method name is **SR-MAPPO**.
Problem 2 is an air-ground heterogeneous extension of SR-MAPPO.

The immediate task is **G6 readiness remediation**, not G6 formal execution.
G5 Task12 generated and froze the validation, refit, G6, and G7 planning
artifacts, but the G6 execution and recovery entry points are still deliberate
blocking stubs. Do not start formal G6 jobs from this state.

Read these files before doing anything:

1. `AGENTS.md`;
2. `docs/PROJECT_STATE.md`;
3. this file, `HANDOFF_G6_READINESS.md`;
4. `HANDOFF_TASK12.md` for the Task12 execution history;
5. `docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md`;
6. `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, G5 Task12 and
   the G6-related orchestration sections;
7. `docs/audits/g5-pilot-freeze-compliance.md`;
8. `docs/PROJECT_STATE.md` sections for G4, G5, and Task12.

`docs/PROJECT_STATE.md` remains the authoritative dynamic project-state record.
Older `HANDOFFG6.md` is historical and currently describes an earlier G5
Task 6 handoff. Do not treat it as the current G6 implementation status.

## 2. Research Identity And Hard Boundaries

- Use the public name `SR-MAPPO`.
- Describe the method as the air-ground heterogeneous extension of SR-MAPPO.
- Do not introduce HAPPO or rename the method to `AG-SR-MAPPO`.
- Pesticide is the only replenished resource.
- Battery replenishment is inactive until a separate activation audit is
  authorized, passed, and persisted.
- OSM/GraphML is read-only road-constrained simulation input, not evidence of
  real field deployment.
- Keep all Problem-2 outputs below `outputs/problem2_sr_mappo_v1`.
- Do not modify the first-problem repository, `D:/Pycharm/Locust_rl`, OSM
  inputs, planning evidence, or external Word thesis files.
- Do not access sealed scenario content during G6 readiness work or G6.
- At the current maturity boundary `M2`, do not claim efficacy, superiority,
  statistical significance, or real deployment verification.

## 3. Current Gate And Conclusion

Current highest research maturity: `M2`, implementation and scoped mechanism
evidence.

G5 Task12 is persisted as a validation-process and development-refit freeze.
The G6 formal gate is **NOT READY for execution**. The project may proceed to
repair and verify the G6 entry system, but it must first reopen the G5 freeze
because changing G6 runner, evaluator, recovery, or preflight code changes the
frozen source/evaluator hash boundary.

The key distinction is:

```text
G5 freeze artifacts exist and pass their current checks
!=
the G6 training/recovery/evaluation executors are implemented and authorized
```

No G6 formal training has been started. No G7 sealed evaluation has been
unlocked. No sealed scenario content has been read.

## 4. What Has Been Completed

### G0-G4 foundation

- Repository isolation, evidence registries, source and parameter lineage,
  partition contracts, output-root rules, and sealed lock were established.
- Offline road topology, projection, physical movement, request/reservation/
  service state transitions, pesticide transfer, conservation, deterministic
  replay, and road-cache provenance passed G2 validation.
- Heterogeneous UAV and vehicle actors, centralized critic, masks, GAE,
  normalization, checkpoint round trip, resume, and deterministic evaluation
  passed G3 acceptance.
- Pesticide-only onboard scarcity and mobile/fixed support probes were audited
  in G4. These are mechanism diagnostics, not learned-policy efficacy evidence.

### G5 Task11 and Task12 evidence

- Development pilot: `2` scales x `5` learning methods x `17` conditions x
  `3` development seeds = `510` physical training jobs.
- Development scenario-reference records: `510` jobs x `20` development
  scenario references = `10200` records. These are descriptive references,
  not 10200 independent experiments.
- Selected development budget: `200000` environment interactions per training
  identity, checkpoint interval `10000`, checkpoint count `20`.
- Validation tuning: `20` frozen candidates x `3` training seeds x `50`
  validation scenarios = exactly `3000` action-driven validation rows.
- Validation technical failures: `0`.
- Every candidate had `success_probability=0.0`. Retain this as a weak/negative
  diagnostic only. It is not a formal ranking, efficacy result, superiority
  result, or significance result.
- Mechanical selected candidates:
  - `sr_mappo_mobile = c02`
  - `mappo_mobile = c01`
  - `ippo_mobile = c01`
  - `maddpg_mobile = c04`
  - `iql_mobile = c03`
- Selected-configuration development refit: `510` physical jobs and `10200`
  development scenario-reference rows. Validation and sealed access are false
  in the refit records.
- G6 plan: `150` base jobs, `375` unique training jobs, and `375000`
  validation evaluation identities (`375` jobs x `20` checkpoints x `50`
  validation scenarios).
- G7 plan: `42500` sealed evaluation identities. It contains no sealed
  scenario content and no evaluation results.
- Sealed lock: maximum unlock count `1`, actual unlock count `0`.

### Important hashes

- Candidate manifest:
  `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`
- Pilot budget manifest:
  `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`
- Sealed lock:
  `78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226`
- Frozen source scope:
  `9a6a9baf960d86f94ba391cef60116d0ab33fb8b8c965c30a2e7f38e9308def4`
- Task12 content commit:
  `9965860ca8d92678d01240c57be4dc887f779760`, subject
  `feat: freeze g5 fair-pilot experiment system`.
- Current persistence commit:
  `93fa732c60196e3ffb3b59d035a80edb1a7db138`, subject
  `docs: record g5 freeze persistence`.

The content commit and persistence commit were pushed without force-push.
Local, upstream, and remote currently agree at `93fa732...`. The current
`PROJECT_STATE.md` records the content commit and parity before the persistence
commit, but does not explicitly record the persistence commit's own hash and
post-push parity. This is a governance-record gap to close in the next state
update.

## 5. Verification Already Completed

Fresh checks on the current persisted state include:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5 -q`: `428 passed`.
- `python -m pytest -q` in the documented host environment: `727 passed`.
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts`: exit `0`.
- `.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py`: `status=pass`,
  `validation_accessed=false` in the audit view, `sealed_accessed=false`, and
  `actual_unlock_count=0`.
- `.venv-g5/Scripts/python.exe scripts/validate_g5_artifacts.py --root
  outputs/problem2_sr_mappo_v1/g5 --dry-run`: completed without executing jobs.
- `.venv-g5/Scripts/python.exe scripts/freeze_g5.py --check-only`: `status=pass`
  under the current G5 freeze implementation.
- `git diff --check`: passed.
- Local/upstream/remote parity: passed.

The exact `.venv-g5` lock intentionally does not include legacy Chapter 4.2
document-rendering dependencies such as `PIL` and `matplotlib`. Therefore a
repository-wide pytest collection in that environment can fail during old
document tests; use the documented host environment for the full regression.
Do not mutate the frozen G5 environment just to remove this known difference.

## 6. Confirmed G6 Blockers And Omissions

### P1: Formal runner and recovery are blocking stubs

Current files:

- `scripts/run_g6_jobs.py:1` calls `run_cli("run_g6_jobs", blocked_reason=...)`.
- `scripts/resume_g6_jobs.py:1` calls `run_cli("resume_g6_jobs", blocked_reason=...)`.
- `scripts/preflight_g6.py:6` also exits through the blocked CLI path when
  invoked as a script.
- `scripts/_g5_cli.py:169-190` is a G5 dry-run guard and returns exit code `2`
  whenever a G6/G7 blocked reason is supplied.

Consequently, `run_g6_jobs.py` cannot start a formal process and
`resume_g6_jobs.py` cannot recover one. A passing static preflight does not
change this fact.

### P1: Evaluator hash is bound to the blocking stub

The top-level `evaluator_hash` in
`outputs/problem2_sr_mappo_v1/g5/manifests/g6-validation-evaluations.json`
is:

`ed10dad7adaa0cbc16a33ad72676d507e05299d3934cef019bccb4b7ef943f74`

This is the SHA-256 of the current `scripts/run_g6_jobs.py` blocking stub. A
real runner/evaluator must never be substituted under this old hash. Any
runner, evaluator, recovery, or preflight implementation change requires a
new source/evaluator hash, a new G5 audit, regenerated affected manifests,
and a new content plus persistence record before formal execution.

### P2: Preflight does not implement the full G6 entry contract

`scripts/_g5_cli.py:36-166` currently checks only a limited static subset. It
does not strictly verify all of the following required by
`docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md:28-49`:

- exact frozen Git commit binding, rather than only local/upstream/remote
  parity;
- complete G5 test and audit evidence on the source being executed;
- required storage for the full formal workload plus atomic temporary writes;
- complete visible hardware/runtime inventory, including GPU model, VRAM,
  CPU, RAM, OS, Python, PyTorch, and CUDA details;
- actual runner, recovery, checkpoint validator, and validation evaluator
  availability;
- all required G6-specific manifest and artifact hashes.

The present `all_pass=true` result means only that the limited static checks
passed. It is not a G6 authorization signal.

### P2: Frozen G6 workload lacks required resource fields

`outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json` has correct
counts and identities, but no explicit top-level fields for:

- `scheduler_order`;
- `expected_storage_bytes`;
- `expected_gpu_hours`.

The G6 design requires these estimates to be frozen and checked before queue
creation. The current disk check only requires at least `1 GB` free and is not
compared with a formal workload estimate.

### P2: G6 execution evidence model is not connected to an executable path

The design requires, under `outputs/problem2_sr_mappo_v1/g6/`:

- append-only job-state and attempt ledgers;
- atomic checkpoints and checkpoint manifests;
- raw training events and validation episode logs;
- selected-checkpoint records with validation justification;
- validated long tables and fail-closed audits;
- recovery, retry, and stale-job reports.

The repository contains supporting G5 ledger/orchestration components, but the
current G6 entry scripts do not connect them into a real formal execution and
recovery loop. Do not infer this loop from the presence of skeleton manifests.

### P2: Selected-refit condition semantics need a ruling

In `scripts/run_g5_validation_tuning.py`, `_run_selected_refit_job()` passes
the learning method as the physical runner's `condition_id`, then records the
outer pilot condition separately as `refit_condition_id` and
`refit_training_condition_id`. The physical runner itself validates and trains
the learning method identity.

This may be intentional: one selected learning checkpoint is being referenced
under each outer development condition. It may also mean that conditions such
as `sr_mappo_fixed`, `sr_mappo_astar`, `sr_mappo_nearest`, and
`sr_mappo_urgency` did not actually switch their vehicle controller. Before
G6, add a focused semantic test and make the interpretation explicit. If the
actual controller behavior is wrong, reopen G5, rerun the affected pilots, and
issue new hashes. Never silently relabel old refit outputs.

### P3: Current handoff/state wording can be misread

The state says G6 is the next authorized gate after persistence parity, while
the G6 scripts are still blocked. The next conversation must interpret this as
authorization to begin the G6 gate's readiness work, not authorization to run
formal jobs. Update `docs/PROJECT_STATE.md` after the next audit so this is
explicit. Also record the persistence commit hash and the post-push parity
check that the current state record omitted.

### P2: Validation-access status has two intentional but confusing layers

The design contracts such as `configs/problem2/g5/protocol.yaml` and
`docs/evidence/g5/checkpoint_selection.yaml` retain
`validation_accessed: false` as a pre-access/design declaration. Actual
Task12 validation access is recorded as `validation_accessed: true` in the
freeze manifest and validation-access ledger. This is not evidence corruption,
but an operator who reads only the contract audit can misread the state. The
next G5/G6 readiness update should expose an explicit actual-access field or
bind the audit output directly to the validation ledger, while preserving the
historical design declaration.

## 7. Next Authorized Work Plan

Do the following in order. Stop at the first failed item.

### Phase A: Preserve and isolate

1. Confirm `git status --short --branch`, current branch, HEAD, upstream HEAD,
   remote HEAD, and `git diff --check`.
2. Treat `93fa732...` as the current frozen starting point.
3. Use an isolated `codex/` readiness branch/worktree if implementing the
   runner separately. Do not stage existing untracked temporary directories.
4. Read the G6 design and the G5 experiment/statistics, checkpoint, exclusion,
   fairness, and sealed-lock contracts completely.

### Phase B: Write failing tests first

Before production code, add focused tests for:

- exact source commit and source-scope binding;
- rejection of dirty tracked trees and mismatched remote parity;
- runner/recovery/evaluator availability;
- frozen `scheduler_order`, storage bytes, GPU hours, and disk-budget check;
- immutable job identities and no duplicate canonical identities;
- append-only job and attempt state transitions;
- same-identity retry only, with stale-input rejection;
- atomic checkpoint write, reload, hash validation, and previous-valid
  checkpoint retention;
- deterministic validation evaluation on `20000-20049` only;
- no sealed scenario ID, sealed flag, or sealed content in any G6 path;
- selected-checkpoint rule and complete validation-row coverage;
- refit condition semantics and controller selection.

Run the new focused tests and record the expected RED failures before writing
the implementation. Use the existing tests and contracts as the style guide.

### Phase C: Implement the minimum real G6 closure

Use shared code rather than duplicating logic in CLI wrappers. The likely
implementation boundaries are:

- a real G6 runner module under `src/problem2/experiments/` or
  `src/problem2/training/`, reusing the accepted physical training and
  evaluation path;
- append-only ledger/recovery support in the existing experiment modules;
- a real frozen validation evaluator bound to the G6 validation manifest;
- `scripts/run_g6_jobs.py` and `scripts/resume_g6_jobs.py` as thin entry
  points over the shared implementation;
- `scripts/preflight_g6.py` as a read-only complete entry audit;
- explicit manifest generation/update for scheduler and resource estimates;
- G6-focused tests under `tests/g6/` or the repository's established test
  layout.

The runner must read the frozen manifest, verify all hashes before a job,
acquire the declared lease, run the exact frozen training identity, write
validated checkpoints atomically, run deterministic validation on the fixed
validation panel, and mark a job complete only after all expected records are
present. A failed job must preserve its attempt and be resumed only with the
same complete identity and frozen inputs.

### Phase D: Reopen and re-freeze G5

Any change to runner, evaluator, recovery, preflight, manifest generation,
condition semantics, or source-scope hashing invalidates the current G5 freeze
for G6 purposes. Therefore:

1. run focused RED/GREEN tests and independent review;
2. rerun affected G5 pilots or refit evidence when semantics changed;
3. regenerate affected G6/G7 planning manifests;
4. update evaluator, source, artifact, and dependency hashes;
5. run the complete G5 audit and freeze checks on the new clean commit;
6. update `docs/PROJECT_STATE.md` with the new content commit, test results,
   and explicit G6 readiness status;
7. push the content commit;
8. create and push a separate persistence commit;
9. record the persistence commit hash and post-push local/upstream/remote
   parity in the state record, using an additional docs-only record commit if
   needed to avoid self-referential hashing.

Do not carry the old `evaluator_hash` or old G6 manifest into a new runner.

### Phase E: G6 formal execution, only after readiness passes

Run the complete read-only preflight first. It must pass every check and
create no training process on failure. Then execute exactly the frozen `375`
unique training jobs, with the mandatory base matrix of `150` jobs:

```text
5 methods x 6 scales x 5 training seeds = 150 base jobs
150 base + 90 required Problem-2 + 60 heuristic
       + 25 remove-one + 50 sensitivity = 375 unique jobs
```

Methods:
`sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`, `maddpg_mobile`,
`iql_mobile`.

Training seeds: `42`, `123`, `2024`, `3407`, `7919`.

Validation scenarios: `20000-20049`.

Sealed scenarios: `30000-30099`, but these remain inaccessible during G6.

Scale horizons:

```text
g20x20_d2: 150
g20x30_d3: 180
g20x40_d3: 220
g30x30_d3: 220
g30x40_d4: 280
g30x50_d4: 350
```

The primary training budget is `200000` environment interactions per identity.
Training reward remains diagnostic; thesis conclusions must use fixed-scenario
evaluation and later locked statistics.

At G6 completion, validate all `375000` validation identities and produce the
G6 acceptance/persistence record. G6 completion does not authorize any method
superiority claim. Only after a successful G6 acceptance and a new persisted
state record may G7 perform its one permitted sealed unlock.

## 8. Absolute Do-Not-Repeat Rules

1. **Never run the current G6 scripts expecting execution.** They are blocking
   stubs and correctly return a refusal. Implement and test the real path first.
2. **Never replace a script while keeping its old evaluator hash.** Hash and
   freeze the actual implementation, then reopen G5 and regenerate manifests.
3. **Never treat `--dry-run` as execution.** A dry-run proves only that a guard
   ran and no jobs were started.
4. **Never access sealed content early.** Scenario IDs/hashes in planning
   manifests are metadata; no sealed scenario payload or result may be read.
5. **Never edit or regenerate candidates, the pilot budget, or validation rows
   after validation access.** The validation transition is one-way. If code or
   semantics change, create a new freeze with new hashes rather than altering
   old evidence.
6. **Never remove an unfavorable result.** The `success_probability=0.0`
   candidate results are retained and diagnosed.
7. **Never call development scenario references independent experiments.** The
   `10200` refit records are `510` jobs with descriptive scenario references.
8. **Never silently relabel outer conditions.** Confirm whether fixed, A*,
   nearest, urgency, and two-stage conditions execute distinct behavior. If
   not, repair the source semantics and rerun the affected G5 evidence.
9. **Never mix partial runs with old artifacts.** Preserve failed attempts,
   quarantine invalid outputs, and rerun the exact identity under frozen
   retry rules only.
10. **Never weaken clean-tree or hash guards to make tests pass.** Commit state
    documentation before provenance checks that require a clean tree.
11. **Never rewrite a recorded generation commit to current HEAD.** A recorded
    artifact generation commit may be an ancestor of the persistence commit;
    verify reachability and frozen source scope instead.
12. **Never use `git add .`, `git add -A`, `git clean`, force-push, destructive
    reset, or checkout commands.** Stage explicit paths only and preserve all
    user-owned untracked files.
13. **Never inspect or modify protected external assets**, including the first
    problem repository, `D:/Pycharm/Locust_rl`, OSM sources, planning evidence,
    or external Word files.
14. **Never assume a top-level file check proves nested job completeness.** G5
    pilot artifacts are nested one level below each outer identity; follow the
    recorded manifest paths.
15. **Never ignore the Windows checkpoint rename issue.** A transient
    `PermissionError` during atomic replacement requires preserving the failed
    attempt, diagnosing the lock, and rerunning the required identity or full
    matrix according to frozen retry rules.
16. **Never change the frozen G5 environment casually.** `.venv-g5` omits old
    document-rendering dependencies; use host Python for the documented full
    regression and `.venv-g5` for G5-specific checks.
17. **Never interpret a design-time `validation_accessed: false` field as proof
    that Task12 did not access validation.** Check the freeze manifest and
    validation ledger for actual access, while keeping sealed access at zero.

## 9. Existing Untracked Items

These existed before this handoff and are out of scope. Do not inspect,
modify, stage, delete, or clean them:

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

The current tracked worktree is clean. Use explicit `git status` checks and do
not let these untracked paths enter a commit.

## 10. Definition Of Success For The Next Conversation

The next conversation has not completed G6 merely by implementing a runner.
It must first produce a new, independently reviewed, tested, committed, and
pushed G5 freeze whose preflight can prove that the actual runner, evaluator,
recovery path, workload estimates, hardware inventory, hashes, and ledgers are
ready. Only then may formal G6 jobs begin.

The next state update must report:

- highest maturity actually supported;
- exact changed files and new hashes;
- RED/GREEN and full regression results;
- source/content/persistence commit hashes and post-push parity;
- whether any G6 job or sealed scenario was accessed;
- unresolved condition-semantics or external-evidence issues;
- the first failed gate if readiness is not complete;
- permitted claims, still limited conservatively until G7 evidence exists.
