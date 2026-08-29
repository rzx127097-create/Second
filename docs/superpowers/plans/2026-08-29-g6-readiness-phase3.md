# G6 Readiness Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revalidate the dynamic G3-G5 execution path after Phase 2 and establish the first controlled pilot evidence needed before a replacement dynamic G5 freeze.

**Architecture:** Keep the existing dynamic ecology and physical environment as the single execution path. Bind one explicit vehicle controller to each executable condition at environment construction, while preserving the learned UAV actor and training metadata. Use existing bounded audits and pilot infrastructure; write only below `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/`.

**Tech Stack:** Python 3.11, pathlib, dataclasses, NumPy, pytest, existing Problem 2 training/heuristic modules.

**Spec:** `HANDOFF_G6_READINESS_PHASE1.md`, `docs/superpowers/plans/2026-08-29-problem2-dynamic-pest-model.md`, and `docs/PROJECT_STATE.md`.

## Global Constraints

- Keep the public algorithm name `SR-MAPPO`; do not introduce HAPPO or `AG-SR-MAPPO`.
- Use `dynamic_pest_v1` for all primary and revalidation execution.
- Pesticide is the only replenished resource; battery replenishment remains disabled.
- Do not access validation scenario payloads (`20000-20049`) or sealed scenario payloads (`30000-30099`) during Phase 3 pilots.
- Do not modify historical `outputs/problem2_sr_mappo_v1/g5/` evidence or protected external assets.
- Write new evidence only below `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/`.
- Run development pilot jobs one at a time and show each completed result before starting another.
- Phase 3 remains `M2`; it does not authorize formal G6 execution, G7 unlock, or efficacy/superiority claims.

### Task 1: Wire executable vehicle controllers into the physical path

**Files:**
- Modify: `src/problem2/training/cooperative_env.py`
- Modify: `src/problem2/training/tuning.py`
- Modify: `src/problem2/training/physical_training.py`
- Test: `tests/g5/test_physical_candidate_training.py` or a focused new test under `tests/g6/`

**Interfaces:**
- `Problem2CooperativeEnv(..., vehicle_controller=...)` accepts a controller implementing `decide(DispatchObservation) -> ControllerDecision`.
- `build_development_environment(..., vehicle_controller=...)` forwards the controller to the physical wrapper.
- Each physical transition uses the controller decision for dispatch slot and service node; learned mode retains the sampled vehicle action.

- [ ] **Step 1: Write the failing test** asserting a non-learned condition uses its controller decision and emits the controller-selected service node, while `sr_mappo_mobile` preserves learned vehicle sampling.
- [ ] **Step 2: Run the focused test and confirm the failure is caused by the current internal A* dispatch path.**
- [ ] **Step 3: Implement the minimum controller injection and condition-to-controller factory.** Do not duplicate heuristic logic or alter resource semantics.
- [ ] **Step 4: Run the focused controller tests and affected physical-training tests.**
- [ ] **Step 5: Commit the controller wiring with a descriptive message.**

### Task 2: Revalidate dynamic G3-G5 contracts

**Files:**
- Modify only if required by a failing test: `scripts/audit_dynamic_pest.py`, `scripts/run_g5_smoke.py`, or affected source modules.
- Create/update: `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/` and `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/smoke/`.

- [ ] **Step 1: Run the dynamic ecology/G3/G4/G5 contract suites affected by the controller and Phase 2 changes.**
- [ ] **Step 2: Run `audit_dynamic_pest.py` and the bounded dynamic G5 smoke with `sr_mappo_mobile`, recording only development evidence.**
- [ ] **Step 3: Verify the audit/smoke outputs declare dynamic ecology, pesticide-only replenishment, no validation/sealed access, and `M2` evidence status.**
- [ ] **Step 4: Commit the revalidation evidence and any narrowly required fixes.**

### Task 3: Run the first controlled dynamic pilot

**Files:**
- Create: a single bounded pilot artifact under `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/`.

- [ ] **Step 1: Resolve the first development pilot identity from the frozen pilot matrix without opening validation or sealed payloads.**
- [ ] **Step 2: Run exactly one pilot job with the dynamic default and bounded interactions.**
- [ ] **Step 3: Validate its raw log and audit, then report the completed result to the user. Stop before starting another pilot.**

### Task 4: Persist Phase 3 state

**Files:**
- Create: `docs/audits/g6-readiness-phase3.md`
- Modify: `docs/PROJECT_STATE.md`

- [ ] **Step 1: Record test/audit/pilot evidence, unresolved limitations, zero sealed unlocks, unchanged historical outputs, and `M2` maturity.**
- [ ] **Step 2: Commit and push the Phase 3 record, then verify local/upstream/remote parity.**
- [ ] **Step 3: Keep the next authorized action explicit: continue controlled dynamic pilots one at a time; no replacement freeze or formal G6 until the required Phase 3 evidence is complete.**

## Self-review

- The plan does not read validation or sealed payloads and does not authorize G6/G7 execution.
- The physical controller wiring is test-first and uses existing heuristic interfaces.
- Dynamic output confinement and historical G5 preservation are explicit.
- Pilot sequencing and the required user checkpoint are explicit.
