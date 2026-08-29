# G6 Readiness Phase 1 RED Audit

Date: 2026-08-29

## Scope

This audit records the test-first boundary for G6 readiness remediation. It
does not authorize or execute a G6 training job, validation evaluation, or G7
sealed evaluation. The repository remains at maturity `M2`.

The focused tests are under `tests/g6/` and cover:

- exact frozen source and source-scope binding;
- clean tracked state and local/upstream/remote parity rejection;
- runner, recovery, checkpoint-validator, evaluator, and preflight entry;
- deterministic scheduler order, storage/GPU estimates, and disk headroom;
- canonical identities, duplicate rejection, append-only attempts, retry, and
  stale-input handling;
- atomic checkpoint rotation, reload, expected-hash validation, and retention
  of the previous valid checkpoint;
- validation IDs `20000-20049`, sealed-input rejection, frozen checkpoint
  selection, and complete row coverage;
- executable semantics for fixed, A*, nearest, urgency, and two-stage
  conditions;
- `dynamic_pest_v1` and dynamic output-root binding;
- the exact `sr_mappo_mobile` restriction for ablation and sensitivity jobs.

## Verification

Relevant pre-edit baseline:

```text
python -m pytest tests/g5/test_orchestration_and_validation.py tests/g5/test_checkpoint_resume.py tests/g5/test_sealed_guards.py tests/g5/test_validation_tuning.py tests/g5/test_task12_remediation2.py -q
120 passed in 57.44s
```

Phase 1 RED command:

```text
python -m pytest tests/g6 -q --tb=short
30 failed, 10 passed in 18.01s
```

The nonzero exit is the required RED result. Collection completed normally;
the failures are caused by missing or stale G6 behavior rather than syntax or
test-discovery defects.

## RED Findings

The 30 failures resolve into these implementation blockers:

- 11 condition-semantics failures: selected refit dispatches every outer
  condition as `sr_mappo_mobile`, and no executable condition resolver exists;
- 9 entry/freeze failures: complete preflight checks, source-scope binding,
  scheduler/resource estimates, disk headroom, and import-safe
  runner/recovery/preflight entry points are absent;
- 2 recovery-evidence failures: ledger events lack complete host/process/time
  and artifact metadata, and recovery cannot validate an expected checkpoint
  hash;
- 8 validation/dynamic failures: deterministic-policy, evaluator, dynamic
  ecology/output, and replacement-manifest bindings are absent, and frozen
  checkpoint selection with complete validation-row coverage is not
  implemented.

The 10 passing tests confirm that the reusable baseline still enforces:

- exact source-commit propagation by the freeze generator;
- dirty tracked-tree and remote-parity rejection;
- unique canonical identities and duplicate-manifest rejection;
- append-only state replay, identical-identity retry, and stale-input denial;
- the frozen validation ID range and sealed-input refusal;
- `sr_mappo_mobile`-only ablation and sensitivity jobs.

## Boundary And Next Step

No production source, runner, manifest, historical G5 output, protected
external asset, OSM input, validation scenario content, or sealed scenario
content was modified or accessed. No G6 or G7 job was started.

Phase 1 is complete when these tests and this audit are committed, pushed, and
recorded in `docs/PROJECT_STATE.md`. Phase 2 may then implement the minimum
shared G6 runner, recovery, validation-selection, condition-execution, and
complete preflight behavior needed to turn the focused suite GREEN. Formal G6
execution remains blocked until the later replacement dynamic G5 freeze and
full preflight pass.
