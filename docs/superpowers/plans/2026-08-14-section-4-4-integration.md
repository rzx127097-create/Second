# Section 4.4 SR-MAPPO Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing Section 4.3 request/rendezvous layer and Section 4.2 road/service environment to the existing SR-MAPPO rollout and PPO update path.

**Architecture:** Keep the existing role actors, team critic, PPO trainer and road executor. The adapter becomes the sole integration boundary: it converts open requests into deterministic fixed-width rendezvous slots, preserves the sampled slot mapping, and exposes reservation/service state to `ScenarioBundle`, which builds fixed-dimension role observations and the semantic global-state vector consumed by SR-MAPPO.

**Tech Stack:** Python 3, NumPy, PyTorch, pytest, YAML configuration.

**Spec:** `docs/design/section-4.2-design-contract.md` and `docs/plans/2026-08-14-section-4-4-sr-mappo.md`

## Global Constraints

- The public algorithm name remains `SR-MAPPO`; do not add HAPPO or `AG-SR-MAPPO`.
- The vehicle replenishes pesticide only.
- Do not modify thesis Word documents or produce experimental claims.
- Preserve deterministic action masks, candidate mappings, event order and pesticide conservation.
- Existing provisional parameters remain unsuitable for formal evidence.

---

### Task 1: Expose Requests and Service State at the Scenario Boundary

**Files:**
- Modify: `src/problem2/domain/requests.py`
- Modify: `src/problem2/scenarios/factory.py`
- Test: `tests/e2e/test_scenario_factory.py`

**Interfaces:**
- Consumes: `RequestManager` lifecycle records and `HeterogeneousDecisionAdapter.state`.
- Produces: fixed-width request slots in role observations and `critic_state["requests"]`, with service state passed to the critic builder.

- [ ] Write a failing test that creates a low-pesticide request and asserts that the same request ID, remaining quantity and service phase are visible in the next scenario snapshot.
- [ ] Run `pytest tests/e2e/test_scenario_factory.py -q` and verify that the assertion fails because `max_request_slots` is currently zero.
- [ ] Add a deterministic public request snapshot API and build a fresh fixed-width `SlotMapping` at every decision boundary.
- [ ] Pass active requests, service state and lock state into `build_observations` and `build_structured_critic_state`.
- [ ] Re-run `pytest tests/e2e/test_scenario_factory.py -q` and commit the passing increment.

### Task 2: Connect Section 4.3 Rendezvous Candidates to Vehicle Actions

**Files:**
- Modify: `src/problem2/section4_2/adapter.py`
- Test: `tests/integration/test_section_4_2_integration.py`

**Interfaces:**
- Consumes: `remaining_work_time_s`, `generate_rendezvous_candidates`, `build_candidate_action_slots`, the weighted `RoadGraph`, current resources and open requests.
- Produces: fixed `hold + slot-*` masks, internal shortest paths and an immutable public `slot -> request:rendezvous` mapping.

- [ ] Write a failing test with one feasible request and two road nodes, asserting deterministic urgency/ETA candidate selection and mapping.
- [ ] Run the test and verify failure because `_refresh_request_candidates` currently routes directly to the UAV cell and never calls Section 4.3 candidate generation.
- [ ] Generate metric rendezvous points around each requesting UAV, filter/order them through the existing Section 4.3 functions and retain routes separately from public mapping keys.
- [ ] Ensure padded slots stay masked and the current route is never overwritten while the vehicle is in transit.
- [ ] Re-run the integration test and commit the passing increment.

### Task 3: Enforce Joint Arrival Before Service Lock

**Files:**
- Modify: `src/problem2/environment/service_state_machine.py`
- Modify: `src/problem2/section4_2/adapter.py`
- Modify: `src/problem2/environment/observations.py`
- Test: `tests/integration/test_section_4_2_integration.py`
- Test: `tests/integration/test_environment_step.py`

**Interfaces:**
- Consumes: the selected request/rendezvous pair, vehicle road position and UAV metric position.
- Produces: explicit reserved/travelling state, joint-arrival event, service preparation lock and release events.

- [ ] Write failing tests proving that reservation does not immediately lock a distant UAV and that service cannot start when only the vehicle has arrived.
- [ ] Run the tests and verify the current immediate-lock/vehicle-only-arrival failures.
- [ ] Add a deferred reservation phase for the road adapter while preserving immediate preparation in the legacy environment.
- [ ] Apply UAV approach masks during limited commitment and enter the hard service lock only after both agents satisfy the rendezvous condition.
- [ ] Re-run both integration files and commit the passing increment.

### Task 4: Verify the Full SR-MAPPO Training Connection

**Files:**
- Modify: `tests/e2e/test_training_smoke.py`
- Modify only if the failing test requires it: `src/problem2/experiments/rollout_runner.py`
- Modify only if the failing test requires it: `src/problem2/algorithms/sr_mappo/algorithm.py`

**Interfaces:**
- Consumes: scenario role observations, semantic global state, exact masks and candidate mappings.
- Produces: a real `RolloutBatch`, one team GAE sequence, independent role updates and a resumable checkpoint.

- [ ] Write a failing end-to-end test asserting that a generated request is represented in the rollout state and that candidate mapping is preserved without recomputation.
- [ ] Run the test and verify the missing integration evidence.
- [ ] Make the smallest runner/algorithm adjustment required by the test; do not alter the established PPO objective.
- [ ] Run `pytest tests/e2e/test_training_smoke.py tests/marl -q`.
- [ ] Run `pytest -q`, `python -m compileall -q src scripts`, and `git diff --check`.
- [ ] Review the complete diff, commit, and push `feature/problem2-code-framework`.
