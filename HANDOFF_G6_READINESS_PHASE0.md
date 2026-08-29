# G6 Readiness Handoff: Dynamic Ecology, Phase 0 Complete

Date: 2026-08-29

This document is the current handoff for a new conversation. Read it together
with `AGENTS.md`, `docs/PROJECT_STATE.md`, and
`HANDOFF_G6_READINESS.md`. `docs/PROJECT_STATE.md` is authoritative when any
older handoff wording conflicts with the current dynamic project state.

## 1. Repository And Current Task

Repository:

```text
C:/Users/RZX/Documents/ChatGPT/Second
```

Current branch:

```text
codex/problem2-dynamic-pest-model
```

Starting commit for this handoff:

```text
2b6edad410a8cb455ceee0ec5b04cda502b31e68
```

Remote:

```text
https://github.com/rzx127097-create/Second.git
```

The research problem is road-constrained air-ground heterogeneous cooperative
pesticide spraying with a mobile pesticide replenishment vehicle. The public
flagship algorithm name is **SR-MAPPO**. Problem 2 is an air-ground
heterogeneous extension of SR-MAPPO.

The immediate task is **G6 readiness remediation**, not formal G6 execution.
The current G6 runner, resume entry point, and CLI preflight are not yet a
complete executable formal system. The next work must therefore repair and
test the entry system before any formal job is started.

## 2. Non-Negotiable Research Decisions

These decisions were explicitly made for all future work:

- Every future primary, formal, ablation, sensitivity, and sealed experiment
  uses the dynamic ecology environment `dynamic_pest_v1`.
- Static ecology is historical diagnostic evidence only. It must not be reused
  as current pilot or formal evidence, and old static output must not be
  relabeled as dynamic output.
- All new outputs belong below:

  ```text
  outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
  ```

- Ablation and sensitivity experiments are restricted to exactly
  `sr_mappo_mobile`.
- No ablation or sensitivity experiment may be run for `mappo_mobile`,
  `ippo_mobile`, `maddpg_mobile`, or `iql_mobile`.
- Pesticide is the only replenished resource.
- Battery replenishment is disabled. It cannot be activated without a separate
  activation audit and a recorded project-state decision.
- OSM road data is a road-constrained simulation input, not evidence of field
  deployment.
- No efficacy, superiority, significance, real-deployment, or universal-
  optimality claim is allowed at the current maturity boundary `M2`.
- Training reward is diagnostic only. Thesis conclusions must use fixed-scenario
  evaluation metrics and the later locked paired statistical summary.

## 3. Two Naming Systems

Do not confuse the overall research gates with the internal G6 readiness
phases.

Overall research gates:

```text
G0 -> G1 -> G2 -> G3 -> G4 -> G5 -> G6 -> G7 -> G8
```

Current G6 readiness phases, using the user-facing numeric names from now on:

| Numeric phase | Handoff label | Purpose | Experiment execution |
|---|---|---|---|
| Phase 0 | Phase A | Preserve/isolate state and audit entry conditions | No |
| Phase 1 | Phase B | Write and run failing G6 readiness tests | No |
| Phase 2 | Phase C | Implement the real runner, recovery, evaluator, and preflight | No |
| Phase 3 | Phase D | Revalidate dynamic G3-G5 and create a replacement G5/G6 freeze | Pilot jobs may occur, one at a time |
| Phase 4 | Phase E | Run complete preflight, then formal G6 jobs | Yes, one job at a time |

Phase 0 is complete. The next authorized work is **Phase 1**, not the first
formal experiment.

## 4. What Has Been Completed

### 4.1 Historical gates and implementation evidence

The repository contains recorded implementation and bounded evidence for the
following historical work:

- G2 deterministic road topology, physical scale, service state machine,
  resource conservation, and replay validation.
- G3 heterogeneous MARL interfaces, role actors, centralized critic, masks,
  GAE, normalization, checkpoint round trip, and bounded development smoke.
- G4 pesticide-only UAV scarcity and mobile/fixed support mechanism probes.
- G5 pilot, validation-tuning, refit, and planning artifacts from the previous
  freeze.

These records remain at maturity `M2` unless a later project-state entry
explicitly promotes the maturity. They do not authorize formal claims.

### 4.2 Dynamic ecology revalidation

The dynamic ecology integration and bounded lineage/test corrections are
recorded in `docs/PROJECT_STATE.md` and the commits below:

