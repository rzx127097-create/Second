# Problem 2 Code Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a traceable, testable code framework for Chapter 4, covering the 4.1 air-ground resource mechanism through 4.5 formal experiment and evidence production.

**Architecture:** Use a layered Python package. Domain state and conservation rules are independent of road topology and reinforcement learning; deterministic environment transitions consume those domain interfaces; demand/rendezvous logic feeds role-specific observations and masks; SR-MAPPO consumes the environment through a stable rollout interface; baselines, experiment jobs and artifact generation consume the same environment and log schema. Formal values remain configuration-driven and provisional until an engineering-source freeze gate passes.

**Tech Stack:** Python 3.11+, dataclasses, NumPy, NetworkX, PyYAML, PyTorch, pytest, pandas, matplotlib, scipy.

**Spec:** `docs/design/section-4.1-design-contract.md`, `docs/design/section-4.2-design-contract.md`, `docs/thesis/chapter4-outline.md`, and `C:\Users\RZX\.codex\skills\sr-mappo-problem2\references\experiment-and-statistics-protocol.md`.

## Global Constraints

- Keep the flagship algorithm name `SR-MAPPO`; do not introduce HAPPO or rename it `AG-SR-MAPPO`.
- The vehicle replenishes pesticide only; battery charging and battery exchange are outside the primary mechanism.
- Use one vehicle in the primary experiment; keep collection-based notation extensible.
- Treat OSM as a road-constrained simulation input, not field deployment evidence.
- Do not hard-code formal engineering parameters, observation dimensions, vehicle slot counts or reward weights in prose; configuration and implementation tests are authoritative.
- Preserve the frozen decision order and pesticide conservation relation from Sections 4.1 and 4.2.
- Training, validation and sealed test scenarios must be separated; never tune on sealed test results.
- Every formal number must trace from configuration and Git commit through raw logs, validated summaries and generated artifacts.
- Existing thesis Word documents are read-only for this code task.

---

### Task 1: Repository and configuration foundation

**Files:**
- Create: `pyproject.toml`
- Create: `configs/parameter_registry.yaml`
- Create: `configs/scales.yaml`
- Create: `configs/environment.yaml`
- Create: `configs/algorithms/sr_mappo.yaml`
- Create: `configs/experiments/formal_matrix.yaml`
- Create: `src/problem2/__init__.py`
- Create: `src/problem2/config.py`
- Create: `tests/unit/test_config.py`

**Produces:** deterministic configuration loading, validation, canonical JSON and SHA-256 configuration identity. Demo values are explicitly provisional and cannot be used as formal results.

### Task 2: 4.1 domain and resource mechanism

**Files:**
- Create: `src/problem2/domain/types.py`
- Create: `src/problem2/domain/state.py`
- Create: `src/problem2/domain/events.py`
- Create: `src/problem2/domain/resources.py`
- Create: `src/problem2/domain/requests.py`
- Create: `src/problem2/domain/units.py`
- Create: `tests/unit/test_resources.py`
- Create: `tests/unit/test_requests.py`
- Create: `tests/unit/test_conservation.py`

**Produces:** finite UAV pesticide, vehicle inventory, request lifecycle, service allocation, actual transfer, no-negative-resource checks and the Section 4.1 global conservation audit.

### Task 3: Field dynamics and deterministic environment core

**Files:**
- Create: `src/problem2/field/pest_dynamics.py`
- Create: `src/problem2/field/pesticide_field.py`
- Create: `src/problem2/field/wind_field.py`
- Create: `src/problem2/environment/movement.py`
- Create: `src/problem2/environment/service_state_machine.py`
- Create: `src/problem2/environment/transition.py`
- Create: `src/problem2/environment/air_ground_env.py`
- Create: `tests/integration/test_environment_step.py`

**Produces:** a deterministic reset/step environment with the frozen event order, six UAV actions, provisional vehicle hold/action hooks, service setup and transfer phases, termination/truncation semantics and event-complete logs.

### Task 4: GIS road graph and rendezvous layer

**Files:**
- Create: `src/problem2/road/projection.py`
- Create: `src/problem2/road/graph.py`
- Create: `src/problem2/road/topology.py`
- Create: `src/problem2/road/shortest_path.py`
- Create: `src/problem2/demand/urgency.py`
- Create: `src/problem2/demand/eta.py`
- Create: `src/problem2/demand/rendezvous.py`
- Create: `src/problem2/demand/feasibility.py`
- Create: `src/problem2/demand/candidate_slots.py`
- Create: `tests/unit/test_road_graph.py`
- Create: `tests/unit/test_rendezvous.py`

