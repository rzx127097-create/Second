# Task 5 Report: Persisted Jobs, CLIs, and Recovery

## Scope completed

- Replaced the placeholder train, evaluation, and matrix scripts with JSON-only
  command-line boundaries that use the existing `ScenarioBundle`, SR-MAPPO
  rollout runner, evaluation protocol, and checkpoint loader.
- Added immutable SHA-256 job IDs over method, scale, training seed, config
  hash, and Git commit. Job JSON records are atomically written and include
  `job_id`, identity fields, status, attempts, checkpoint path, and full error
  traceback.
- Added identity-preserving failed-job retries, retry limits, completed-job
  no-op behavior, and missing/corrupt checkpoint diagnostics. Failed workers
  retain their full exception text; CLI failures return nonzero with a JSON
  error payload.
- Enriched raw episode JSONL rows at the runner boundary with the complete
  long-format trace identity required by `validate_logs.REQUIRED_FIELDS`:
  run ID, method, scale, seed, scenario, config hash, Git commit, reduction,
  success, and physically logged transferred pesticide.
- Migrated the formal matrix to the canonical `sr_mappo_astar` key without a
  compatibility alias.

## Gates and isolation

Both the parameter registry and formal matrix are still provisional. Training,
evaluation, and matrix execution reject formal runs without `--smoke`; dry-run
only enumerates immutable jobs and writes no execution outputs. Smoke uses the
real CPU training/evaluation path with a deliberately short rollout. Evaluation
checks that the requested scenario belongs to its requested split. `sealed_test`
remains blocked while provisional and otherwise continues through deterministic
frozen-policy evaluation checks.

## Tests and verification

- RED recorded: `pytest tests/e2e/test_cli_and_recovery.py -q` initially failed
  at collection because `load_job_record` did not exist.
- Focused: `pytest tests/e2e/test_cli_and_recovery.py tests/integration/test_job_recovery.py -q`
  passed `8` tests.
- Full: `pytest -q` passed `124` tests.
- `python -m compileall -q src scripts` and `git diff --check` passed.

## Maturity and remaining boundary

This task reaches M2 implementation verification only. The configurations and
all smoke outputs remain provisional simulation interfaces, not formal results
or deployment evidence. M3/M4 still require verified engineering parameters,
frozen validation/formal matrix, and sealed-test evidence.

## Review Fix Addendum

- **Identity refusal:** `evaluate.py` now requires the persisted completed job
  JSON, canonicalizes the checkpoint path, verifies the recorded path and
  current configuration hash, and never synthesizes a fallback identity.
- **Checkpoint integrity:** `JobRunner` validates the canonical format-2
  checkpoint envelope and accepts a full evaluator validator. The training CLI
  supplies `load_evaluation_checkpoint`, so missing, malformed, or incompatible
  checkpoints move a completed job to failed with the complete diagnostic.
- **Matrix method coverage:** smoke enumeration preserves method identities for
  all five canonical methods. Only the mobile training worker is implemented;
  every other selected method is returned as an explicit rejected job rather
  than silently omitted. A matrix without `sr_mappo_mobile` is explicitly
  rejected, and empty execution cannot report completed.
- **Sealed split:** `sealed_test` is always passed unchanged to
  `evaluate_policy`; `--smoke` only changes provisional/short-run settings and
  cannot substitute the smoke split.
- **Path handling:** training records absolute checkpoint paths and evaluation
  compares resolved paths, avoiding Windows relative-path ambiguity.

Covering tests:

- `test_evaluate_cli_rejects_checkpoint_without_persisted_job_identity`
- `test_completed_job_rejects_corrupt_checkpoint_before_worker`
- `test_matrix_smoke_reports_each_method_instead_of_silently_skipping_methods`
- `test_matrix_smoke_rejects_matrix_without_mobile_method`
- `test_sealed_test_never_changes_to_smoke_split`

Verification after fixes:

```text
pytest tests/e2e/test_cli_and_recovery.py::test_sealed_test_never_changes_to_smoke_split tests/e2e/test_cli_and_recovery.py::test_matrix_smoke_rejects_matrix_without_mobile_method -q
2 passed in 3.13s
pytest -q
129 passed in 38.42s
python -m compileall -q src scripts       [exit 0]
git diff --check                         [exit 0]
```
