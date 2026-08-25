# Task 8 Report: G5 Orchestration And Evidence Validation

## Scope

Task 8 adds the append-only orchestration and evidence-integrity boundaries
required before any G6 formal execution. It does not run pilots, formal jobs,
validation tuning, or sealed evaluation.

## Implementation

- `experiments.ledger.AppendOnlyLedger` stores immutable JSONL transition
  events, rebuilds materialized state on reload, enforces legal state changes,
  exclusive `(identity, attempt, lease_id)` ownership, same-input retries, and
  fail-closed stale drift handling.
- `experiments.orchestrator` provides deterministic method/scale/seed ordering
  and a single-owner GPU telemetry lease for a future scheduler.
- `experiments.artifacts` and `experiments.recovery` provide fsync-backed
  atomic byte/checkpoint writes, content hashes, verified reload, and the
  `<checkpoint>.previous` recovery sibling.
- `evaluation.schema` defines strict raw, validated-table, and artifact-manifest
  contracts. `evaluation.validator` rejects malformed identities, non-finite or
  inconsistent metrics, terminal/counter errors, illegal actions, battery
  replenishment, conservation residuals, partition violations, duplicates, and
  incomplete expected cells. Quarantine preserves exact UTF-8 bytes (base64),
  locator, reason, and source SHA-256.
- `evaluation.sealed_lock` is the public fail-closed boundary for partition,
  path, truthy-flag, lock-count, and G7-unlock checks. The eight G5/G6/G7
  scripts are thin dry-run guards and cannot execute jobs or mutate the sealed
  lock during G5.
- G5 evidence schema YAML files are recorded below `docs/evidence/g5`.

## Verification

- `tests/g5/test_orchestration_and_validation.py tests/g5/test_sealed_guards.py`:
  `33 passed`.
- `tests/g3 tests/g5`: `331 passed`.
- `tests/g2 tests/g4`: `178 passed`.
- `python -m compileall -q src scripts`: passed.
- All eight public CLI `--help` calls: passed.
- `git diff --check`: passed.

## Boundary and concerns

The implementation remains at the accepted M2 boundary. G6/G7 preflight and
execution entry points intentionally fail closed while the current gate is G5;
no formal or sealed data was read or generated. The controller must independently
review this report, update `docs/PROJECT_STATE.md`, commit, push, and verify
three-way remote parity before Task 8 is considered persisted.