**Produces:** metre-based road graph, connected-component and unreachable checks, shortest-path ETA, deterministic candidate ordering, service feasibility and fallback behavior.

### Task 5: Observations, masks and structured state

**Files:**
- Create: `src/problem2/environment/observations.py`
- Create: `src/problem2/environment/action_masks.py`
- Create: `src/problem2/environment/rewards.py`
- Create: `tests/unit/test_observations_masks.py`
- Create: `tests/unit/test_rewards.py`

**Produces:** role-local observations, structured critic state, fixed-slot mapping, legal-action masks, `fallback_hold`, common metrics and auditable team reward components.

### Task 6: SR-MAPPO implementation

**Files:**
- Create: `src/problem2/algorithms/common/normalization.py`
- Create: `src/problem2/algorithms/common/masked_distribution.py`
- Create: `src/problem2/algorithms/common/gae.py`
- Create: `src/problem2/algorithms/common/checkpoint.py`
- Create: `src/problem2/algorithms/sr_mappo/actors.py`
- Create: `src/problem2/algorithms/sr_mappo/critic.py`
- Create: `src/problem2/algorithms/sr_mappo/rollout.py`
- Create: `src/problem2/algorithms/sr_mappo/losses.py`
- Create: `src/problem2/algorithms/sr_mappo/trainer.py`
- Create: `src/problem2/algorithms/sr_mappo/algorithm.py`
- Create: `tests/marl/test_masks_and_gae.py`
- Create: `tests/marl/test_role_gradient_isolation.py`
- Create: `tests/marl/test_checkpoint_roundtrip.py`

**Produces:** role-separated UAV/vehicle actors, structured central critic, team GAE, masked sampling/replay, SR-MAPPO stability components, deterministic-evaluation normalization freeze and checkpoint round-trip.

### Task 7: Baselines and experiment orchestration

**Files:**
- Create: `src/problem2/baselines/unlimited_supply.py`
- Create: `src/problem2/baselines/teleport_service.py`
- Create: `src/problem2/baselines/fixed_support.py`
- Create: `src/problem2/baselines/priority_dispatch.py`
- Create: `src/problem2/baselines/rolling_astar.py`
- Create: `src/problem2/experiments/job_identity.py`
- Create: `src/problem2/experiments/runner.py`
- Create: `src/problem2/experiments/recovery.py`
- Create: `src/problem2/experiments/evaluation.py`
- Create: `scripts/train.py`
- Create: `scripts/evaluate.py`
- Create: `scripts/run_matrix.py`
- Create: `tests/baselines/test_baselines.py`
- Create: `tests/integration/test_job_recovery.py`

**Produces:** resource-matched baselines, rolling A*, immutable job IDs, atomic checkpoints, failed-job retry, shared scenarios and sealed-test evaluation entry points.

### Task 8: Evidence pipeline and final integration

**Files:**
- Create: `src/problem2/artifacts/validate_logs.py`
- Create: `src/problem2/artifacts/summarize.py`
- Create: `src/problem2/artifacts/figures.py`
- Create: `src/problem2/artifacts/tables.py`
- Create: `src/problem2/artifacts/evidence_manifest.py`
- Create: `scripts/audit_resource_activation.py`
- Create: `scripts/build_artifacts.py`
- Create: `tests/artifacts/test_traceability.py`
- Modify: `README.md`

**Produces:** validated long-format logs, paired summaries, bootstrap statistics, Nature-style figures, three-line tables, source-to-artifact manifest and complete run documentation.

## Delivery Gates

- Gate M1: repository foundation and configuration identity pass.
- Gate M2a: 4.1 deterministic resource/request/conservation tests pass.
- Gate M2b: road, service-state and environment integration tests pass.
- Gate M2c: heterogeneous SR-MAPPO implementation tests pass.
- Gate M3: pilot on independent validation scenes and multiple seeds.
- Gate M4: frozen formal matrix, sealed test and traceable evidence artifacts.

This first implementation increment targets Task 1 and Task 2 only. It must not claim formal experiment results or algorithmic superiority.
