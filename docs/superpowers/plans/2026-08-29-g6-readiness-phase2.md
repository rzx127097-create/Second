# G6 Readiness Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Phase 1 G6 readiness contracts GREEN with executable condition semantics, complete immutable freeze metadata, fail-closed preflight, recoverable ledger/checkpoint evidence, and import-safe G6 entry points.

**Architecture:** Reuse the existing G5 contract, artifact, identity, and sealed-lock boundaries. Add small shared modules for condition resolution and validation checkpoint selection; extend the existing freeze builder, ledger, recovery, and read-only CLI guard. Keep the three G6 scripts as thin wrappers with no import-time work.

**Tech Stack:** Python 3.11, pathlib, dataclasses, JSON/YAML manifests, pytest, existing `problem2` modules.

**Spec:** `docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md` and `HANDOFF_G6_READINESS_PHASE1.md`.

## Global Constraints

- Keep the flagship name `SR-MAPPO`; never add HAPPO or `AG-SR-MAPPO`.
- Keep pesticide as the only replenished resource and battery replenishment inactive.
- Do not read validation scenario content or any sealed scenario ID/content; do not run G6/G7 jobs.
- Keep historical `outputs/problem2_sr_mappo_v1/g5/` evidence byte-preserved; new replacement manifests belong under `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/`.
- Preserve all pre-existing untracked directories and protected external assets.
- Use the exact validation panel `20000-20049`, deterministic evaluation, and the frozen checkpoint tie-break order.
- Persist content and state commits to the current `codex/` branch and push before declaring Phase 2 complete.

### Task 1: Executable Condition Semantics

**Files:**
- Create: `src/problem2/training/conditions.py`
- Modify: `scripts/run_g5_validation_tuning.py:415-450`
- Test: `tests/g6/test_condition_semantics.py`

**Interfaces:**
- Produce `ConditionExecution` and `resolve_condition_execution(condition_id: str) -> ConditionExecution`.
- `ConditionExecution` exposes `condition_id`, `vehicle_controller`, `vehicle_trainable`, and `training_mode`.

- [ ] **Step 1: Confirm RED**

Run `python -m pytest tests/g6/test_condition_semantics.py -q --tb=short`; expect the missing module and mobile-relabelling failures.

- [ ] **Step 2: Implement the six explicit mappings**

