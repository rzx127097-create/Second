# G5 Replacement Primary Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and freeze a 48-job dynamic G5 replacement pilot matrix while preserving the formal G6 protocol and reducing repeated reacceptance work.

**Architecture:** Keep `build_pilot_matrix` and `run_pilot_matrix` as the only matrix and coverage authorities. Replace the broad exploratory condition list with the eight executable condition-to-method pairs required for primary comparisons and runtime coverage, expose the twelve excluded diagnostic conditions for auditability, and reuse unchanged G3/G4 evidence after a source-scope check instead of rerunning unrelated suites.

**Tech Stack:** Python 3.11, pathlib, dataclasses, pytest, existing Problem 2 training and audit modules.

**Spec:** `docs/superpowers/specs/2026-08-30-g5-replacement-primary-matrix-design.md`

## Global Constraints

- Use `dynamic_pest_v1` for every primary and revalidation execution.
- Keep pesticide as the only replenished resource and battery replenishment false.
- Do not access validation scenarios `20000-20049` or sealed scenarios `30000-30099`.
- Preserve the public algorithm name `SR-MAPPO`; do not introduce HAPPO or `AG-SR-MAPPO`.
- Keep formal G6 scales, formal training seeds, statistics, and sealed-test lock unchanged.
- Keep one-job-at-a-time development execution; no batch or parallel pilot runner.
- Preserve all historical and existing Phase 3 artifacts without relabeling.

### Task 1: Replace the executable development matrix scope

**Files:**
- Modify: `src/problem2/training/pilot.py`
- Test: `tests/g5/test_pilot_freeze.py`

**Interfaces:**
- `PILOT_CONDITIONS` exposes exactly the eight executable conditions.
- `PILOT_EXCLUDED_CONDITIONS` exposes the twelve diagnostic-only conditions.
- `build_pilot_matrix(contract)` returns exactly 48 unique development `PilotJob` values.
- `run_pilot_matrix` rejects excluded conditions and incomplete replacement coverage.

- [ ] **Step 1: Update tests to assert the 48-job replacement scope and excluded diagnostics.**
- [ ] **Step 2: Run the focused tests and observe the expected failures against the current 120-job contract.**
- [ ] **Step 3: Implement the minimum constants/mapping change in `pilot.py`.**
- [ ] **Step 4: Run the focused pilot-freeze suite and affected G5 tests.**
- [ ] **Step 5: Commit the contract implementation and tests.**

### Task 2: Record and audit the replacement freeze boundary

**Files:**
- Create: `docs/audits/g5-replacement-primary-matrix.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `HANDOFF_G6_READINESS_PHASE3.md`

**Interfaces:**
- The audit record names the exact eight-condition scope, 48-job count, excluded diagnostics, and formal G6 invariants.
- `PROJECT_STATE.md` and the handoff identify the replacement matrix as the only next authorized development scope.

- [ ] **Step 1: Record the implementation commit, test result, and scope hash after Task 1.**
- [ ] **Step 2: Run documentation diff checks and verify no protected or historical output changed.**
- [ ] **Step 3: Commit and push the replacement scope/state record.**

### Task 3: Generate and verify the replacement G5 freeze

**Files:**
- Create: dynamic replacement G5 freeze artifacts below `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/`
- Test: existing G5 freeze/audit commands and tests

**Interfaces:**
- A freeze is emitted only after all 48 development identities complete and pass artifact validation.
- The freeze records `matrix_complete=true`, dynamic ecology, pesticide-only replenishment, and false validation/sealed access.

- [ ] **Step 1: Run the replacement primary matrix one job at a time, preserving failed attempts.**
- [ ] **Step 2: Validate the complete 48-job evidence set and candidate/budget manifests.**
- [ ] **Step 3: Run the read-only Phase 4 preflight against the exact pushed freeze.**
