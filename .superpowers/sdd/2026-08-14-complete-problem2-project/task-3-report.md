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

## Review hardening

- RED: `pytest tests/e2e/test_evaluation_smoke.py -q` -> 2 failures: sealed-test provisional guard masked the deterministic/frozen contract, and the test exposed the trainer's `optimizers` state API.
- GREEN: `pytest tests/e2e/test_evaluation_smoke.py -q` -> `13 passed`.
- Sealed-test now requires `deterministic=True`, a named policy, and eval capability; every evaluation enters eval mode (including stochastic smoke), freezes normalization/optimizer state, and restores prior training mode.
- Checkpoint metadata is parsed before atomic `load_checkpoint`; `format` must be exactly integer `2`, `step` exactly a non-bool non-negative integer, and returned metadata must match raw values.
- Numeric action conversion rejects booleans and non-integral float indices; action method dispatch no longer masks internal `TypeError`.
- Review fix commit SHA: `3e20d500a21fdba2c6b123b5602fb6445fb818d5`.
- Full verification after hardening: `pytest -q` -> `109 passed`; `python -m compileall -q src scripts` -> passed; `git diff --check` -> passed (only normal LF/CRLF notices).

## Frozen-marker follow-up

- RED: `pytest tests/e2e/test_evaluation_smoke.py -q` -> mutable named policy was accepted by sealed-test (`Failed: DID NOT RAISE`).
- GREEN: `pytest tests/e2e/test_evaluation_smoke.py -q` -> `15 passed`.
- `PolicyProtocol` implementations now expose an explicit `frozen` marker. `HoldPolicy` is frozen; `AlgorithmPolicyAdapter` derives it from algorithm eval state and updates it on `eval()`/`train()`.
- Sealed-test requires deterministic mode, a non-empty name, eval capability, `frozen is True`, and no active training state before scenario construction. Evaluation still enters eval mode for stochastic smoke/validation and restores prior state.
- Role-batched action flattening preserves booleans from Python sequences, NumPy arrays, and tensors before validation; booleans and non-integral floats are rejected.
- Follow-up fix commit SHA: `d0ed7856ccc70d962dc80ea538fa9497e4783942`.
- Full verification: `pytest -q` -> `111 passed`; `python -m compileall -q src scripts` -> passed; `git diff --check` -> passed (only normal LF/CRLF notices).