- `8e1a36a`: integrate dynamic ecology with physical spraying;
- `ca59bbd`: reconcile dynamic validation and state restore;
- `3c34528`: persist dynamic validation provenance;
- `af0c0b1`: enforce the dynamic ecology evidence contract;
- `a1f0a23`: enforce dynamic ecology output lineage;
- `a827726`: reconcile dynamic G4 lineage audits;
- `465aac3`: record dynamic revalidation closure.

The latest recorded dynamic checks include:

- ecology/G3/G4/G5 targeted suite: `707 passed`;
- G5 suite: `434 passed`;
- repository-wide suite: `865 passed`;
- G4 mechanism audit: `status=pass`;
- G4 lineage audit: `status=pass`;
- `python -m compileall -q src scripts`: exit `0`;
- `git diff --check`: pass.

These are implementation and bounded development-scope checks. They are not
formal treatment-efficacy results.

### 4.3 Current Phase 0 audit

The Phase 0 audit was recorded in `docs/PROJECT_STATE.md` and pushed in:

- `fc12e389754b2017c53ebed4704d2fd370b718e8`:
  `docs: record g6 readiness phase 0 audit`;
- `2b6edad410a8cb455ceee0ec5b04cda502b31e68`:
  `docs: record phase 0 persistence hash`.

At the end of this session:

- local HEAD, upstream HEAD, and remote HEAD all equal
  `2b6edad410a8cb455ceee0ec5b04cda502b31e68`;
- tracked working tree and index are clean;
- `git diff --check` passes;
- existing untracked temporary directories remain untouched and unstaged;
- no G6 formal job was started;
- no G7 sealed evaluation was unlocked;
- no validation scenario content or sealed scenario content was accessed;
- protected external repositories, OSM inputs, historical static outputs, and
  external Word files were not modified.

The current checkout is a normal authoritative checkout. An existing detached
worktree named `Second-tdd-clean` is outside this task and must remain
untouched.

## 5. Why G6 Formal Execution Is Still Blocked

The current G6 design is in
`docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md`. Its entry
contract is stricter than the current scripts.

Known blockers from `HANDOFF_G6_READINESS.md`:

1. `scripts/run_g6_jobs.py` is a blocking stub.
2. `scripts/resume_g6_jobs.py` is a blocking stub.
3. `scripts/preflight_g6.py` still routes through the blocking G5 CLI guard
   when invoked as a CLI.
4. The existing evaluator hash is bound to the blocking stub. A new evaluator
   or runner must receive new hashes; the old hash must never be retained.
5. Current preflight does not fully verify exact frozen commit binding,
   complete G5 evidence, hardware/runtime inventory, storage estimates, or
   actual runner/recovery/evaluator availability.
6. The current G6 training manifest lacks frozen `scheduler_order`,
   `expected_storage_bytes`, and `expected_gpu_hours` fields.
7. Existing ledger, recovery, checkpoint, and orchestration components are not
   connected to one complete executable G6 loop.
8. The selected-refit condition semantics still need a focused test. Fixed,
   A*, nearest, urgency, and two-stage conditions must be shown to change the
   intended controller/training behavior rather than only changing labels.
9. Any change to runner, recovery, evaluator, preflight, manifest generation,
   or condition semantics invalidates the previous G5 freeze for G6 purposes.
   A new dynamic G5 freeze is required before formal execution.

Never interpret a dry-run or a limited static preflight as G6 authorization.

## 6. Next Work Plan

### Phase 1: Write RED readiness tests

Add focused tests under the established G6 test area, preferably
`tests/g6/`. Use existing tests and contracts as the style guide. The tests
must cover:

- exact source commit and source-scope binding;
- dirty tracked-tree rejection and local/upstream/remote mismatch rejection;
- runner, recovery, checkpoint validator, and validation evaluator
  availability;
- frozen scheduler order, storage bytes, GPU hours, and disk-budget checks;
- immutable canonical job identities and duplicate rejection;
- append-only job and attempt transitions;
- same-identity retry only and stale-input rejection;
- atomic checkpoint writing, reload/hash validation, and retention of the
  previous valid checkpoint;
- deterministic validation limited to `20000-20049`;
- rejection of any sealed scenario ID, sealed flag, or sealed content in G6;
- frozen selected-checkpoint rule and complete validation-row coverage;
- condition/controller semantics for fixed, A*, nearest, urgency, and
  two-stage conditions;
- dynamic ecology binding and output-root confinement;
- exact `sr_mappo_mobile` restriction for ablation and sensitivity families.

Run the focused tests against the current implementation and record the
expected RED failures. Do not start training to produce this result. The RED
report should identify the missing contracts precisely.

