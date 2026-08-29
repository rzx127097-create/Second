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
