# HANDOFF G5: TASK 5

Date: 2026-08-24
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g5-pilot-freeze`
Remote: `origin/codex/problem2-g5-pilot-freeze`
Task-4 persistence baseline: `dc8fbb09852370f6d99dee4aa34e4ed9f2d69bb4`

## Purpose

This is the context-free continuation record for the next conversation. The
only authorized work is **G5 Task 5: implement heterogeneous discrete MADDPG
and IQL** from
`docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`.

Do not redo Tasks 1-4. Do not start Task 6. Do not run a pilot, tune on
validation scenarios, access sealed scenarios, queue formal jobs, or make an
efficacy/superiority claim. Stop after Task 5 is implemented, reviewed,
verified, committed, pushed, and recorded in `docs/PROJECT_STATE.md`.

## Mandatory Startup

Read these files completely before editing:

1. `AGENTS.md`;
2. `docs/PROJECT_STATE.md`;
3. this handoff;
4. `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, especially Task 5;
5. `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md`;
6. the applicable local skills, including `using-superpowers`,
   `sr-mappo-problem2`, `executing-plans`, `test-driven-development`,
   `requesting-code-review`, and `verification-before-completion` when
   available.

Use PowerShell from the repository root and inspect state before changes:

```powershell
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote --heads origin codex/problem2-g5-pilot-freeze
git diff --check
```

The Task-4 persistence baseline above must be an ancestor of the current HEAD.
The current local, upstream, and remote branch heads must match before Task 5
starts. Do not reset back to the baseline because handoff/state commits follow
it. The only known unrelated working-tree item is the user-owned untracked
directory `_tmp_docx_assets/`; do not inspect, stage, modify, delete, or clean
it. Stop if there are other unexplained changes that overlap Task 5.

## Research Identity And Boundary

- Public flagship name: **SR-MAPPO**.
- Problem 2 is the air-ground heterogeneous extension of SR-MAPPO.
- Do not introduce HAPPO or rename the method to `AG-SR-MAPPO`.
- The replenished resource is pesticide only. Battery replenishment is
  inactive.
- OSM roads are simulation inputs, not evidence of real field deployment.
- Keep all future Problem-2 outputs below `outputs/problem2_sr_mappo_v1`.
- Do not modify the protected first-problem repository, base project/OSM
  inputs, planning evidence, external Word files, or other output roots.

The current highest maturity is `M2`: implementation and scoped mechanism
evidence. G5 remains open. No G5 pilot, validation tuning, formal job, or
sealed-test access has occurred; sealed unlock count is `0`.

Permitted wording is limited to implementation and test verification. It is
not permitted to claim that mobile support improves treatment, that SR-MAPPO
or another algorithm is superior, that formal experiments show a result, that
any result is statistically significant, or that simulation verifies a real
deployment.

## Completed G5 Work

- **Task 1:** reconciled G4 lineage to one accepted
  commit/tree/source-bundle tuple and recorded the audit.
- **Task 2:** froze strict G5 registries and contracts for methods,
  candidates, fairness, budgets, partitions, metrics, statistics, exclusions,
  dependency lock, and Problem-1 lineage. The isolated `.venv-g5` exists; the
  host dependency environment remains unchanged.
- **Task 3:** added `HeterogeneousAlgorithm`, behavior-bound `RoleBatch`,
  `JointReplayBuffer`, diagnostics, and atomic versioned checkpoint/resume
  support while preserving G3 checkpoint behavior.
- **Task 4:** implemented `sr_mappo_mobile`, same-source `mappo_mobile`, and
  role-local `ippo_mobile`, including all frozen `c01-c04` candidates,
  behavior-bound `OnPolicyEnvelope`, validity-aware GAE, frozen evaluation,
  transactional update failure handling, and exact resume.

Task-4 content commit:
`0593f17edad38a892115a375c1ac836cf8081e19`.
Task-4 persistence commit/baseline:
`dc8fbb09852370f6d99dee4aa34e4ed9f2d69bb4`.

Fresh Task-4 verification recorded before persistence:

- G5 suite: `165 passed`;
- G3 suite: `65 passed`;
- host full regression: `464 passed`;
- G5 contract audit: `status=pass`, validation/sealed access false, unlock
  count `0`;
- final independent review: `Ready`.

## Task 5 Exact Scope

Create only the planned algorithm files plus narrowly necessary shared
protocol/replay changes:

```text
src/problem2/algorithms/maddpg/__init__.py
src/problem2/algorithms/maddpg/algorithm.py
src/problem2/algorithms/maddpg/networks.py
src/problem2/algorithms/maddpg/trainer.py
src/problem2/algorithms/iql/__init__.py
src/problem2/algorithms/iql/algorithm.py
src/problem2/algorithms/iql/networks.py
src/problem2/algorithms/iql/trainer.py
tests/g5/test_off_policy_algorithms.py
```

Extend `src/problem2/algorithms/__init__.py` so `build_algorithm` constructs
`maddpg_mobile` and `iql_mobile` for every frozen `c01-c04` candidate. Modify
`src/problem2/algorithms/protocol.py`,
`src/problem2/algorithms/common/replay.py`, exports, and existing focused tests
only as required to establish a strict off-policy contract. Preserve all
accepted on-policy and G3 behavior.

Required MADDPG behavior:

- one shared UAV discrete actor and one separate vehicle discrete actor;
- centralized role-Q critics, matching target actors/critics, replay, and
  soft target updates;
- straight-through masked Gumbel-Softmax actor updates;
- `masked_straight_through_gumbel(logits, mask, temperature) -> Tensor` gives
  every illegal action exactly zero mass and exactly zero actor gradient;
- actor gradients reach only the selected role actor, with role optimizer and
  parameter isolation;
- deterministic evaluation uses masked actor argmax.

Required IQL behavior:

- one shared UAV Q/target-Q network and one separate vehicle Q/target-Q
  network;
- role-local masked epsilon-greedy behavior, replay, and frozen target updates;
- `masked_bootstrap_max(q, mask)` excludes illegal actions and rejects any
  all-false mask;
- role parameters, optimizers, targets, exploration state, and replay resume
  remain isolated and complete;
- deterministic evaluation uses masked greedy actions with epsilon exactly
  `0` and must not mutate exploration state.

Both algorithms must use the same behavior-bound role actions/masks, shared
team reward, identities, candidate-slot mapping, validity semantics,
interaction budget, local actor observations, and information conditions as
the accepted G5 contract. Checkpoints must contain every method-specific
network, target, optimizer, schedule/exploration counter, replay position,
replay RNG, trainer RNG, pending state, configuration, and diagnostics needed
for uninterrupted-versus-resumed next-update equivalence.

## Critical Integration Hazard

Resolve this contract issue with failing tests before production code:

- `HeterogeneousAlgorithm.observe` currently advertises only
  `OnPolicyEnvelope`;
- `JointReplayBuffer` currently stores only `RoleBatch`;
- `RoleBatch` lacks the current/next structured global state required by
  MADDPG centralized role-Q critics.

The conservative resolution is a strict typed `OffPolicyEnvelope` or a
reviewed general transition protocol. It must wrap the exact behavior-bound
`RoleBatch` and carry current/next structured state, shared team reward,
team/role validity, masks, role and agent identities, and vehicle candidate
mapping. It must validate and serialize through replay and checkpoints.

Widen the abstract `observe` surface without weakening `OnPolicyEnvelope`.
Existing on-policy algorithms must continue to reject raw `RoleBatch` and
off-policy envelopes. Off-policy algorithms must reject on-policy envelopes
and incomplete/raw transition data. Do not place critic-only structured state
in actor forward signatures.

Audit `JointReplayBuffer.load_state_dict` as part of this change. Require exact
keys and types, validate all contents before mutating live state, make
defensive copies, preserve ring slots/insertion index/size/RNG/masks, reject
impossible sparse layouts or malformed RNG state, and prove deterministic
sampling after resume. Do not weaken the accepted behavior-mask binding.

## Frozen Candidate Grid

The authoritative registry is
`configs/problem2/g5/tuning_candidates.yaml`. Do not tune or alter it.

MADDPG fixed values: hidden network `128 x 2`, replay capacity `100000`,
discount `0.99`, exploration `1.0 -> 0.05`.

| Candidate | Actor LR | Critic LR | Tau | Batch |
|---|---:|---:|---:|---:|
| `c01` | `1e-4` | `3e-4` | `0.005` | `64` |
| `c02` | `3e-4` | `3e-4` | `0.005` | `64` |
| `c03` | `1e-4` | `1e-3` | `0.010` | `128` |
| `c04` | `3e-4` | `1e-3` | `0.010` | `128` |