The Phase 1 deliverable is the tests plus a verification record. Commit and
push it before Phase 2 begins, and update `docs/PROJECT_STATE.md` with the
commit, test command, failure count, and remaining blockers.

### Phase 2: Implement the real G6 closure

Implement shared library code and keep the CLI scripts thin. Likely areas are:

- `src/problem2/experiments/ledger.py`;
- `src/problem2/experiments/recovery.py`;
- `src/problem2/experiments/orchestrator.py`;
- `src/problem2/training/physical_training.py`;
- `src/problem2/evaluation/runner.py`;
- `src/problem2/evaluation/validator.py`;
- a new G6 runner/evaluator module under `src/problem2/experiments/` or
  `src/problem2/training/`;
- thin wrappers in `scripts/run_g6_jobs.py`,
  `scripts/resume_g6_jobs.py`, and `scripts/preflight_g6.py`.

The real runner must:

1. read the frozen manifest;
2. verify all source/config/protocol/scenario/evaluator hashes;
3. reject sealed access and wrong ecology/output roots;
4. acquire the declared lease without duplicate workers;
5. execute the exact canonical training identity;
6. write training records and checkpoints atomically;
7. run deterministic validation on the frozen project panel `20000-20049`;
8. validate all expected rows and artifacts;
9. mark a job complete only after the complete evidence set exists;
10. preserve failed attempts and allow only identical-identity retries.

Phase 2 is implementation and test work, not formal scientific evidence.

### Phase 3: Reopen and refreeze dynamic G5

Because Phase 2 changes the source/evaluator boundary, the previous G5 freeze
cannot be reused. Do the following in order:

1. run the focused RED/GREEN tests and an independent code review;
2. rerun any affected dynamic G3-G5 validation, pilot, refit, or condition
   semantics work;
3. keep all actual pilot jobs sequential; after each complete job, show the
   user its result and wait for confirmation before starting another;
4. regenerate G6 and G7 planning manifests under the dynamic output root;
5. freeze scheduler order, storage estimate, GPU estimate, hashes, statistics,
   and checkpoint selection;
6. run the complete dynamic G5 audit and freeze checks on a clean commit;
7. push a content commit and then a separate persistence/state-record commit;
8. record both hashes and post-push parity in `docs/PROJECT_STATE.md`.

No old static candidate, old evaluator hash, old G6 manifest, or old static
pilot result may be silently carried forward.

### Phase 4: Preflight, then one formal job

Only after the replacement dynamic G5 freeze is pushed and recorded:

1. run the complete read-only G6 preflight;
2. if any check fails, start no training process;
3. if preflight passes, run exactly one formal job:

   ```text
   sr_mappo_mobile / g20x20_d2 / training seed 42
   ```

4. stop after that one job;
5. show the user training diagnostics, dynamic ecology confirmation,
   pesticide/resource accounting, validation result, checkpoint selection,
   recovery/provenance result, and artifact hashes;
6. wait for explicit confirmation before starting the next job.

The first formal job is not authorized merely because its name is known. It is
authorized only after Phase 1, Phase 2, Phase 3, the replacement freeze, and
the complete preflight all pass.

## 7. Frozen Formal Matrix After Readiness

The target formal matrix, after a new dynamic G5 freeze, is:

```text
150 base jobs
+ 90 SR-MAPPO fixed/A*/two-stage jobs
+ 60 SR-MAPPO nearest/urgency jobs
+ 25 SR-MAPPO remove-one ablation jobs
+ 50 SR-MAPPO algorithmic-sensitivity jobs
= 375 unique jobs
```

Base methods:

```text
sr_mappo_mobile
mappo_mobile
ippo_mobile
maddpg_mobile
iql_mobile
```

Base scales and maximum physical decision steps:

| Scale | Maximum physical decision steps |
|---|---:|
| `g20x20_d2` | 150 |
| `g20x30_d3` | 180 |
| `g20x40_d3` | 220 |
| `g30x30_d3` | 220 |
| `g30x40_d4` | 280 |
| `g30x50_d4` | 350 |

Training seeds:

```text
42, 123, 2024, 3407, 7919
```

Training budget: `200000` environment interactions per canonical training
identity, with approximately `20` checkpoints at `10000` interaction
intervals, subject to the replacement dynamic freeze.

Validation scenario seeds: `20000-20049` only.

Sealed-test scenario seeds: `30000-30099`; inaccessible during readiness and
G6. The G7 sealed lock allows one unlock at most, and actual unlock count is
currently `0`.

