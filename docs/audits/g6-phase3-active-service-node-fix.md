# G6 Readiness Phase 3: Active Service-Node Observation Fix

Date: 2026-08-29

## Scope

This bounded development-correctness fix addresses the reproduced nearest and
urgency controller failure in `Problem2CooperativeEnv`. An active dispatch keeps
its original request identity, sampled slot, and selected service node while
the UAV may move outside the current rendezvous radius. The active observation
must therefore retain that locked node for controller validation. Unrelated
nodes remain excluded.

The change is M2 engineering evidence only. It does not authorize formal G6
jobs, validation or sealed evaluation, efficacy or superiority claims, or any
historical-output rewrite.

## Root Cause And Fix

`_controller_decision(active=...)` rebuilt every `ObservableRequest.service_nodes`
tuple solely from the UAV's current radius. Nearest and urgency active branches
intentionally returned `observation.selected_service_node`, so validation then
rejected the controller's locked node as absent from the request options.

The observation builder now appends the locked node only for the active request
when it is outside the current-radius tuple. Candidate/request mapping and the
existing service-node, component, reachability, and route-length validation are
unchanged.

## TDD And Verification

- RED: the new active nearest/urgency regression failed twice with
  `ValueError: controller service node is not allowed for the selected request`.
- GREEN: `python -m pytest tests/g6/test_controller_wiring.py -q` -> `6 passed`.
- Focused controller/environment/heuristic suite:
  `python -m pytest tests/g6/test_controller_wiring.py tests/g5/test_heuristics.py tests/g5/test_environment_metrics.py -q --tb=short`
  -> `39 passed`.
- Direct development-only dynamic path (`g20x20_d2`, scenario `10000`,
  8 physical steps) completed for both `sr_mappo_nearest` and
  `sr_mappo_urgency`.
- `python -m compileall -q src scripts` -> exit `0`.
- `git diff --check` -> no content errors.

The regression captures the active request observation and asserts that the
current-radius node plus the locked node are present, while a controller that
selects the unrelated middle node is still rejected.

## Boundary

No validation or sealed scenario payloads were accessed. No formal jobs ran.
Pesticide-only replenishment and inactive battery semantics are unchanged.
