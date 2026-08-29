# Rolling A* Current-Route Validation Fix

Date: 2026-08-29

## Scope

The Phase 3 development refit for `sr_mappo_mobile` under the
`sr_mappo_astar` condition failed at step 6 when the vehicle had moved from
node 100 to node 99 between rolling-plan updates. `RollingAStarController`
returned its cached 510 m route even though the current vehicle-to-service
distance had changed, so the physical environment rejected the decision.

No validation or sealed scenario payloads were accessed, and no historical
pilot output was modified.

## TDD Evidence

The regression test
`test_astar_active_dispatch_reports_current_distance_between_replans` first
ran against the pre-fix controller and failed as expected:

```text
assert 40.0 == 30.0
```

The root cause was an active-dispatch branch that only called `astar_distance`
when `replan_due` was true, then returned `cached_route_length_m` on all other
decisions. The fix computes the current distance on every active decision,
uses it for `route_length_m`, and updates cached plan state only when the
existing replan cadence is due.

After the fix:

```text
python -m pytest tests/g5/test_heuristics.py -q
18 passed
python -m pytest tests/g6/test_controller_wiring.py -q
3 passed
```

The regression confirms `replanned=False` and an unchanged `plan_version` and
cached route while returning the updated current distance.

## Boundary

This is a controller-validation correctness fix for development pilots. It is
not efficacy, superiority, formal G6, sealed-test, or deployment evidence.