Primary success threshold: `reduction_rate >= 0.85`.

## 8. Evidence Chain Required For Every Formal Result

Do not accept or report a formal result unless this complete chain exists:

```text
source parameter/literature
-> frozen configuration and Git commit
-> canonical run identity and raw episode log
-> validated long-format table
-> paired statistical summary
-> figure/table artifact manifest
-> thesis statement
```

Every identity must bind method, scale, training seed, config hash, Git commit,
experiment family, condition, protocol hash, checkpoint hash, partition,
scenario panel hash, deterministic-policy flag, and evaluator hash as required
by the G6 design.

Training completion alone is not a thesis result. G6 does not authorize method
ranking or superiority claims; sealed evaluation and locked paired inference
belong to G7.

## 9. Absolute Do-Not-Repeat Rules

1. Do not run the current `scripts/run_g6_jobs.py` or
   `scripts/resume_g6_jobs.py` expecting formal execution. They are blocking
   stubs until Phase 2 replaces and tests the real path.
2. Do not treat `--dry-run` as execution or authorization.
3. Do not retain the old evaluator hash after changing runner/evaluator code.
4. Do not reuse or relabel static G5 output as `dynamic_pest_v1` evidence.
5. Do not access sealed scenario payloads, scenario files, or sealed results
   during readiness, G5, or G6.
6. Do not use validation scenario IDs outside `20000-20049`.
7. Do not run ablation or sensitivity for any method other than
   `sr_mappo_mobile`.
8. Do not enable battery replenishment; pesticide is the only active resource.
9. Do not silently relabel fixed/A*/nearest/urgency/two-stage conditions. Test
   the actual controller behavior and rerun affected evidence if semantics are
   wrong.
10. Do not interpret training reward, a smoke run, a dry-run, or a mechanism
    probe as formal efficacy or superiority evidence.
11. Do not treat descriptive development scenario references as independent
    experiments.
12. Do not change frozen candidates, validation rows, budget, statistics, or
    manifests in place after validation access. Create a replacement freeze
    with new hashes.
13. Do not manually overwrite, average, or delete unfavorable or failed raw
    artifacts. Preserve attempts and quarantine invalid outputs.
14. Do not weaken clean-tree, hash, partition, or sealed-lock guards to make a
    test pass.
15. Do not use `git add .`, `git add -A`, `git clean`, force-push,
    `git reset --hard`, or destructive checkout commands.
16. Do not stage or modify the existing untracked directories, including
    `_tmp_docx_assets/`, G5 `_debug/` and `quarantine/`, and the listed
    `tmp-*` directories.
17. Do not modify protected external assets:
    `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`,
    `D:/Pycharm/Locust_rl`, planning evidence, OSM source files, or external
    Word thesis files.
18. Do not ignore the Windows checkpoint rename/lock issue. A transient
    `PermissionError` during atomic replacement is a failed attempt requiring
    diagnostics and identical-identity recovery.
19. Do not run formal jobs in parallel. One completed job must be shown to the
    user before the next job begins.

## 10. First Action For The Next Conversation

The next conversation should read:

```powershell
Get-Content -Raw docs/PROJECT_STATE.md
Get-Content -Raw HANDOFF_G6_READINESS_PHASE0.md
Get-Content -Raw HANDOFF_G6_READINESS.md
git status --short --branch
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/codex/problem2-dynamic-pest-model
```

Then begin **Phase 1** by writing the focused G6 readiness tests and running
only those tests to produce the RED report. Do not start an experiment in that
step. Do not run the first formal job until the new dynamic G5 freeze and full
G6 preflight have passed.

## 11. Definition Of Readiness Completion

G6 readiness is complete only when all of the following are true:

- Phase 1 RED tests were written, run, and recorded;
- Phase 2 implementation turns the required tests GREEN;
- an independent review finds no blocking runner/recovery/evaluator defect;
- dynamic G3-G5 evidence is revalidated where affected;
- a replacement dynamic G5 freeze is generated with new source/evaluator,
  manifest, artifact, and dependency hashes;
- scheduler order, storage bytes, and GPU hours are frozen;
- complete preflight passes on the exact pushed commit;
- `docs/PROJECT_STATE.md` records content and persistence commits plus parity;
- no formal job or sealed scenario was accessed prematurely.

Until these conditions pass, the project remains at `M2`, G6 formal execution
is blocked, and only readiness implementation/testing or explicitly authorized
dynamic pilot work may proceed.
