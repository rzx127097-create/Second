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
