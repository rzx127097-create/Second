# HANDOFF: G5 Task 11 Complete -> G5 Task 12

Date: 2026-08-27

Repository: `C:/Users/RZX/Documents/ChatGPT/Second`

Branch: `codex/problem2-g5-pilot-freeze`

Task11 final persistence commit before this handoff:
`3136a3bbf6478f3c3af30ff93411c2266ea92173`

Task11 pilot evidence content commit:
`34f0941ca1d4d167c65e234e8313f421b05f3eaa`

Task11 pilot generation/source commit:
`33ba716aacedeff4e90a6d6f604f103732a970fd`

Highest accepted maturity: `M2` implementation and scoped mechanism evidence

Current gate: G5 Tasks 1-11 accepted; Task12 is next

Validation status: not yet accessed

Sealed-test status: locked, maximum unlock count `1`, actual unlock count `0`

## 0. Read This First

This document is written for a new conversation with no prior context. The
project is building the second thesis problem: road-constrained heterogeneous
air-ground cooperative pesticide spraying with multiple UAVs and one mobile
pesticide replenishment vehicle. The public flagship method name is
**SR-MAPPO**. Problem 2 is an air-ground heterogeneous extension of SR-MAPPO.

The work completed in the previous conversation was **G5 Task11**, not a
formal experiment. Task11 ran and froze a development-only pilot system,
selected a runtime budget, and created an immutable set of validation
candidates. The only authorized next work is **G5 Task12: equal-budget
validation tuning, selected-configuration development refit, and final G5
freeze of the G6/G7 manifests**.

Do not redo Task11. Do not start G6 formal training. Do not unlock or read
sealed-test scenarios. Do not generate thesis efficacy or superiority claims.

`docs/PROJECT_STATE.md` is authoritative for dynamic state. This handoff is a
continuation guide and must not override a later persisted project-state
record.

## 1. Mandatory Startup For The New Conversation

Read these files completely before editing or running validation:

