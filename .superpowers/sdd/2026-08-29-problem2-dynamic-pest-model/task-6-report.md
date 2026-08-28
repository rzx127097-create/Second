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

## Fix Round 1

Review findings were verified against the current implementation before
changes. The fix remains bounded to dynamic validation compatibility, exact
wrapper view restoration, and static diagnostic construction guards. No plan,
project-state record, historical G5 output, validation artifact, or sealed
scenario was modified.

### RED

Three regression tests were added before the fix:

- Dynamic growth with no spray failed because
  `validate_validation_episode` accepted only
  `action_driven_environment` and rejected the dynamic metric source.
- The unsigned dynamic reduction regression failed at the same stale metric
  source check.
- Exact wrapper view restoration failed with `KeyError: 'current_view'` because
  the wrapper state did not contain the current view.
- Static constructor enforcement failed because direct construction without a
  diagnostic purpose/output root did not raise.

### GREEN

The focused fix regressions passed:

```text
tests/g5/test_validation_tuning.py dynamic regressions: 2 passed in 7.34s
tests/ecology/test_dynamic_environment.py current-view restore: 1 passed in 1.84s
tests/g5/test_physical_candidate_training.py static guard: 1 passed in 9.85s
```

The complete directly affected validation module then passed:

```text
python -m pytest tests/g5/test_validation_tuning.py -q
22 passed in 25.23s
```

The wrapper module had already passed `6 passed` before the fix round, and the
new exact-view regression passed after the state changes. No broad repository
suite was run.

### Fixes

- `validate_validation_episode` now preserves legacy static-row rules while
  accepting dynamic rows with signed reduction, growth beyond initial prey,
  predation-driven reduction, and zero spray.
- `scripts/run_g5_validation_tuning.py` now emits dynamic prey fields, direct
  signed reduction, dynamic metric provenance, and the ecology scenario
  locator.
- `DynamicPestEnvironment.state_dict()` now stores a detached current view and
  `load_state_dict()` restores it exactly while retaining physical legality
  state and the saved pre-step ecology context.
- `ActionDrivenValidationEnv` requires explicit development static-diagnostic
  purpose/output scope for direct construction; its internal legacy path is
  private and static adapters remain `primary_eligible=False`.
- Existing static adapter tests now pass explicit diagnostic scope.

### Remaining Concern

The full wrapper module was not rerun after every Fix Round 1 edit because the
user requested immediate finalization after the affected validation module
completed. The exact-view regression and all 22 validation tests passed after
the changes; the prior wrapper baseline was `6 passed`.
