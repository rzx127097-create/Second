# Task 5 Implementation Report

## Scope

Task 5 implemented heterogeneous discrete MADDPG and IQL for the Problem 2
G5 method family. The public method identity remains `SR-MAPPO`; no HAPPO or
`AG-SR-MAPPO` implementation was added. The work remains at the M2 boundary:
implementation and scoped tests are verified, but no pilot, validation tuning,
formal job, sealed evaluation, efficacy claim, or superiority claim was run.

The protected `_tmp_docx_assets/` directory was preserved and was not staged.
The unauthorized temporary plan file was removed.

## RED Evidence

Focused tests were written before production implementation. The first focused
run failed during collection because the new IQL module did not yet exist:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_off_policy_algorithms.py -q
```

Observed output:

```text
ERROR collecting tests/g5/test_off_policy_algorithms.py
ModuleNotFoundError: No module named 'problem2.algorithms.iql'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

This was the expected missing-module RED, rather than a test syntax or
environment error.

## Changed Files

- `src/problem2/algorithms/__init__.py`
- `src/problem2/algorithms/common/replay.py`
- `src/problem2/algorithms/protocol.py`
- `src/problem2/algorithms/iql/__init__.py`
- `src/problem2/algorithms/iql/algorithm.py`
- `src/problem2/algorithms/iql/networks.py`
- `src/problem2/algorithms/iql/trainer.py`
- `src/problem2/algorithms/maddpg/__init__.py`
- `src/problem2/algorithms/maddpg/algorithm.py`
- `src/problem2/algorithms/maddpg/networks.py`
- `src/problem2/algorithms/maddpg/trainer.py`
- `tests/g5/test_off_policy_algorithms.py`

## Implementation Decisions

- Added a strict typed `OffPolicyEnvelope` around the accepted behavior-bound
  `RoleBatch`. It carries current/next structured critic state, shared team
  reward, team and role validity, role identities, and vehicle candidate-slot
  mapping. Serialization uses an exact schema and rejects reward, mask,
  identity, candidate, shape, and non-finite-value drift.
- Extended `JointReplayBuffer` to preserve both accepted role batches and
  off-policy envelopes. Restore validates exact top-level keys, row schemas,
  sparse/full ring layout, insertion index, size, and replay RNG state before
  mutating live state.
- Extended the existing factory for all frozen `c01`-`c04` MADDPG and IQL
  candidates while retaining on-policy rejection of raw role batches and
  off-policy envelopes.
- MADDPG uses one shared UAV discrete actor, one vehicle actor, centralized
  role-specific Q critics, matching target networks, replay, soft target
  updates, and masked straight-through Gumbel-Softmax. Illegal actions have
  exactly zero relaxed mass and zero actor gradient.
- IQL uses shared UAV and separate vehicle role-local Q/target-Q networks,
  role-specific replay and optimizers, masked epsilon-greedy behavior, and
  masked bootstrap maxima that reject all-false masks. Target-update cadence
  is checkpointed per role, so the frozen interval is measured independently
  for the UAV and vehicle learners.
- Deterministic evaluation uses masked actor argmax or masked Q argmax and
  does not mutate exploration or replay state. Checkpoint state includes
  method networks, target networks, optimizer state, exploration counters,
  replay state, trainer counters, configuration, and diagnostics.

## GREEN Evidence

Focused off-policy suite after implementation and resume-test addition:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_off_policy_algorithms.py -q
```

Observed output:

```text
..................                                                       [100%]
18 passed in 16.03s
```

Follow-up role-local target-update regression (test-first correction):

```powershell
pytest -q tests/g5/test_off_policy_algorithms.py::test_iql_target_update_interval_is_role_local
```

RED observed output: `1 failed`; the pre-fix assertion observed
`{'uav': 0, 'vehicle': 1}` after one update for each role, while the expected
role-local counters were `{'uav': 0, 'vehicle': 0}`.

GREEN observed output:

```text
.                                                                        [100%]
1 passed in 9.01s
```

Protocol and checkpoint regressions:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q
```

Observed output:

```text
...........................                                              [100%]
27 passed in 9.30s
```