1. `AGENTS.md`;
2. `docs/PROJECT_STATE.md`;
3. `HANDOFF_TASK12.md`;
4. `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, especially Task12
   at lines around 441-496;
5. `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md`, especially
   the pilot/validation sequence and statistical freeze;
6. `docs/audits/g5-task11-pilot-freeze-implementation.md`;
7. `outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json`;
8. `outputs/problem2_sr_mappo_v1/g5/manifests/pilot-budget.json`;
9. `docs/evidence/g5/checkpoint_selection.yaml`;
10. `docs/evidence/g1/sealed_test_lock.yaml`.

Use the applicable local skills before acting, especially
`using-superpowers`, `sr-mappo-problem2`, `test-driven-development`,
`systematic-debugging`, `requesting-code-review`, and
`verification-before-completion`.

Run the following read-only checks first:

```powershell
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze
git log -5 --oneline --decorate
git diff --check
```

Local HEAD, upstream HEAD, and `git ls-remote` must agree before Task12 begins.
The handoff and its persistence record advance the HEAD beyond the Task11 hash
shown above, so discover the actual current hash instead of assuming
`3136a3b` is still HEAD.

## 2. Non-Negotiable Research Identity And Boundaries

- Use the public name `SR-MAPPO` everywhere.
- Describe Problem 2 as an air-ground heterogeneous extension of SR-MAPPO.
- Do not introduce HAPPO as an implementation or baseline.
- Do not rename the method to `AG-SR-MAPPO` or another public algorithm name.
- Pesticide is the only replenished resource.
- Battery replenishment remains inactive unless a separate activation audit
  is authorized, passed, and persisted.
- OSM/GraphML is a read-only road-constrained simulation input, not evidence of
  real field deployment.
- Training reward is diagnostic only. Thesis conclusions require paired,
  fixed-scenario evaluation from the locked evidence pipeline.
- At M2, permitted wording is limited to implementation, interface, invariant,
  smoke, and development-pilot verification.
- Do not claim that mobile support improves treatment, that SR-MAPPO is best,
  that results are statistically significant, or that real deployment was
  verified.

Protected external assets must not be changed:

- `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`;
- `D:/Pycharm/Locust_rl` and its OSM inputs;
- `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析`;
- all existing Word thesis files outside this repository.

All Problem-2 outputs belong below `outputs/problem2_sr_mappo_v1`. Do not
write into Problem-1 output roots.

## 3. What Has Been Completed

### G0-G1

- The authoritative repository, branch policy, protected assets, output root,
  evidence registries, seed partitions, parameters, literature registry,
  artifact schemas, and sealed lock were established.
- Training, development, validation, formal, and sealed identities are
  separated and fail closed.

### G2

- Offline road topology, metric projection, physical-scale movement,
  request/reservation/service state machine, pesticide transfer, resource
  conservation, deterministic replay, and road-cache provenance passed.

### G3

- Heterogeneous UAV and vehicle role actors, centralized critic contract,
  exact behavior masks, GAE, normalization, checkpoint round trip, resume,
  and deterministic evaluation were accepted at M2.

### G4

- Onboard UAV pesticide scarcity and diagnostic mobile/fixed support probes
  were activated and audited.
- This is diagnostic mechanism evidence only. It is not learned-policy
  efficacy evidence and does not establish vehicle-inventory scarcity.

### G5 Tasks 1-10

- G4 lineage was reconciled.
- Method, candidate, fairness, metric, statistics, exclusion, budget,
  checkpoint, partition, and dependency contracts were frozen.
- The shared heterogeneous protocol and atomic checkpoint/resume path were
  implemented.
- Five learning methods were implemented:
  `sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`, `maddpg_mobile`, and
  `iql_mobile`.
- The physical G2-to-G3 adapter, direct episode metrics, fixed support,
  rolling A*, nearest, urgency, and two-stage controllers were implemented.
- The experiment graph, orchestration, evidence validation, and paired
  statistics/mechanism adapters were implemented and tested.
- Task10 development smoke passed for all 5 methods x 17 condition types on
  CPU (`85/85`) and one CUDA job per method (`5/5`).

### G5 Task11

Task11 executed the complete development-only pilot matrix:

```text
2 scales x 5 methods x 17 conditions x 3 training seeds = 510 jobs
510 jobs x 20 development scenario references = 10,200 records
```

Frozen identities:

- scales: `g20x20_d2`, `g30x50_d4`;
- development training seeds: `51001`, `51002`, `51003`;
- development scenarios: `10000-10019`;
- all five registered learning methods;
- all 17 registered condition types.

Task11 final results:

- pilot status: `pass`;
- training jobs: `510`;
- episode/scenario-reference records: `10,200`;
- failures: `0`;
- every job contains checkpoint, manifest, summary, and training log;
- selected budget: `200000` environment interactions;
- checkpoint interval: `10000`;
- checkpoint count: `20`;
- projected slowest runtime: `0.7708476562500424` hours;
- frozen validation candidates: `20`, exactly four per learning method;
- validation panel: IDs `20000-20049`, count `50`, content excluded;
- validation scenario panel hash:
  `7bba8dd6f37272c0d8e333ec3308d13fc2d89a1595093a8ac74c47757ff2a3b4`;
- all records have `validation_accessed=false`, `sealed_accessed=false`, and
  `battery_replenishment_enabled=false`.

The 10,200 records are explicitly `development_pilot_descriptive` scenario
references with `scenario_execution=false`. Do not relabel them as 10,200
independent experiments or as validation/formal outcomes.

## 4. Task11 Evidence Inventory

Canonical root:

`outputs/problem2_sr_mappo_v1/g5`

Core artifacts and SHA-256:

- `validated/pilot-episodes.jsonl`:
  `7609183B3B8945BC019F63F361C5FEBE7D00E9E7E4E8042BB07530A9C013DE72`;
- `audits/pilot-audit.json`:
  `4A14FE3B3518ECD0E864DDD79FADFCE7311E829BB1E505E76925AE162EF58CF2`;
- `audits/pilot-artifact-manifest.json`:
  `1B757397A28240C567CBADC5AD56B64C533E316558CE2924935C4D33B1ACC61E`;
- `manifests/pilot-budget.json`:
  `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`;
- `manifests/validation-candidates.json`:
  `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`.

Relevant directories:

- `outputs/problem2_sr_mappo_v1/g5/pilots/`;
- `outputs/problem2_sr_mappo_v1/g5/smoke/`;
- `outputs/problem2_sr_mappo_v1/g5/validated/`;
- `outputs/problem2_sr_mappo_v1/g5/manifests/`;
- `outputs/problem2_sr_mappo_v1/g5/audits/`.

Recorded verification:

- `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`:
  `402 passed`;
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed`;
- Task11 focused pilot/smoke suite: `32 passed`;
- CPU smoke: `85/85`, status `pass`;
- CUDA smoke: `5/5`, status `pass`;
- G5 contract audit: `status=pass`, validation/sealed false,
  `actual_unlock_count=0`;
