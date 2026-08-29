# G6 Readiness Phase 2 Audit

Date: 2026-08-29

## Scope

Phase 2 implements the minimum G6 readiness contracts identified by
`HANDOFF_G6_READINESS_PHASE1.md`. It remains a readiness milestone at maturity
`M2`; it does not authorize formal training, validation evaluation, or the G7
sealed-test unlock.

## Implemented Contracts

- `problem2.training.conditions` resolves the six required condition IDs to
  explicit vehicle-controller, trainability, and training-mode semantics.
- Selected refit dispatch forwards the executable outer condition while
  retaining the selected learning method and candidate identity.
- `problem2.evaluation.selection` validates complete validation coverage for
  `20000-20049`, rejects duplicate/mixed/sealed rows, applies the frozen
  four-level ordering, and retains all candidate rows.
- Ledger events now carry UTC time, host, process, attempt, and artifact hash
  metadata; checkpoint recovery can validate an expected SHA-256 while using
  the retained previous valid copy.
- `build_formal_freeze_payloads` and `freeze_g5.py` bind source scope,
  deterministic scheduler order, positive storage/GPU estimates, dynamic
  ecology/output, deterministic evaluation, and a maintained evaluator hash.
- Replacement manifests are stored only under
  `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/manifests/`.
- The shared read-only preflight exposes the complete G6 entry contract and
  reports atomic-write disk headroom without creating a queue or mutating the
  sealed lock.
- `run_g6_jobs.py`, `resume_g6_jobs.py`, and `preflight_g6.py` are import-safe
  wrappers with callable `main()` entry points.

## Verification

```text
python -m pytest tests/g6 -q --tb=short                         40 passed
python -m pytest tests/g5/test_experiment_matrix.py -q          8 passed
python -m pytest tests/g5/test_physical_candidate_training.py \
  tests/g5/test_task12_remediation2.py::test_selected_refit_runner_uses_physical_development_training -q
                                                                  52 passed
python -m pytest -q                                             905 passed
python -m compileall -q src scripts                            exit 0
git diff --check                                                pass
```

The full regression initially reported four expected dirty-tree failures in
the G5 experiment-matrix tests; after the implementation commits were made and
the tracked tree was clean, the same tests passed and the final full run was
`905 passed`.

## Boundary Audit

- No G6 training job was started.
- No validation scenario content was read or evaluated.
- No sealed scenario ID/content was accessed; actual unlock count remains `0`.
- Historical `outputs/problem2_sr_mappo_v1/g5/` evidence was not modified.
- Protected external assets, OSM inputs, and pre-existing untracked directories
  were not modified or staged.
- Battery replenishment remains inactive and pesticide is the only replenished
  resource.

## Persistence

- Content commit `b34a5124470a1f22abe94cd345a9a081b23ca5db`:
  `feat: implement g6 readiness phase 2 contracts`.
- Dynamic-manifest binding commit
  `d648378ce509b226d5803d57a72cd2344fbc244f`:
  `docs: bind dynamic g6 manifests to phase 2 source`.
- Both commits were pushed to
  `origin/codex/problem2-dynamic-pest-model` before this state record.

## Decision

Phase 2 readiness contracts pass at `M2`. The next authorized action is Phase 3
dynamic G3-G5 revalidation and replacement freeze. Formal G6 execution remains
blocked until that work and the later full read-only preflight pass. No
efficacy, superiority, significance, formal-result, deployment, or universal-
optimality claim is permitted.
