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

## Fix Round 1

The independent review identified two Critical and eight Important contract
gaps. This round closes them without changing the scientific scope:

- Raw validation now accepts an exact expected provenance mapping, binds the
  frozen reduction epsilon, includes all registered direct mechanism metrics,
  accepts all frozen learning methods, enforces six UAV/four vehicle actions,
  recomputes pesticide conservation, and rejects non-finite or negative direct
  measurements.
- Ledger replay validates prior state, legal transitions, attempt monotonicity,
  lease ownership, and metadata. Same-identity retry records `failed -> pending
  -> running`; identity drift is field-mapped rather than set-based.
- Quarantine preserves arbitrary bytes unchanged. Artifact manifests validate
  digest fields and resolve output paths beneath the true frozen root.
- Sealed guards normalize path-like values and reject boolean lock counters.
  GPU telemetry is finite and non-negative, with optional atomic inter-process
  coordination for future schedulers.
- G6/G7 preflight wrappers now expose read-only audit functions covering frozen
  contract/registry hashes, source/remote parity and cleanliness, G4 lineage,
  road-cache provenance, output confinement, disk/runtime state, manifest
  sealed-identity absence, and queue/sealed-access invariants. They still fail
  closed at the current G5 gate and never create a queue.

Fix-round verification: focused Task 8 `44 passed`; G3/G5 `342 passed`; G2/G4
`178 passed`; compileall, all CLI `--help`, and `git diff --check` passed.

## Fix Round 2

The scoped re-review required all evidence-boundary defaults to fail closed.
This round makes the complete expected provenance mapping mandatory for raw
and validated evidence, recomputes the Task 7 canonical training identity, and
requires the evaluation identity to equal that canonical digest (comparison
schema fixtures may explicitly use `verify_identity=False`). Ledger replay
rejects duplicate initial events, completed identity drift transitions to
stale, and the default GPU lease now fails closed without an atomic shared
coordination path. Validated and locked artifact manifests require existing
output files whose bytes match the declared SHA-256; design-only records retain
the only nullable provenance allowance. Integer and boolean domains remain
strict. Read-only G6/G7 preflight now checks local/upstream/origin parity,
source cleanliness, frozen manifest hash, G4 audit markers, road-cache tuple,
lock status/count/gate/resource flags, runtime/disk fields, and sealed IDs
without creating a queue or mutating the lock.