- compileall and diff checks passed.

## 5. Current Git And Working-Tree State

The Task11 evidence and persistence commits were pushed without force-push.
At Task11 closure, local, upstream, and remote all matched
`3136a3bbf6478f3c3af30ff93411c2266ea92173`.

The tracked worktree was clean. The following untracked directories existed
locally and were deliberately not committed:

```text
_tmp_docx_assets/
outputs/problem2_sr_mappo_v1/g5/_debug/
tmp-bench-cpu/
tmp-bench-cuda/
tmp-bench-loop/
tmp-bench-opt/
tmp-bench-opt128/
tmp-full2/
tmp-pilot-bench/
tmp-res2/
tmp-smoke-review-fix-resume/
tmp-smoke-review/
tmp-smoke/
tmp-task11-cli/
```

Treat these as out of scope. Do not inspect or modify `_tmp_docx_assets/`.
Do not run `git clean`, do not delete these folders, and never use
`git add -A` or `git add .`. Stage explicit Task12 paths only.

## 6. Exact Next Task: G5 Task12

Authoritative plan section:
`docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, Task12.

Task12 must create or generate exactly these planned artifacts, with only
narrowly justified supporting changes:

```text
src/problem2/training/tuning.py
src/problem2/training/selection.py
tests/g5/test_validation_tuning.py
scripts/run_g5_validation_tuning.py
scripts/freeze_g5.py
outputs/problem2_sr_mappo_v1/g5/validation/**
outputs/problem2_sr_mappo_v1/g5/validated/validation-episodes.jsonl
outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json
outputs/problem2_sr_mappo_v1/g5/manifests/g6-validation-evaluations.json
outputs/problem2_sr_mappo_v1/g5/manifests/g7-sealed-evaluations.json
outputs/problem2_sr_mappo_v1/g5/manifests/g7-analysis.json
outputs/problem2_sr_mappo_v1/g5/freeze-manifest.json
outputs/problem2_sr_mappo_v1/g5/audits/negative-result-diagnosis.json
docs/audits/g5-pilot-freeze-compliance.md
HANDOFFG5.md
docs/PROJECT_STATE.md
```

The four G6/G7 JSON manifests already exist from Task7 as unexecuted skeleton
artifacts. Their presence is not Task12 completion. Task12 must regenerate or
finalize and audit them under the selected configurations and final freeze
contract. Do not treat the existing files as executed formal or sealed
evidence. `HANDOFFG5.md` is also a historical handoff until Task12 updates it.

Task12 required behavior:

1. Write failing tests first for candidate immutability after first validation
   access, equal budgets, selection tie-breaks, exact G6/G7 counts, missing
   hash rejection, and zero sealed access.
2. Implement validation-only tuning and selected-configuration recording.
3. Evaluate only the 20 pre-hashed candidates on validation IDs
   `20000-20049` with equal environment interactions.
4. Mechanically select one configuration per learning method by the frozen
   order: mean validation reduction rate, then higher success probability,
   then lower interaction count, then lexicographically smaller config hash.
5. Preserve every candidate result, including unfavorable and failed results.
6. Disable candidate generation or edits after the first validation row.
7. Rerun the selected configurations on the same complete development pilot
   matrix before the final freeze.
8. Validate the refit evidence chain and retain raw artifacts.
9. Generate and audit G6/G7 manifests without reading sealed scenario content.
10. Require exactly `150` base and `375` total unique G6 training jobs.
11. Require exactly `42,500` expected G7 sealed evaluation identities, but no
    sealed scenario content and no evaluation result.
12. Generate the negative-result diagnosis rather than suppressing weak or
    unfavorable findings.
13. `freeze_g5` must verify source cleanliness, local/upstream/remote parity,
    contract and artifact hashes, full matrix coverage, statistics contract,
    sealed lock `maximum=1/actual=0`, and protected-asset preservation.
14. Stop at the first failed gate. G6 remains unauthorized unless every G5
    freeze acceptance item passes and is persisted.

Task12 consumes validation data, so this is a one-way governance transition.
Before the first validation row, confirm the candidate and budget hashes one
last time. After the first row, never edit, regenerate, reorder, or replace a
candidate based on observed outcomes.

## 7. Task12 Verification And Persistence Contract

The plan proposes these checks, but inspect current CLI help before executing
them because one command signature is stale (see Pitfall 4 below):

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5 -q
.venv-g5/Scripts/python.exe -m pytest -q
.venv-g5/Scripts/python.exe -m compileall -q src scripts
.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py
.venv-g5/Scripts/python.exe scripts/freeze_g5.py --check-only
git diff --check
```

Also run host-Python G2/G4 regression where required by the accepted
cross-process G2 environment. Do not silently replace fresh counts with old
counts from this handoff.

Task12 content commit subject required by the plan:

```text
feat: freeze g5 fair-pilot experiment system
```

After pushing the content commit:

1. rerun final verification on that exact content commit;
2. update `docs/PROJECT_STATE.md` with content hash, verification, access
   status, maturity, and first failed gate if any;
3. commit with `docs: record g5 freeze persistence`;
4. push normally, never force-push;
5. verify local HEAD, upstream HEAD, and `git ls-remote` are identical.

Only then may G5 be marked passed and G6 become the next authorized gate.

## 8. Pitfalls Encountered: Do Not Repeat Them

### Pitfall 1: Post-Persistence Pilot Verifier Compares Against Current HEAD

`src/problem2/training/pilot.py::verify_pilot_artifacts` currently requires
the manifest `source_commit` to equal the repository's current HEAD.

This passed when Task11 evidence was generated at `33ba716...`, but after the
evidence and documentation were correctly committed, current HEAD advanced.
A direct verifier call at the Task11 persistence HEAD therefore raises:

```text
ValueError: pilot artifact manifest source commit mismatch
```

This is a verifier lineage-semantics defect, not evidence that the pilot files
were corrupted. Fresh checks established that:

- `33ba716...` is an ancestor of the persisted HEAD;
- `src`, `scripts`, `configs`, `docs/evidence`, `requirements-g3.lock`, and
  `requirements-g5.lock` are unchanged from `33ba716...` to the Task11
  persistence HEAD;
- the recorded artifact SHA-256 values still match;
- pilot audit and nested job provenance all bind consistently to
  `33ba716...`.

Do **not** rewrite the artifact `source_commit` to the current HEAD. No pilot
was generated at that later commit, so doing so would falsify provenance.

Before Task12 relies on the final `freeze_g5 --check-only` lineage audit, add a
failing regression test and repair the verifier contract. The conservative
direction is to validate that the recorded generation commit is valid and
reachable/ancestral and that the explicitly frozen source/protocol scope or
source-bundle hashes have not drifted. Preserve exact artifact hashes and the
original generation commit. Use TDD and independent review for this change.

### Pitfall 2: Full Matrix Tests Fail On Any Tracked Dirty File

`src/problem2/experiments/matrix.py::_git_commit` rejects a dirty tracked tree.
Four experiment-matrix tests failed only because `docs/PROJECT_STATE.md` was
modified but not yet committed. Once the documentation commit was made, the
same matrix suite passed `8/8`, and the full G3/G5 suite passed `402/402`.

Do not weaken this clean-tree guard just to make tests pass. Structure Task12
verification around clean commits. When a failure says
`source tree is dirty; frozen provenance cannot be generated`, inspect
`git status --porcelain --untracked-files=no` before changing code.

### Pitfall 3: Windows Checkpoint Rename Can Fail Transiently

One 85-job CPU smoke refresh failed at job 45 with a Windows
`PermissionError` during checkpoint temporary-file rename. The entire CPU
smoke was rerun; the final canonical audit is `pass/85`.

Never combine a partial failed run with old jobs and call it complete. Preserve
the failure, determine whether the target is locked, and rerun the required
identity or complete matrix under the frozen retry semantics. Do not change
hyperparameters or output identities to work around an OS file lock.

### Pitfall 4: The Plan's Artifact-Validator CLI Is Stale

The Task12 plan shows:

```text
scripts/validate_g5_artifacts.py --output-root ...
```

The current script instead exposes `--root` and is still described as a
dry-run-only guard; the accepted Task11 usage passed `--dry-run`. Do not
blindly paste the stale plan command and do not mistake the current dry-run
message for a full artifact validation. Task12 must reconcile the intended
acceptance check with the actual CLI, add tests, and document the final
executable command.

### Pitfall 5: Pilot Job Files Are Nested Two Levels Deep

Each outer pilot identity directory contains one inner runner directory, and
the four job artifacts live in that inner directory. A scan that checks only
the outer folder falsely reports all 510 jobs missing files. Traverse the inner
job directory or follow paths from the audit/manifest.

### Pitfall 6: Large Git Operations May Outlive The Tool Wait Window

The Task11 evidence commit staged 2,304 files. The commit command returned no
text within one wait window but had actually succeeded. Always inspect
`git log -1`, `git status`, and the index before retrying a commit or push.
Never create duplicate commits because a UI/tool wait timed out.

### Pitfall 7: Do Not Stage Temporary Or Protected Files

Task11 used explicit `git add -- <paths>`. Continue this pattern. Never stage
the untracked directories listed above, `_debug`, external repositories, Word
files, or OSM sources. Never run `git clean` or force-push.

### Pitfall 8: Use The Correct Python Environment

- Use `.venv-g5/Scripts/python.exe` for the frozen G5 environment and CUDA
  checks (`torch 2.13.0+cu126`).
- Host Python remains intentionally CPU-only and is required for some legacy
  G2/G4 cross-process regressions.
- Do not mutate the host environment to make G5 tests convenient.

### Pitfall 9: Line-Ending Warnings Are Not Test Failures

Git may warn that LF will be replaced by CRLF on Windows. Do not mass-reformat
JSON/JSONL or Markdown to silence this. Treat `git diff --check` exit status,
artifact byte hashes, and manifest hashes as authoritative.

### Pitfall 10: Validation And Sealed IDs Are Not Interchangeable

- Development: `10000-10019`;
- validation: `20000-20049`;
- sealed test: `30000-30099`.

Task12 may access validation only through its frozen protocol. It must not
read sealed content. The G7 manifests may contain sealed identities/hashes and
expected counts only. `actual_unlock_count` must remain `0` throughout G5.

## 9. Work That Has Not Been Done

- Task12 code has not been implemented.
- Validation candidates have not been evaluated.
- `validation_accessed` is still false at this handoff.
- Selected configurations have not been refit on the development matrix.
- The final G5 freeze manifest and compliance audit do not exist yet.
- G6 formal training has not started.
- G7 sealed test has not been unlocked or evaluated.
- No formal Problem-2 paired statistical conclusions exist.
- No locked figures, tables, or thesis efficacy/superiority prose exist.
- Engineering source records still need independent manuals, field studies,
  or expert confirmation where `docs/PROJECT_STATE.md` marks them pending.

## 10. Stop Conditions For Task12

Stop, record the first blocker, and keep G6 unauthorized if any of the
following occurs:

- local/upstream/remote history differs unexpectedly;
- unexplained user changes overlap Task12;
- the immutable candidate or pilot-budget hash differs before validation;
- a candidate is missing, duplicated, edited, or unequally budgeted;
- any candidate/result is removed because it is unfavorable;
- validation content is read before the final pre-access freeze checks;
- sealed scenario content or results are read;
- sealed unlock count changes from `0`;
- exact G6/G7 identity counts do not match `150` base, `375` unique training,
  and `42,500` sealed evaluation identities;
- source/artifact/checkpoint/statistics hashes do not close;
- protected external assets are modified;
- focused, regression, compile, contract, artifact, freeze, or diff checks
  fail;
- the work would require changing the scientific question, candidate grid,
  primary statistics, or frozen fairness protocol after seeing validation
  results.

## 11. Definition Of Task12 Completion

Task12 is complete only when all of the following are true:

- validation tuning consumed only the 20 frozen candidates at equal budget;
- every validation result, including failures/negative outcomes, is retained;
- selection used the exact pre-registered tie-break chain;
- selected configurations were refit on the full development pilot matrix;
- the validation long table and evidence audit pass;
- G6/G7 manifests have exact counts, hashes, dependencies, and no sealed
  content/result leakage;
- `freeze_g5 --check-only` passes on a clean source tree with correct lineage;
- G5 compliance and negative-result reports are persisted;
- all required fresh tests pass;
- the content commit is pushed;
- `docs/PROJECT_STATE.md` records the pushed content hash and verification;
- the separate persistence commit is pushed;
- local, upstream, and remote heads match;
- the highest maturity and permitted claims are stated conservatively.

Only after that may the project state authorize G6. G7 sealed evaluation and
G8 thesis artifact generation remain later gates.

## 12. Suggested First Message In The New Conversation

Use this as the new request after opening the repository:

> Read `AGENTS.md`, `docs/PROJECT_STATE.md`, and `HANDOFF_TASK12.md` completely.
> Continue only the next authorized G5 Task12. First audit local/upstream/remote
> parity, the immutable candidate/budget hashes, the sealed lock, and the known
> post-persistence pilot-verifier lineage defect. Use TDD, preserve all
> validation results, do not access sealed content, stop at the first failed
> gate, and persist the content and state-record commits to GitHub before
> claiming G5 complete.
