# Task 3 report

## TDD evidence

- RED: `pytest tests/e2e/test_evaluation_smoke.py -q` failed during collection with `ImportError: cannot import name 'evaluate_policy'`.
- GREEN: `pytest tests/e2e/test_evaluation_smoke.py -q` -> `4 passed`.

## Interfaces and semantics

- Added `PolicyProtocol`, `HoldPolicy`, `AlgorithmPolicyAdapter`, and `actions_to_environment` in `src/problem2/experiments/policy_protocol.py`.
- Added `evaluate_policy(policy, scenario_factory, *, scenarios, split, deterministic)` returning `EpisodeRecord` values.
- Evaluation resets each exact scenario ID, uses only role-local observation vectors in the SR-MAPPO adapter, and converts numeric actor outputs through the current snapshot `ActionMask` before `ScenarioBundle.step`.
- `smoke` is the only split that permits provisional scenarios. `train`, `validation`, and `sealed_test` call `assert_formal_ready()`; sealed test also requires a named frozen policy.
- `EpisodeRecord.to_row()` now includes `scenario_id`, `split`, and `policy_name` while preserving existing fields and callers.

## Determinism and checkpoint evidence

The smoke test evaluates a hold policy twice on `s1` and compares all metric rows and emitted events. SR-MAPPO evaluation uses `algorithm.evaluate()`/`eval()` and does not update running normalization statistics or optimizer state. `load_evaluation_checkpoint()` delegates to atomic `load_checkpoint`, rejects missing paths, malformed payloads, unsupported format, and missing/invalid step metadata, and leaves the loaded algorithm in evaluation mode.

## Verification

- `pytest tests/e2e/test_evaluation_smoke.py -q` -> `4 passed`.
- `pytest tests/e2e/test_training_smoke.py tests/integration/test_job_recovery.py tests/e2e/test_scenario_factory.py -q` -> `7 passed`.
- `pytest -q` -> `100 passed`.
- `python -m compileall -q src scripts` -> passed.
- `git diff --check` -> passed (only normal LF/CRLF conversion notices from Git).

## Concerns

Formal scenario parameters remain provisional in the repository, so formal validation/sealed-test evaluation is intentionally blocked until the parameter registry is verified. No Word documents were modified.

Commit SHA: `8229162` (superseded by the final amend if this line changes).
