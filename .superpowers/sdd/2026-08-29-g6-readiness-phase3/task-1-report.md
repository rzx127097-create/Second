# Phase 3 Task 1 Report

## Files changed

- `src/problem2/training/cooperative_env.py`: injectable vehicle controller boundary; dispatch observations and controller-selected slot/service node are used for non-learned physical transitions. Learned mode remains sampled-action driven.
- `src/problem2/training/tuning.py`: condition-aware controller factory and forwarding through dynamic development environment construction.
- `src/problem2/training/physical_training.py`: pass condition identity when constructing development environments.
- `tests/g6/test_controller_wiring.py`: regression test for controller-selected service node.

## TDD evidence

RED:

`python -m pytest tests/g6/test_controller_wiring.py -q --tb=short` failed with `TypeError: Problem2CooperativeEnv.__init__() got an unexpected keyword argument 'vehicle_controller'`.

GREEN:

`python -m pytest tests/g6/test_controller_wiring.py tests/g5/test_environment_metrics.py -q --tb=short` -> `16 passed`.

`python -m pytest tests/g5/test_physical_candidate_training.py::test_all_methods_follow_their_frozen_physical_update_cadence tests/g6/test_controller_wiring.py -q --tb=short` -> `6 passed`.

## Design decisions

The controller receives the existing observable dispatch contract and returns `ControllerDecision`. For non-learned conditions, its slot and service node are authoritative; resource accounting and service state-machine logic are unchanged. Learned methods have no injected controller and retain the sampled vehicle action. Unknown method IDs passed as condition identities are treated as learned algorithm methods for backward compatibility.

## Commit

Implementation commit recorded after verification: `18604d4e974f6f80e39bfcb751b36b856e7022e7`.

## Unresolved concerns

The fixed-support factory selects the first primary-component road node as its deterministic support node, and rolling A* uses a fixed five-step replan interval. These are readiness defaults and require dynamic G3-G5 pilot validation before any formal G6 execution. No validation or sealed scenarios were accessed.

## Fix Round 1

Added fail-closed controller decision mapping validation, ensuring slot and request identity agree before reservation, plus condition semantics and learned-mobile regression coverage. Unknown explicit condition IDs now raise; algorithm-only methods omit condition factory dispatch. Verification: `python -m pytest tests/g6/test_controller_wiring.py tests/g5/test_environment_metrics.py tests/g5/test_physical_candidate_training.py::test_all_methods_follow_their_frozen_physical_update_cadence -q --tb=short` -> `23 passed`.

## Fix Round 2

Checkpoint provenance now binds to the learning method while outer condition metadata remains separate. Fixed-support environments place the initial vehicle at the frozen support node. Injected decisions are validated for request/slot identity, integer primary-component node, allowed service node, reachability, and exact A* route length before reservation and active replans. Focused verification: `18 passed`; compileall passed. No validation, sealed, or formal jobs were run.

## Fix Round 3

Controller-driven views now report the executed controller slot. Physical envelopes accept `vehicle_trainable`; uav-only transitions mark vehicle actor samples invalid, and update snapshots restore vehicle networks after generic updates while preserving UAV learning. Verification: controller/environment suite `18 passed`; compileall passed.

## Fix Round 4

Closed the remaining controller-isolation gaps identified in review `ca90e43..5a54e41`:

- Physical envelopes now bind the executed controller vehicle slot from the environment view. For non-learned on-policy conditions, the vehicle behavior log probability is recomputed for that executed action so behavior replay remains exact while the vehicle actor is invalidated.
- Added `_observe_physical_algorithm` to keep non-trainable IQL transitions out of vehicle replay while retaining the UAV replay row. MADDPG's joint replay is held only through the UAV update boundary and restored afterward.
- Vehicle update state is snapshotted/restored across modules, role normalizers/replay, role optimizers, schedulers, and role counters. UAV learning and shared critic updates continue.

TDD RED: `python -m pytest tests/g6/test_physical_vehicle_isolation.py -q --tb=short` failed during collection because `_observe_physical_algorithm` was not present.

Focused GREEN: `python -m pytest tests/g6/test_physical_vehicle_isolation.py -q --tb=short` -> `3 passed`.

Affecting protocol regression suite: `python -m pytest tests/g5/test_physical_candidate_training.py tests/g6/test_controller_wiring.py tests/g6/test_condition_semantics.py tests/g5/test_off_policy_algorithms.py tests/g5/test_on_policy_algorithms.py -q --tb=short` -> `198 passed in 164.81s`.

No validation or sealed scenario payloads were accessed; historical outputs remain unchanged. Phase 3 remains `M2` and no formal G6/G7 work was run.
