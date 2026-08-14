# Formal Experiment Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Problem 2 repository auditable and runnable up to the highest gate supported by the available evidence, while failing closed when real engineering or GIS evidence is missing.

**Architecture:** Add a strict readiness layer above the existing configuration, road, scenario, resource, and experiment modules. Parameter and road registries remain source-of-truth inputs; deterministic audit reports expose missing provenance, unit conversions, scale consistency, and resource activation. The matrix runner and sealed-test freezer consult the same readiness report, so a smoke/pilot run cannot be mistaken for formal evidence.

**Tech Stack:** Python 3.11, PyYAML, NumPy, pytest, XML GraphML parsing from the standard library, SHA-256 manifests, existing SR-MAPPO/experiment modules.

**Spec:** `docs/design/section-4.2-design-contract.md`, `docs/verification/section-4-5-runbook.md`, and the six `sr-mappo-problem2` reference contracts.

## Global Constraints

- The flagship algorithm remains `SR-MAPPO`; do not add HAPPO or `AG-SR-MAPPO`.
- Do not modify Word documents or overwrite user experiment outputs.
- Do not invent equipment, field-study, or road-survey evidence.
- OSM GraphML is read-only and is reported as a simulation constraint, not field deployment.
- Formal jobs are blocked until every required gate is verified; smoke/pilot outputs are provisional.
- Every changed behavior receives a failing test before implementation and a fresh full regression before completion.

### Task 1: Parameter evidence registry and audit

**Files:**
- Modify: `configs/parameter_registry.yaml`
- Create: `src/problem2/experiments/readiness.py`
- Create: `scripts/audit_parameters.py`
- Create: `tests/experiments/test_parameter_audit.py`

- [ ] Write failing tests for required provenance fields, unit/range checks, deterministic conversion checks, and explicit provisional status.
- [ ] Implement parameter-record validation and a machine-readable audit report; preserve current demo values as assumptions.
- [ ] Add all contract-required parameters, including `uav_speed`, `usable_fraction`, `decision_dt`, and explicit source/conversion fields.
- [ ] Run focused tests, then commit `feat: audit engineering parameter evidence`.

### Task 2: Offline GraphML road ingestion and metadata audit

**Files:**
- Modify: `src/problem2/road/graph.py`
- Create: `src/problem2/road/graphml.py`
- Create: `scripts/audit_road_source.py`
- Create: `tests/unit/test_graphml_audit.py`
- Modify: `configs/environment.yaml`

- [ ] Write failing tests for GraphML node/edge parsing, directed-to-undirected policy, metric projection, connected components, source hash, and missing-file failure.
- [ ] Implement deterministic GraphML loading with declared lon/lat or metric coordinate mode and metadata output; never download during training.
- [ ] Add an explicit optional external source path and crop/bbox metadata without changing the synthetic default when no source is configured.
- [ ] Run focused tests and a read-only audit against the existing Jodhpur GraphML; commit `feat: add auditable offline road ingestion`.

### Task 3: Scenario split and physical-scale audit

**Files:**
- Modify: `src/problem2/config.py`
- Modify: `configs/scenarios.yaml`
- Modify: `configs/scales.yaml`
- Create: `scripts/audit_scenarios.py`
- Create: `tests/experiments/test_scenario_audit.py`

- [ ] Write failing tests for split disjointness, per-scale coverage, seed uniqueness, extent-preserving cell sizes, and sealed-test isolation.
- [ ] Implement scenario and scale audit functions and report unresolved source/dynamics metadata instead of silently verifying them.
- [ ] Keep existing scenario IDs compatible with the experiment matrix.
- [ ] Run focused tests and commit `feat: audit scenario independence and physical scale`.

### Task 4: Unified readiness gate and resource pilot tooling

**Files:**
- Modify: `src/problem2/experiments/readiness.py`
- Modify: `scripts/run_matrix.py`
- Modify: `scripts/freeze_sealed_test.py`
- Create: `scripts/run_resource_pilot.py`
- Create: `tests/experiments/test_readiness_gate.py`

- [ ] Write failing tests showing formal execution is rejected when any audit is unresolved and accepted only for a fully verified fixture.
- [ ] Implement the unified report with explicit gate names, maturity level, blockers, and evidence paths.
- [ ] Add a deterministic resource-counterfactual pilot for unlimited, no-support, fixed, teleport, and mobile conditions; emit raw rows and an activation report.
- [ ] Ensure readiness checks do not alter algorithm behavior or update evaluation normalization.
- [ ] Run focused tests and commit `feat: enforce formal readiness and resource activation gate`.

### Task 5: End-to-end verification and handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/verification/complete-project-runbook.md`
- Create: `docs/verification/formal-readiness-report.md`

- [ ] Run the focused test suites, full `pytest -q`, `compileall`, `git diff --check`, and smoke/resource audits.
- [ ] Run the 150-job dry-run and one CPU smoke job; preserve raw outputs under ignored `runs/` paths.
- [ ] Run the readiness CLI and record the highest gate actually passed plus the exact external evidence still required.
- [ ] Commit `docs: document formal experiment readiness gate` and push only repository files.

## Self-review checklist

- Every six contract areas has a corresponding audit or explicit blocker.
- No parameter is promoted from assumption to verified without source metadata.
- No OSM file is copied or changed; source hash is recorded instead.
- The same readiness predicate protects matrix execution and sealed-test unlock.
- Resource activation is measured before any causal wording is permitted.
- Formal results remain impossible to generate from provisional configuration.
