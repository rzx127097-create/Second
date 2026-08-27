# Task 12 Remediation 1 Report: Physical Candidate Training

## Status

Implemented the bounded G5 Task12 physical candidate-training remediation at
the existing M2 boundary. No canonical validation, 200,000-interaction job,
formal job, sealed evaluation, commit, or push was performed.

## RED Evidence

Tests were added before production changes and run against the original code:

- `test_completed_smoke_checkpoint_contains_the_post_update_policy`:
  `1 failed`; restored checkpoint digest
  `081270804cd446ba3e8db932981179736d9fc4a8e0d33e50738957018b6933d0`
  differed from post-update summary digest
  `f24dcb43ef05f1bd834ab85b3f88402fe7732a1f5582e69e442e30af9cfe74f2`.
- Same-step pest and partition factory slice: `2 failed`; spray returned the
  stale field mean `1.0` instead of `0.995`, and
  `build_development_environment` was absent.
- Dedicated physical-training suite: collection failed with
  `ModuleNotFoundError: problem2.training.physical_training`.

## Changed Files

- `src/problem2/training/physical_training.py` (new)
- `src/problem2/training/tuning.py`
- `src/problem2/training/runner.py`
- `scripts/run_g5_validation_tuning.py`
- `tests/g5/test_physical_candidate_training.py` (new)
- `tests/g5/test_validation_tuning.py`
- `tests/g5/test_end_to_end_smoke.py`
- `.superpowers/sdd/2026-08-22-g5-pilot-freeze/task-12-remediation-1-report.md`

## Design Decisions

- Task10 smoke behavior remains synthetic and bounded, but completed smoke
  checkpoints are now saved after the optimizer update and evaluation-state
  snapshot. Interrupted smoke checkpoints remain pre-update resume points.
- Development and validation factories share the frozen G2 road-cache path,
  accept only `10000-10019` and `20000-20049` respectively, reject sealed IDs,
  initialize every UAV with exactly `0.2875 L`, and expose pesticide-only
  provenance.
- Spray mortality is applied before rebuilding the returned role observations
  and critic state. Team reward is the immediate pest decrease divided by the
  episode's initial pest total; every role/agent receives that exact scalar.
- On-policy methods update at each frozen `rollout_horizon` and flush a final
  partial rollout. Off-policy methods update once per fresh frozen `batch_size`
  block; their replay is cleared after each block so checkpoints and memory do
  not accumulate 200,000 transitions. A final partial off-policy block is
  reported and excluded from the terminal checkpoint without inventing an
  update or interaction.
- Terminal validation checkpoints use `g5-training-checkpoint-v1`, are written
  after the final optimizer update, reload through the strict API, and must
  reproduce the trained evaluation-state digest. Pending rollouts and replay
  rows are zero, and the checkpoint is explicitly non-resumable.
- Task12 recovery accepts only `g5-physical-candidate-training-v1` summaries
  with physical mode, scenario proof, post-update digest equality, compact
  terminal-buffer fields, exact identity, and path confinement. Stopped
  synthetic summaries fail before checkpoint reuse.

## Verification

- Focused remediation integration:
  `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_physical_candidate_training.py tests/g5/test_validation_tuning.py tests/g5/test_end_to_end_smoke.py -q`
  returned `48 passed in 76.18s`.
- Existing protocol/checkpoint regression:
  `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q`
  returned `27 passed in 5.72s`.
- The focused compact test ran `257` real physical interactions, crossed from
  scenario `10000` to `10001`, performed four IQL updates, strictly reloaded
  the terminal checkpoint, found zero replay rows, and verified size below
  `100 MiB` (`1 passed in 12.16s`).
- Real `train_frozen_candidates` partition test trained all four IQL candidate
  identities for seed `51001` at 128 interactions under a temporary supplied
  root (`1 passed in 18.13s`).
- Full G5 run returned `366 passed, 4 failed in 142.84s`. All four failures are
  `tests/g5/test_experiment_matrix.py` clean-tree provenance tests raising
  `RuntimeError: source tree is dirty; frozen provenance cannot be generated`.
  This is expected while these tracked edits are intentionally uncommitted;
  changing that guard is outside the write scope, and committing is forbidden.
