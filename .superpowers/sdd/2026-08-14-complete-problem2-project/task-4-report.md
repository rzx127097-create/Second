# Task 4 Report: Fair Baseline Adapters

## RED/GREEN

- RED: `pytest -q tests/e2e/test_baseline_protocol.py` failed during collection because `PRIMARY_METHODS` and `make_policy` were not registered.
- GREEN: the focused protocol and legacy baseline tests pass (`7 passed`), followed by the full suite (`114 passed`).

## Method registry and configuration metadata

The primary registry is exactly:

`sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`, `sr_mappo_two_stage`.

`teleport_service` and `unlimited_supply` remain importable diagnostic baselines but are not registered. Each adapter exposes `name`, `frozen=True`, `act(snapshot)`, `smoke_only`, and `formal_ready`. Smoke adapters are deterministic and explicitly rejected by formal evaluation. Checkpoint adapters validate the path immediately and lazily infer actor dimensions from the first snapshot before loading through `load_evaluation_checkpoint`.

The machine-readable metadata contains all configured SR-MAPPO stability components. `mappo_mobile` disables only observation and return normalization and labels the method as a same-source heterogeneous MAPPO ablation. `sr_mappo_two_stage` records its two-stage initialization protocol. No method metadata changes environment resources or horizon.

## Fairness evidence

The end-to-end smoke test builds a fresh `s1` `ScenarioBundle` with seed 7 for every method, runs the same horizon, and asserts identical scenario identity, pesticide-initial total, and UAV/vehicle agent IDs. Policies only read `DecisionSnapshot` observations, masks, and candidate mappings. Every emitted action is passed through `actions_to_environment`; vehicle actions are limited to `hold` or currently valid `slot-*` candidates. Resource conservation is asserted after each episode and policy calls do not mutate resource state.

Rolling A* compatibility remains available through its standalone `plan(graph, current_node, requests)` API. The registered adapter uses only the current snapshot candidate routes and never receives future scenario state.

## Verification commands

- `pytest -q tests/e2e/test_baseline_protocol.py tests/baselines/test_baselines.py` -> `7 passed`
- `pytest -q` -> `114 passed`
- `python -m compileall -q src tests` -> success
- `git diff --check` -> success

## Commit

Subject: `feat: expose fair common baseline protocol`

SHA: `0bc6b5f3d9e3f589a560b15011e9c15eb2dae4c7`.

## Concerns

- The no-checkpoint adapters are smoke-only deterministic policies, not trained model claims.
- Formal checkpoints still require dimensions compatible with the first evaluation snapshot; malformed payloads are rejected by the shared checkpoint loader.

## Review Fixes (2026-08-14)

- RED: the added regression tests initially failed four cases: role-first smoke actions were copied across UAVs; A* and fixed-support checkpoint paths did not invoke `_load_algorithm`; fixed support allowed a learned vehicle slot; and two-stage metadata lacked an explicit training protocol.
- GREEN: `pytest -q tests/e2e/test_baseline_protocol.py` -> `7 passed`; `pytest -q` -> `118 passed`; `python -m compileall -q src scripts` and `git diff --check` -> success.
- A* now loads the checkpoint algorithm, preserves learned UAV actions, and overrides only the vehicle with a currently valid candidate slot or hold. Fixed support loads learned UAV actions but forces every vehicle to legal hold while retaining `support_node` and `vehicle_id`.
- Checkpoint factories receive the declared stability-component map; `mappo_mobile` disables only observation/return normalization. Two-stage adapters expose `initialization` and `training_protocol` metadata and remain smoke-only without checkpoints.
- Policy purity is tested by comparing pesticide totals, UAV onboard amounts, vehicle inventories, and adapter vehicle nodes before/after `policy.act`; only `ScenarioBundle.step` performs transitions and conservation checks.
- Review-fix commit SHA: `aaa07c0dd7b3b090b8bc5a2f6cdf44f30733ef04`.

## Rolling Candidate Fix

- RED: the new regression test failed because a learned vehicle `slot-0` survived when `candidate_mapping` was empty, and `deterministic=False` was not forwarded to the actor.
- GREEN: focused baseline/e2e tests -> `12 passed`; full suite -> `119 passed`; `python -m compileall -q src scripts` and `git diff --check` -> success.
- Every vehicle in the rolling adapter now receives the first deterministic currently valid candidate slot, or explicit legal `hold` when no candidate exists. Formal learned calls thread the adapter's `deterministic` argument through the actor.
- Commit SHA: `49a55e89e723c6259b923eabaec26d40c745bff9` (`fix: constrain rolling planner candidate actions`).
