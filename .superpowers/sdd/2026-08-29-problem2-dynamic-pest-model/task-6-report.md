# Task 6 Report: Integrate Accepted Physical Spray Events And Signed Rewards

Date: 2026-08-29

## Scope

Task 6 integrates the physical `Problem2CooperativeEnv` with the dynamic
Holling-Tanner ecology. The physical environment remains authoritative for
legal actions, event production, and pesticide litre conservation. The new
wrapper consumes only finite positive physical spray events after
`physical.step`, maps their action-complete metric positions to ecology cells,
advances ecology once per physical decision step, and publishes signed
ecological rewards and diagnostics.

The default development and validation factories now construct
`DynamicPestEnvironment`. The former local subtraction adapter remains
available only through `build_static_diagnostic_environment`, which requires
the development partition, the exact static diagnostic purpose, an output root
outside the G5 primary/validation/sealed namespace, and exposes
`primary_eligible=False`.

## TDD Evidence

### RED

Test-first integration tests were added in
`tests/ecology/test_dynamic_environment.py` before the production wrapper
was created. The required command:

```text
python -m pytest tests/ecology/test_dynamic_environment.py -q
```

failed during collection with:

```text
ModuleNotFoundError: No module named 'problem2.training.dynamic_env'
```

This was the expected missing-feature failure.

### GREEN

After implementation, the same focused wrapper command passed freshly:

```text
6 passed in 1.74s
```

The tests cover accepted positive spray versus zero-delta rejection, radial
deposit mapping, signed negative growth reward and growth beyond initial prey,
matched spray/no-spray counterfactual behavior, physical pesticide
conservation, exact wrapper state restoration, and static diagnostic
restrictions.

The directly affected physical test selection was run once to completion
before the final metric-state hardening and returned:

```text
13 passed, 37 deselected in 48.97s
```

A fresh rerun after the final hardening was intentionally interrupted at the
user's request while still executing. It produced seven progress dots and no
failure output; therefore this report does not claim a completed rerun for
that selection.

## Implemented Changes

- Added `DynamicPestEnvironment` with accepted-event filtering, ecology
  stepping, signed team reward, dynamic provenance, ecology/predator,
  concentration, wind, and deposited-effect diagnostics.
- Added detached physical/ecological state serialization, including physical
  state, dispatch cursor, candidate nodes, metric accumulators, sampled
  actions, ecology state, and immutable scenario identity.
- Switched default development and validation factories to deterministic
  dynamic ecology scenarios.
- Added explicit static diagnostic construction and fail-closed primary
  training checks.
- Updated physical episode logging to stable `initial_prey`/`prey` properties
  and direct dynamic ecology fields.
- Kept pesticide conservation and battery-disabled semantics unchanged.

## Concerns And Boundary

This is Task 6 integration evidence only. It does not claim full G5
readiness, formal efficacy, superiority, validation tuning, sealed evaluation,
or a maturity increase. The long physical test selection was not rerun to
completion after the final hardening because execution was interrupted; the
last completed focused physical result is recorded above.