Use a frozen mapping for `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `sr_mappo_nearest`, `sr_mappo_urgency`, and `sr_mappo_two_stage`; reject unknown IDs with `ValueError`.

- [ ] **Step 3: Forward the outer condition**

Set the physical refit job's `condition_id` from `job["condition_id"]`, retain the selected learning method/candidate separately, and return the same condition without relabelling the physical execution as mobile.

- [ ] **Step 4: Verify and commit**

Run the focused test file and `python -m compileall -q src scripts`; commit the focused implementation.

### Task 2: Frozen Validation Checkpoint Selection

**Files:**
- Create: `src/problem2/evaluation/selection.py`
- Modify: `src/problem2/evaluation/__init__.py` only if export is needed
- Test: `tests/g6/test_validation_readiness.py`

**Interfaces:**
- Produce `select_frozen_checkpoint(rows: Iterable[Mapping[str, Any]], expected_scenarios: Iterable[int]) -> dict[str, Any]`.

- [ ] **Step 1: Confirm RED**

Run the two checkpoint-selection tests and observe the missing module failures.

- [ ] **Step 2: Validate complete candidate coverage**

Require exactly the expected scenario set once per checkpoint, reject duplicates/missing/out-of-range/sealed rows, require finite reduction and boolean success, and keep every input row in `candidate_rows`.

- [ ] **Step 3: Apply the frozen ordering**

Rank by descending mean reduction, descending success probability, ascending interaction count, then ascending checkpoint hash; emit the exact four-item `selection_order` list and the winning checkpoint fields.

- [ ] **Step 4: Verify and commit**

Run `python -m pytest tests/g6/test_validation_readiness.py -q --tb=short` and commit the selector.

### Task 3: Ledger and Checkpoint Recovery Evidence

**Files:**
- Modify: `src/problem2/experiments/ledger.py`
- Modify: `src/problem2/experiments/recovery.py`
- Test: `tests/g6/test_runtime_readiness.py`

**Interfaces:**
- Preserve `AppendOnlyLedger` public methods while adding UTC timestamp, host, process, attempt, and artifact hash metadata to every event.
- Extend `recover_checkpoint(path, *, expected_identity=None, expected_sha256=None)`.

- [ ] **Step 1: Confirm RED**

Run the metadata and expected-hash tests and record their current failures.

- [ ] **Step 2: Add event metadata centrally**

Create event metadata at append time using UTC ISO-8601, `platform.node()`, `os.getpid()`, and the existing attempt number; include `artifact_hashes` as a JSON object (empty when no artifact is supplied).

- [ ] **Step 3: Validate checkpoint hashes without losing the previous copy**

Check each candidate's SHA-256 when `expected_sha256` is provided. If the current checkpoint hash is wrong, continue to the retained `.previous` copy; if neither matches, raise a hash error. Preserve the existing atomic rotation behavior and propagate replacement failures.

- [ ] **Step 4: Verify and commit**

Run the complete runtime readiness file plus affected G5 ledger/checkpoint tests; commit the changes.

### Task 4: Dynamic Replacement Freeze Payloads and Manifests

**Files:**
- Modify: `src/problem2/training/selection.py`
- Modify: `scripts/freeze_g5.py`
- Create: `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/g6-training-jobs.json`
- Create: `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/g6-validation-evaluations.json`
- Test: `tests/g6/test_preflight_readiness.py`, `tests/g6/test_validation_readiness.py`

**Interfaces:**
- `build_formal_freeze_payloads` emits common `source_scope_sha256`, deterministic `scheduler_order`, positive `expected_storage_bytes`/`expected_gpu_hours`, dynamic ecology/output-root bindings, and complete validation metadata.

- [ ] **Step 1: Confirm RED**

Run the freeze and manifest assertions before changing production code.

- [ ] **Step 2: Extend the builder**

Derive scheduler order deterministically from canonical identities, calculate positive storage/GPU estimates from the 375-job workload, bind `dynamic_pest_v1` and `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g6`, and set validation deterministic policy plus a non-stub evaluator hash.

- [ ] **Step 3: Add replacement manifest generation**

Make `freeze_g5.py` write/verify the two replacement manifests below the dynamic G5 manifest root, keeping sealed payloads locked and free of sealed content. Do not alter historical G5 files.

- [ ] **Step 4: Verify and commit**

Run the focused preflight/validation tests and verify all new JSON parses; commit the payload and manifest implementation.

### Task 5: Complete Read-Only G6 Preflight

**Files:**
- Modify: `scripts/_g5_cli.py`
- Test: `tests/g6/test_preflight_readiness.py`

**Interfaces:**
- Extend `read_only_preflight(root, gate="G6")` with the complete check names and `resource_budget` fields while preserving `queue_created=False` and `sealed_accessed=False`.

- [ ] **Step 1: Confirm RED**

Run the preflight readiness tests and record missing checks and resource budget failures.

- [ ] **Step 2: Implement shared checks**

Read the dynamic replacement manifests and verify frozen source commit/scope, runner/recovery/checkpoint-validator/evaluator availability, scheduler order, storage/GPU estimates, dynamic ecology/root, restricted families, validation panel, hardware inventory, sealed lock, and source parity. Compute available disk bytes and required bytes including atomic headroom; never create queue/artifacts.

- [ ] **Step 3: Verify fail-closed behavior**

Keep dirty-tree and local/upstream/remote mismatch checks false under the existing monkeypatches and ensure a failed preflight starts no process.

- [ ] **Step 4: Verify and commit**

Run `python -m pytest tests/g6/test_preflight_readiness.py -q --tb=short` and commit.

### Task 6: Import-Safe G6 Entry Points

**Files:**
- Modify: `scripts/run_g6_jobs.py`
- Modify: `scripts/resume_g6_jobs.py`
- Modify: `scripts/preflight_g6.py`
- Test: `tests/g6/test_preflight_readiness.py`

**Interfaces:**
- Each module exposes callable `main()`, does no work on import, and uses an `if __name__ == "__main__"` guard.

- [ ] **Step 1: Confirm RED**

Run the import-safety parametrized tests and observe `SystemExit`/missing `main` failures.

- [ ] **Step 2: Implement thin wrappers**

Delegate argument parsing to shared CLI helpers; `run` and `resume` remain authorization-blocked in Phase 2, while `preflight` returns the read-only report. Importing any wrapper must not print, mutate locks, or raise.

- [ ] **Step 3: Verify and commit**

Run the import-safety tests and `python -m compileall -q scripts`; commit.

### Task 7: Phase 2 Verification and Persistence

**Files:**
- Modify: `docs/PROJECT_STATE.md`
- Create: `docs/audits/g6-readiness-phase2.md`

- [ ] **Step 1: Run scoped verification**

Run `python -m pytest tests/g6 -q --tb=short`, affected G3-G5 regression paths, `python -m compileall -q src scripts`, and `git diff --check`.

- [ ] **Step 2: Review boundaries**

Confirm no training/validation/sealed job ran, actual unlock count remains zero, historical G5 outputs and protected external assets are unchanged, and Phase 2 remains maturity M2.

- [ ] **Step 3: Record and push**

Write the audit and update `docs/PROJECT_STATE.md` with verification, content commit, pushed state commit, and next authorized action (Phase 3 dynamic G3-G5 revalidation/replacement freeze). Commit explicitly, push the branch, and verify local/upstream/remote parity.
