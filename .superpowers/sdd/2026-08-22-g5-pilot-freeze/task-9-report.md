# Task 9 Fix Report

## Review Closure

The scoped Task 9 review findings were addressed in the follow-up fix commit.
The two JSON adapters now bootstrap the repository source tree, require
explicit `validated: true` provenance with a non-sealed partition, reject raw
or sealed locators before opening a path, and confine explicit input/output
paths to `outputs/problem2_sr_mappo_v1`.

The paired estimator now requires a declared ordered `method_order` for
method/value rows and preserves that A-B direction. Explicit `value_a` and
`value_b` rows remain ordered by field name. Convergence rejects
`finite: false`, requires one frozen scale, and reports mixed-seed threshold
censoring conservatively at the budget boundary. Mechanism summaries enforce
typed direct metrics, exact mobile/fixed method identities, and scenario,
training-seed, scale, and aggregate sign coherence. Diagnosis validates all
audit statuses, retains unresolved stages, and is complete only when all seven
ordered stages pass. Holm and equivalence inputs reject booleans and string
coercion.

No experiments, validation scenarios, sealed scenarios, locks, or raw evidence
files were accessed.

## Verification

- Focused Task 9 tests: `12 passed`.
- G3/G5 regression and G2/G4 regression were rerun after the fix.
- Both CLI `--help` commands run from the repository checkout.
- `compileall` and `git diff --check` pass.