G3 regression:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g3 -q
```

Observed output:

```text
.................................................................        [100%]
65 passed in 25.65s
```

G5 regression:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5 -q
```

Observed output:

```text
........................................................................ [ 39%]
........................................................................ [ 78%]
.......................................                                  [100%]
183 passed in 27.17s
```

Compilation and contract audit:

```powershell
.venv-g5\Scripts\python.exe -m compileall -q src scripts
```

Observed output: no output; exit code `0`.

```powershell
.venv-g5\Scripts\python.exe scripts/audit_g5_contracts.py
```

Observed result: JSON status `pass`, methods included `maddpg_mobile` and
`iql_mobile`, `validation_accessed` was `false`, `sealed_accessed` was
`false`, and `actual_unlock_count` was `0`.

Diff validation:

```powershell
git diff --check
```

Observed result: no content errors. Git emitted only existing Windows line
ending normalization warnings for modified Python files.

## Full Regression Limitation

The final host full-suite command was intentionally not rerun after the user
directed handoff continuation:

```powershell
python -m pytest -q
```

The prior final-tree attempt was interrupted by the user at approximately 14%
after partial dot output and produced no test failure or final count. Before
the final resume test was added, an earlier host run completed with `479 passed
in 189.77s`; that count is not claimed as a final-tree full-regression result.
Per instruction, the full suite was not rerun.

## Self-Review Concerns

- The final host full regression is incomplete because it was intentionally
  interrupted; the focused, protocol/checkpoint, G3, and G5 suites are the
  completed evidence for this handoff.
- Repository-generated Python caches, `.pytest_cache`, and the generated
  `.egg-info` directory were removed after verification. The isolated
  `.venv-g5` dependency environment was left intact and no generated cache or
  environment file is part of the implementation commit.
- No pilot or later-gate execution was performed, and the M2 stop boundary is
  unchanged.

## Commit

Implementation commit:

```text
caf4277 feat: implement heterogeneous maddpg and iql
```

The report is recorded as a separate handoff-only documentation commit after
the implementation commit so this report can contain the verified
implementation hash.

## Fix Round 1

The reviewer identified two important validity and scheduling defects. Both
were verified against the current data flow before implementation:

1. MADDPG discarded `valid_actor_sample` in `_batch_tensors`, so invalid role
   samples still reached the selected role critic and actor updates.
2. IQL used the aggregate `update_count` for target synchronization, so the
   UAV and vehicle target intervals depended on update-call ordering instead
   of each role's own optimizer-update count.

TDD RED for the MADDPG validity reproducer:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_off_policy_algorithms.py::test_maddpg_excludes_invalid_role_samples_from_updates -q
```

Observed output: `2 failed`; both parameterizations reported nonzero critic
and actor losses for an all-invalid selected role (`critic_loss` 3.3317897 /
2.4670615 and nonzero `actor_loss`).

TDD GREEN for the MADDPG validity fix:

```text
..                                                                       [100%]
2 passed in 9.71s
```

The fix retains team validity and additionally requires all stored
role-validity entries for the selected role before critic, actor, and target
updates. IQL now persists and uses `role_update_count` independently for UAV
and vehicle target scheduling.

Dedicated IQL cadence regression:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_off_policy_algorithms.py::test_iql_target_update_interval_is_role_local -q
```

```text
.                                                                        [100%]
1 passed in 10.47s
```

Amended verification:

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_off_policy_algorithms.py -q
```

```text
....................                                                     [100%]
20 passed in 10.59s
```

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q
```

```text
...........................                                              [100%]
27 passed in 3.82s
```

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g3 -q
```

```text
.................................................................        [100%]
65 passed in 23.24s
```

```powershell
.venv-g5\Scripts\python.exe -m pytest tests/g5 -q
```

```text
........................................................................ [ 38%]
........................................................................ [ 77%]
.........................                                [100%]
185 passed in 29.50s
```

The minor reviewer findings concerning replay-capacity type validation,
stronger Gumbel-gradient assertions, and explicit replay ring/resume test
coverage remain deferred by controller. No registry, pilot, or full-suite
execution was performed.