- `python -m compileall -q src scripts` and `git diff --check` exited `0`.
- Immutable SHA-256 values remain exact:
  candidate `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`,
  budget `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`,
  sealed lock `78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226`.

## Remaining Risks And Boundaries

- The four clean-tree experiment-matrix tests cannot pass under the simultaneous
  requirements to retain tracked edits and not commit. Focused acceptance and
  the required protocol/checkpoint suites pass.
- No canonical training or validation command was run. Existing untracked
  output directories were not listed, read, moved, deleted, recovered, or
  modified; all execution outputs used pytest temporary directories.
- The later selected-configuration development-refit adapter remains outside
  this remediation's candidate-training path and retains its existing Task10
  runner integration.
- No requirement in the focused remediation suite remains unsatisfied. The
  repository maturity remains M2; this work supplies implementation evidence,
  not validation efficacy, superiority, formal, sealed, or deployment evidence.

## Fix Round 1/5

This round closed independent-review findings C1 and I1-I6 within the
authorized Task12 scope. The I3 controller ruling authorized the preceding
physical-scenario contract correction. It freezes gamma shape `2.0`, gamma
scale `1.0`, normalized initial pest total `100.0`, and spray mortality
coefficient `5.0` with units. Each is a provisional simulation assumption;
empirical and deployment claims are explicitly false. The contract file hash
is registered by the strict G5 loader and deterministic scenario content hashes
are emitted in physical provenance.

Controller ruling: if the ecological assumptions are wrong or changed, all 60
candidates require retraining; validation remains untouched. The cost of an
incorrect assumption is therefore a complete 60-candidate retraining, while
the validation partition and access state remain unchanged.

### RED Evidence

Tests were added before the production corrections. Initial RED command:

```text
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_physical_candidate_training.py -x -q --tb=short
```

Exit `1`: `5 passed`, then the expected missing explicit test API failure:
`AttributeError: module 'problem2.training.physical_training' has no attribute
'run_noncanonical_physical_candidate_training_for_test'`.

Isolated RED slices also recorded: normalizer-only digest mutation `1 failed`
with identical digest `a46280...8591b`; direct wrapper partition/sealed/
unknown checks `4 failed` because construction did not raise; physical scenario
contract registration failed with missing `G5Contract.physical_scenario`;
canonical output confinement `2 failed` because training was reached; and the
wrong-budget guard `1 failed` because training was reached. The initial forced
mask fixture exposed a protocol-invalid action/mapping setup; it was corrected
to preserve the behavior-time mask and candidate-slot invariant.

### GREEN Verification

```text
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_physical_candidate_training.py tests/g5/test_validation_tuning.py tests/g5/test_end_to_end_smoke.py -q --tb=short
```

Exit `0`: `81 passed in 268.99s (0:04:28)`.

```text
.venv-g5\Scripts\python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q --tb=short
```

Exit `0`: `27 passed in 4.28s`.

The focused coverage includes all five method round trips, normalizer/mode/
exploration-sensitive evaluation digests, forced UAV/vehicle validity,
strict scenario parsing and deterministic content hashes, direct wrapper
guards, canonical alternate-CWD/root/budget/candidate no-write checks,
dirty-source rejection, complete `10019 -> 10000` cycling, exact completion
manifest/artifact/hash/byte/path/provenance checks, strict reload, finite-state
rejection, append-only quarantine, and explicit from-scratch rerun.

```text
.venv-g5\Scripts\python.exe -m compileall -q src scripts
```

Exit `0`.

```text
git diff --check
```

Exit `0`; only Git LF/CRLF normalization warnings were emitted.

Immutable SHA-256 verification returned:

```text
outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json  67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A
outputs/problem2_sr_mappo_v1/g5/manifests/pilot-budget.json          048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB
docs/evidence/g1/sealed_test_lock.yaml                              78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226
```

No canonical 200,000-interaction training, validation, refit, formal, or
sealed operation ran. No commit or push ran.

### Concerns

Canonical execution remains intentionally unverified and validation remains
unaccessed. The previously known full-G5 clean-tree provenance failures remain
outside this uncommitted round and were not rerun. Repository maturity remains
M2; no efficacy, superiority, formal, sealed, deployment, or empirical
ecological claim is authorized.
