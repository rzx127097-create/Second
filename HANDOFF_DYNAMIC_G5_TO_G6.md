# Dynamic G5 Freeze to G6 Handoff

Date: 2026-08-30

This is the no-context startup document for the next conversation. The next
agent must read `AGENTS.md`, `docs/PROJECT_STATE.md`, and this file before
touching code or experiment outputs. `AGENTS.md` is the repository policy and
`docs/PROJECT_STATE.md` is the authoritative gate, maturity, and evidence
record. If any text here conflicts with either file, those files win.

## 1. Task In Progress

The project is the thesis second problem: road-constrained air-ground
heterogeneous cooperative pesticide spraying with a mobile pesticide
replenishment vehicle, using **SR-MAPPO** as the public flagship method.

The user asked to simplify the remaining verification burden because of time
pressure. The active work was Stage 0, item 4: dynamic G3-G5 reacceptance,
specifically reconstruction and rerun preparation for the dynamic G5
development pilot matrix. The safe simplification was to reuse the accepted
dynamic source scope, run only the replacement matrix required by the G5
contract, and consolidate the gate into a read-only freeze check plus a Phase 4
preflight. No evidence gate was bypassed.

## 2. Repository And Boundary

Repository: `C:/Users/RZX/Documents/ChatGPT/Second`

Branch: `codex/problem2-dynamic-pest-model`

Remote: `https://github.com/rzx127097-create/Second.git`

The verified code/evidence base immediately before this handoff document was
committed was:

```text
df75d67ef9f5679b090e3db5eb763037ec7fa7d6
```

The handoff document was then committed and pushed as `7f952a2`.

Current maturity is `M2`. This is implementation and scoped mechanism
evidence, not formal efficacy evidence. The only replenished resource is
pesticide. Battery replenishment is disabled. OSM/GraphML is read-only
simulation input for road-constrained modeling, not field-deployment evidence.

All new Problem-2 outputs belong below:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/
```

The historical static output root
`outputs/problem2_sr_mappo_v1/g5/` is read-only diagnostic material. Do not
overwrite, relabel, or merge it into dynamic evidence.

## 3. Completed Work

### Dynamic replacement matrix and freeze

The replacement matrix is complete:

```text
8 executable conditions x 2 representative scales x 3 development seeds
= 48 jobs
= 960 development episode-reference rows
```

It covers the five required learning methods and the required primary paths:

| condition | learning method | vehicle path |
|---|---|---|
| `sr_mappo_mobile` | `sr_mappo_mobile` | learned, joint |
| `sr_mappo_fixed` | `sr_mappo_mobile` | fixed support, UAV-only |
| `sr_mappo_astar` | `sr_mappo_mobile` | rolling A*, UAV-only |
| `mappo_mobile` | `mappo_mobile` | learned, joint |
| `sr_mappo_two_stage` | `sr_mappo_mobile` | learned two-stage |
| `ippo_mobile` | `ippo_mobile` | IPPO mobile |
| `maddpg_mobile` | `maddpg_mobile` | MADDPG mobile |
| `iql_mobile` | `iql_mobile` | IQL mobile |

Representative scales are `g20x20_d2` and `g30x50_d4`; training seeds are
`51001`, `51002`, and `51003`; development scenarios are `10000-10019`.

Authoritative freeze:

```text
outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/freeze-manifest.json
schema=g5-dynamic-replacement-freeze-v1
matrix_complete=true
validation_accessed=false
sealed_accessed=false
battery_replenishment_enabled=false
actual_unlock_count=0
freeze_sha256=066a786e536045aa75c3e4ccc3f707a93428d3b38bf81efd21f32a91c19cdc0b
```

Frozen input hashes:

```text
candidate_manifest_sha256=c5aee01a2ad180301aa8f2d2d39b067500f6297ac3ac1b503f68814334ba8918
budget_manifest_sha256=6c97e5e882dfbbba3cba133185f1a589268d9191beb51f2874a0202cbcc0920d
g6_training_manifest_sha256=79712f8746d92476f4350d26cf3a7fd85bd6a2c3c64a7f734e5ef2ddd3a18e3e
g6_validation_manifest_sha256=e5dfe8cf6df35efdcbc415ada2ed8eb8667048ebf9c66c9fa9cea680fedad5e0
source_commit=e0a43d219b58c2e0ce2c6ac33c1ec891d5846c0f
source_scope_sha256=f3f307e8f20bce13f5d0340691c0de5cc8cb7bfeb03ac051aecbc344ff348d92
```

### Code and evidence integrity repair

The following repairs are already committed and pushed:

- `6b0aa05`: bind physical training to dynamic candidate/budget hashes;
- `c96636e`: bind every dynamic G6 job dependency graph to those hashes;
- `e0a43d2`: preserve historical-manifest compatibility for diagnostic tests;
- `592ad5a`: regenerate the dynamic G6 manifests and freeze after the source
  scope changed;
- `df75d67`: record the final integrity repair and verification in project
  state.

The relevant code is in:

- `src/problem2/training/physical_training.py`;
- `src/problem2/training/tuning.py`;
- `scripts/freeze_g5.py`;
- `tests/g5/test_dynamic_replacement_freeze.py`.

## 4. Fresh Verification

The final focused regression was:

```text
python -m pytest tests/g5/test_dynamic_replacement_freeze.py tests/g5/test_pilot_freeze.py tests/g5/test_task12_remediation2.py tests/g6 -q --tb=short
115 passed in 133.00s
```

Also verified:

```text
python scripts/freeze_g5.py --dynamic-replacement --check-only --root .   exit 0
read_only_preflight(ROOT, gate="G6")                              all_pass=true
python -m compileall -q src scripts                                  exit 0
git diff --check                                                     pass
```

The preflight reported `dynamic_g5_freeze=true`,
`dynamic_replacement_matrix=true`, `no_sealed_identities=true`,
`queue_created=false`, and local/upstream/remote parity at `df75d67`.

## 5. Exact Next Plan

The next authorized gate is **G6, first immutable formal training job**. Do
not interpret the completed G5 freeze or read-only preflight as a completed G6
execution.

### Step A: bootstrap read-only checks

Run these before any new write:

```text
python scripts/freeze_g5.py --dynamic-replacement --check-only --root .
python scripts/preflight_g6.py --help
```

The second command is only an interface inspection. The current
`scripts/preflight_g6.py` entry point is still a blocked CLI wrapper, so use
the callable `read_only_preflight` from `scripts/_g5_cli.py` for the actual
read-only readiness check.

### Step B: audit or implement the formal G6 entry path

The current files are deliberate blocking stubs:

- `scripts/run_g6_jobs.py` blocks formal execution;
- `scripts/resume_g6_jobs.py` blocks recovery;
- `scripts/preflight_g6.py` blocks as a standalone CLI;
- `src/problem2/training/runner.py::run_training_job` is the bounded smoke
  runner, not proof that the full physical G6 executor exists.

Before formal execution, read
`docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md` and implement or
audit the actual physical G6 runner, atomic checkpointing, recovery, checkpoint
validation, and fixed-scenario evaluator. Any change to runner, recovery,
evaluator, or preflight code changes the frozen source/evaluator boundary:
add tests, update the G5/G6 source and evaluator hashes, regenerate the
affected dynamic manifests/freeze, update `docs/PROJECT_STATE.md`, commit,
push, and re-run the focused regression before starting a job.

### Step C: run exactly one frozen job

Read the first job from
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/g6-training-jobs.json`
and pass the manifest fields through unchanged. Do not hand-write a new
identity. The current first scheduler entry is the `sr_mappo_mobile` base
identity at `g20x20_d2`, candidate `c02`, training seed `42`; re-read the file
at execution time in case a later authorized freeze changes it.