IQL fixed values: hidden network `128 x 2`, replay capacity `100000`, discount
`0.99`, epsilon `1.0 -> 0.05`.

| Candidate | Learning Rate | Target Interval | Epsilon Decay | Batch |
|---|---:|---:|---:|---:|
| `c01` | `1e-4` | `100` | `0.999` | `64` |
| `c02` | `3e-4` | `100` | `0.999` | `64` |
| `c03` | `3e-4` | `250` | `0.995` | `128` |
| `c04` | `5e-4` | `250` | `0.995` | `128` |

## Required Execution Order

1. Inspect the accepted protocol, replay, checkpoint, factory, registry, and
   on-policy rejection tests. Write down the exact off-policy envelope/replay
   state contract before implementation.
2. Write failing MADDPG tests for both roles, joint-action critic inputs,
   behavior masks, illegal-action zero mass/gradient, role gradient isolation,
   target updates, replay/checkpoint round trip, resume equivalence, and
   deterministic evaluation.
3. Write failing IQL tests for both roles, masked epsilon-greedy behavior,
   all-false rejection, illegal bootstrap exclusion, role isolation, target
   updates, replay/checkpoint round trip, resume equivalence, and epsilon-zero
   evaluation.
4. Run the focused suite and record the expected RED caused by missing
   modules/interfaces.
5. Implement the minimum strict shared off-policy contract, MADDPG, IQL, and
   factory extensions. Keep configuration immutable and fail closed on
   malformed/non-finite state, loss, gradient, or checkpoint input.
6. Run focused regression while implementing, then request an independent
   code review. Fix every Critical/Important finding with a reproducing test
   and repeat review until no such finding remains.
7. Run the complete verification below on final content. Inspect the diff,
   forbidden names, partition access, and working tree manually.
8. Commit with the exact subject
   `feat: implement heterogeneous maddpg and iql`, push it, and verify local,
   upstream, and remote parity.
9. Update `docs/PROJECT_STATE.md` with scope, TDD evidence, review result,
   verification counts, content commit, remote parity, maturity boundary,
   access statement, and the next authorized task. Commit and push that
   persistence record separately, then verify parity again.

## Required Verification

Use `.venv-g5` for the exact G5 lock and host Python for the full legacy
regression:

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5/test_off_policy_algorithms.py -q
.venv-g5/Scripts/python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q
.venv-g5/Scripts/python.exe -m pytest tests/g3 -q
.venv-g5/Scripts/python.exe -m pytest tests/g5 -q
python -m pytest -q
.venv-g5/Scripts/python.exe -m compileall -q src scripts
.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py
git diff --check
```

Also run targeted leakage/identity checks such as:

```powershell
rg -n "HAPPO|AG-SR-MAPPO|30000|30099|validation|sealed" src/problem2/algorithms tests/g5/test_off_policy_algorithms.py
git status --short --branch
git diff --stat
git diff -- src/problem2/algorithms tests/g5/test_off_policy_algorithms.py
```

Literal forbidden-name and partition strings may appear only in explicit
fail-closed tests/audits, never as a new method or accessed scenario. Report
actual command output; do not copy the old pass counts as fresh evidence.

## Stop Conditions

Stop Task 5 and record the blocker without advancing the gate if any of these
occurs:

- local/upstream/remote history differs unexpectedly;
- unexplained user changes overlap Task 5;
- the strict off-policy transition cannot carry centralized critic state
  without weakening actor isolation or on-policy rejection;
- illegal MADDPG actions receive nonzero mass or gradient;
- IQL bootstraps from an illegal action or accepts an all-false mask;
- replay/checkpoint restoration is partial, mutates before validation, or does
  not reproduce deterministic sampling/next update;
- any focused, G3, G5, full-regression, compile, contract, or diff check fails;
- implementation would require Task 6 environment/controller work, a pilot,
  validation data, sealed data, a protected external write, or a registry
  change not explicitly authorized by the plan.

Task 5 completion does not pass G5 or raise maturity above `M2`. After a clean
Task-5 content and persistence push, Task 6 becomes the next candidate work,
but do not begin it in the same task without new user authorization.

## Required Final Report

Report the exact Task-5 result, changed files, RED/GREEN/review evidence,
verification counts, content commit, persistence commit, local/upstream/remote
parity, highest maturity, validation/sealed access state, protected paths left
untouched, blockers, and the next authorized task. Never claim more evidence
than the recorded gate supports.