The job must write only under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6/`, use the frozen protocol,
and keep validation and sealed access false during training. Checkpoint
interval and count are frozen at `10000` and `20`.

### Step D: recovery and fixed validation

Immediately after that one job:

1. verify the terminal checkpoint and manifest hashes;
2. interrupt/resume or replay the same job through the recovery path and prove
   state/metric equivalence;
3. evaluate the job against the fixed validation panel `20000-20049` only
   after training, without tuning candidate choices;
4. validate the long-format rows and artifact manifest;
5. record the result and the pushed commit in `docs/PROJECT_STATE.md`.

Do not start a second formal job until the first job's recovery and validation
checks pass and the evidence chain is persisted.

## 6. Pitfalls That Must Not Recur

1. Do not use the old static hashes `67e6784b...` and `04813895...` for the
   dynamic default path. They are valid only for explicit historical
   diagnostic manifests. The dynamic defaults are `c5aee01a...` and
   `6c97e5e8...`.
2. Do not update source files and then run freeze check-only while tracked
   files are dirty. Commit and push the source change first, regenerate the
   dynamic manifests/freeze, then check again. Untracked temporary material
   is intentionally preserved and is not a reason to clean the worktree.
3. Do not call `scripts/run_g6_jobs.py` or `scripts/resume_g6_jobs.py` and
   assume they execute work. They currently return the blocked CLI response.
4. Do not treat a smoke result, training reward, pilot result, or read-only
   preflight as formal treatment efficacy or superiority evidence.
5. Do not access validation scenarios before the first immutable G6 training
   identity is frozen and completed. Never access sealed-test content
   `30000-30099`; G7 unlock count must remain `0`.
6. Do not enable battery replenishment, introduce HAPPO, rename the public
   method, or write Problem-2 output into the first-problem roots.
7. Do not stage, delete, rename, or merge the preserved untracked artifact
   `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-008-ippo/`
   or the existing `tmp-*`, `_tmp_docx_assets`, `g5/_debug`, and
   `g5/quarantine` directories.
8. Do not force-push. Every important phase needs a descriptive commit,
   remote push, and a matching record in `docs/PROJECT_STATE.md`.

## 7. Claim Boundary

Until a later maturity gate is explicitly persisted, use wording such as
"proposes", "defines", "establishes", and "plans to test". Do not write
"proves", "significantly outperforms", "formal experiments show", "real
deployment verified", or "universally optimal". The evidence chain must stay
complete:

```text
source parameter/literature
-> frozen configuration and Git commit
-> run ID and raw episode log
-> validated long-format table
-> paired statistical summary
-> figure/table artifact manifest
-> thesis statement
```

The immediate goal is operational readiness for one auditable G6 job, not a
scientific conclusion.
