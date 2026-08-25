# Project State

Last updated: 2026-08-20

## Final Goal

Build a reproducible and auditable thesis-level package for the second research
problem: road-constrained air-ground heterogeneous cooperative pesticide
spraying with a mobile pesticide replenishment vehicle, using SR-MAPPO as the
flagship algorithm.

The final package must cover problem modeling, parameter registration,
environment modeling, heterogeneous SR-MAPPO implementation, fair baselines,
experiment freezing, batch training, sealed evaluation, statistics, figures,
tables, and thesis chapter prose. It must not represent simulation results as
real deployment evidence.

## Current State

- Authoritative repository for future work:
  `C:/Users/RZX/Documents/ChatGPT/Second`.
- GitHub remote: `https://github.com/rzx127097-create/Second.git`.
- Current branch: `codex/problem2-g0-orchestration`.
- Current branch base at start of G0:
  `2643753855c385253951dfad2c225be0b09b7e00`
  (`origin/main`, commit message `docs: mark section 4.2 delivery complete`).
- Existing remote feature branch:
  `origin/feature/problem2-code-framework` at
  `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`.
- Current highest maturity: `M1` design/specification evidence.
- Current gate: bounded `G1.1` remediation passed TDD, independent full-range
  review, fresh controller verification, and GitHub persistence. Content and
  evidence are at `1b10457`; the acceptance record is at `9ece829`. `G2`
  deterministic-model specification and validation are the next authorized
  work; no G2 implementation has started.
- Sealed-test status: locked; maximum unlock count is `1`, actual unlock count
  is `0`, and no sealed-test result may be used for tuning.
- Main resource: pesticide-only replenishment.
- Battery replenishment: inactive until a separate activation audit passes.
- Frozen second-problem output root: `outputs/problem2_sr_mappo_v1`.

The repository already contains chapter 4.1/4.2 design, figure, document, and
artifact-ledger assets on `origin/main`. The remote branch
`origin/feature/problem2-code-framework` contains extensive problem-2 code,
configuration, test, verification, and planning assets. G1 audited those Git
objects read-only; they remain candidate inputs and are not integrated or
accepted as current M2/M3/M4 evidence.

## Source Documents And Inputs

### Planning Documents

| Path | SHA-256 | Status |
|---|---|---|
| `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析/第二个问题_14项能力强化与验收矩阵.md` | `BE74DCC04B9C216CC67FB942798A72DCEF0EBEFAF4A99D1151F2438E823450DA` | Read-only planning evidence |
| `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析/第二个问题_代码实验与论文一体化实施总纲.md` | `DA6F51A9B644A1FF34C9F99E6F8687F03F7B070C56DA02EB4322178AA3E4BA87` | Read-only planning evidence |
| `D:/Pycharm/Locust_rl/CODEX_TASK_problem2.md` | `FCC6026F2FFCE23C98EDA5DE9A87EFC5C0A0C4BD8113D9878594A14ABECFC813` | Historical implementation brief |
| `D:/Pycharm/Locust_rl/CODEX_TASK_problem2_v2.md` | `6DA25B14752069D1700344FCE732EEE8B0D867FDE8F79892308448FF4A51E4A4` | Historical implementation brief |

The historical `CODEX_TASK_problem2*.md` files are useful implementation
references but do not override the current final goal. In particular, their
small-scale-only boundary and any instruction to reuse first-problem fixed
station results conflict with the current requirement for a full second-problem
evidence chain and same-environment reruns.

### OSM And Base Project Inputs

| Path | SHA-256 | Status |
|---|---|---|
| `D:/Pycharm/Locust_rl/data/jodhpur_drive.graphml` | `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462` | Read-only road input |
| `D:/Pycharm/Locust_rl/data/jodhpur_buildings.geojson` | `08A81DF6C8FA401014ACD161661072714D9231B2B95173CBE932C86FE57F37DB` | Read-only context input |
| `D:/Pycharm/Locust_rl/data/jodhpur_green.geojson` | `B80F54C7C03EE42B4F8E8A55BFBCFBD4B7A166ED5E3EB97CD443069398CE0647` | Read-only context input |

`D:/Pycharm/Locust_rl` is not a Git repository. Any future use of that code or
data must be linked to a reproducible source-tree hash, a copied controlled
source snapshot in this repository, or an explicitly audited branch in this
repository.

## Protected First-Problem Assets

First-problem repository:
`C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`

- Git remote: `https://github.com/rzx127097-create/locust-rl-paper.git`.
- HEAD at G0 inventory:
  `1ca9e5ccc5f77ed775cd2b607dd70d635720accf`.
- Branch at inventory: `main`.
- Dirty state at inventory: user changes present; do not revert or overwrite.

Protected dirty files:

- `scripts/run_sr_mappo_sensitivity.py`
- `source/locust_rl_selected/config/settings.py`
- `source/locust_rl_selected/evaluation/ablation_convergence.py`
- `source/locust_rl_selected/evaluation/ablation_integrity.py`
- `source/locust_rl_selected/main.py`
- `source/locust_rl_selected/rewards/calculator.py`
- `source/locust_rl_selected/tests/test_sr_mappo_sensitivity.py`
- `source/locust_rl_selected/training/trainer.py`
- `KNOWLEDGE.md`
- `scripts/analyze_sr_mappo_reward_sensitivity.py`
- `scripts/build_reward_sensitivity_deliverables.py`
- `scripts/insert_reward_sensitivity_into_small_paper.py`
- `scripts/run_sr_mappo_reward_sensitivity.py`

These files appear to relate to first-problem SR-MAPPO reward sensitivity and
must not be mixed with second-problem implementation work.

### Protected Word Assets

The following existing Word files are read-only inputs or historical deliverables
for the first problem. They must not be edited by second-problem workers:

| Path | SHA-256 | Length |
|---|---|---:|
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/方向.docx` | `DD614ABF8D221B79CE379D6830B0DD9DD384ED53A449F512ECE424CCDB833A89` | 19,665 |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/无人机蝗灾.docx` | `363284C6D7DD4F0D46A95E1F45AD723E2C2B1780BCD87C1C50DB428FFD30D127` | 1,971,885 |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/消融.docx` | `EC0A620D6AB5CB6E2055C4C1D3A90344FAE6B67474B33BBC46B97879E8F9F43A` | 297,169 |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/knowledge/archive/旧第4章-RL算法比较主线/deliverable/第4章-实验结果与分析.docx` | `3BC9D2C74E5C525EFE412429989709AE7A5DC4B3B20A05236691001ED23BC397` | 5,029,276 |

### Protected Experiment And Figure Roots

These roots remain outside the `Second` repository and are protected from
second-problem writes:

| Path | Inventory at G0 |
|---|---:|
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/outputs/sr_mappo_paper_v1` | 1,012 files; 193,200,108 bytes |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/Table` | 78 files; 352,914 bytes |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/picture` | 135 files; 54,970,056 bytes |
| `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper/source/locust_rl_selected/logs` | 0 files at inventory |

The first-problem repository's dirty state and these protected roots are
historical/context evidence only. They cannot be used as second-problem formal
results without an explicitly frozen same-environment rerun.

## GitHub Persistence Contract

For every important phase `G0` through `G8`, the controller must:

1. write the phase outputs into this repository;
2. run and record fresh verification;
3. create a non-rewriting Git commit;
4. push the working branch to `origin`;
5. record the pushed commit hash, verification command, and result here before
   moving to the next phase.

G0 persistence record:

- Content commit: `7731d37`
  (`chore: register problem2 orchestration state`).
- Branch pushed: `origin/codex/problem2-g0-orchestration`.
- Verification: `python -m pytest tests\test_section_4_2_artifacts.py -q`
  returned `7 passed`; required-field scan returned `PASS`; `git diff --check`
  returned no errors; `.gitignore` matched both generated Python cache files.
- Persistence-record commit: `9fdd560`
  (`docs: record g0 verification and push`), pushed to the same branch.

Original G1 persistence record (historical; reopened by independent review):

- Local implementation commits: `03f56e9`, `e63a85b`, `b0bfbad`, `d93fd1f`,
  and `267e715`.
- Registry paths:
  `docs/evidence/g1/parameter_registry.yaml`,
  `docs/evidence/g1/literature_source_ledger.yaml`,
  `docs/evidence/g1/experiment_matrix.yaml`,
  `docs/evidence/g1/scenario_seed_manifest.yaml`,
  `docs/evidence/g1/job_identity_contract.yaml`,
  `docs/evidence/g1/raw_episode_schema.yaml`,
  `docs/evidence/g1/validated_long_table_schema.yaml`,
  `docs/evidence/g1/artifact_manifest_schema.yaml`,
  `docs/evidence/g1/sealed_test_lock.yaml`,
  `docs/evidence/g1/output_root_contract.yaml`.
- Registry validator:
  `python scripts/audit_g1_registries.py --root docs/evidence/g1 --report outputs/problem2_sr_mappo_v1/g1/registry-audit.json`
  returned `status=pass`, `10` files checked, and `0` errors.
- Candidate audit:
  `python scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown docs/audits/g1-feature-branch-audit.md --json outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json`
  returned `status=pass`, base `2643753855c385253951dfad2c225be0b09b7e00`,
  candidate `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`, and `210` changed paths.
- Focused verification:
  `python -m pytest tests/test_g1_registries.py tests/test_g1_feature_branch_audit.py -q`
  returned `16 passed`.
- G0 regression verification:
  `python -m pytest tests/test_section_4_2_artifacts.py -q`
  returned `7 passed`.
- `git diff --check` returned no errors; the protected first-problem
  repository remained at HEAD `1ca9e5ccc5f77ed775cd2b607dd70d635720accf` with
  its pre-existing dirty files unchanged.
- G1 status: verification passed locally; pushed commit hash is recorded in
  the follow-up persistence commit after the required push.
- Persistence candidate commit: `03fa12329f75db9e2a06dae1e01b7242ebedadf6`
  (`docs: record g1 evidence registration and audit`), pushed to
  `origin/codex/problem2-g0-orchestration`.
- Pushed-hash verification: `git rev-parse HEAD` and
  `git ls-remote origin refs/heads/codex/problem2-g0-orchestration` both
  returned `03fa12329f75db9e2a06dae1e01b7242ebedadf6`.
- Persistence-record commit: `92da39d2a769ce7d164f9996de28a97fcdf095a0`
  (`docs: persist g1 pushed hash`), pushed to
  `origin/codex/problem2-g0-orchestration`; local and remote hashes matched
  after the push.

G1 final-review remediation record:

- Independent final review reopened G1 after finding fail-open registry
  validation, incomplete canonical metric/raw/validated schemas, incomplete
  fairness declarations, and incomplete candidate-branch provenance and path
  handling.
- Fix base: `31795ca39d8412b0e22949207bdce2aeef2e57b1`.
- Code/schema/test commit:
  `ebada80f6aa95a9d8c2c321149ce45e33e106dcb`
  (`fix: harden g1 evidence registration audits`).
- Registry report provenance resolves the generator commit as `ebada80`, with
  10 registry hashes and validator SHA-256
  `94351669bf8a66374371de2b675e2fe871ea5067d1afc02ac68c3be338232846`.
- Registry audit result: `status=pass`, 10 files, 21 canonical metrics,
  10 parameters, 5 sources, 0 errors, and one warning that four external
  source records remain pending and are not verified evidence.
- Candidate audit result: `status=pass` means only that the read-only audit
  executed successfully. It records 210 changed paths, 210 rendered paths,
  0 omitted paths, five inspected Git blobs, and 20 unresolved findings.
- The candidate `training_seeds: [0, 1, 2, 3, 4]` conflict with the frozen G1
  seeds `[42, 123, 2024, 3407, 7919]` and remain unaccepted.
- Focused verification:
  `python -m pytest tests/test_g1_registries.py tests/test_g1_feature_branch_audit.py -q`
  returned `32 passed`.
- Full verification: `python -m pytest -q` returned `39 passed`; both audit
  CLIs returned `status=pass`; `git diff --check` returned no errors.
- No training, formal experiment, sealed-test access, external repository
  write, Word-file edit, push, merge, or pull request occurred in this wave.
- Fix-round code/test commit:
  `91466005f0927a14c408fe5f04da5a87dc78010c`
  (`fix: close g1 audit validation gaps`).
- Fix-round regenerated-evidence commit:
  `af388c76d4ddf7c7afdf610da1ec40dc1027361e`
  (`docs: record g1 fix round 1 evidence`).
- Independent scoped re-review found all original findings and both new
  fail-open findings addressed, with no new Critical or Important breakage.
- Fresh controller verification on `af388c7`:
  `python -m pytest -q` returned `45 passed`; the focused G1 suite returned
  `38 passed`; both audit CLIs returned `status=pass`; the registry audit
  reported 10 files, 21 metrics, 10 parameters, 5 sources, 0 errors, and one
  pending-source warning; `git diff --check` returned no errors.
- The protected first-problem repository remained at
  `1ca9e5ccc5f77ed775cd2b607dd70d635720accf` with the same 13 pre-existing
  modified/untracked paths recorded at G0.
- Handoff content commit:
  `ece353583fca5e222c405270c05110660cd416f1`
  (`docs: add g1 handoff and reopen contract gaps`), pushed to
  `origin/codex/problem2-g0-orchestration`. Local HEAD, upstream, and
  `git ls-remote` matched that hash after the push.
- PR #1 remained open and non-draft with head `ece3535...`; GitHub reported
  mergeability as recalculating (`null`/`unknown`) immediately after the push.
  G1.1 blocks merge regardless of that transient GitHub status.
- Corrected G1 acceptance commit:
  `8969e5e9ab3b88d0851d2d7c0ae1292892dfc99e`
  (`docs: accept g1 audit remediation`), pushed to
  `origin/codex/problem2-g0-orchestration`.
- Pushed-hash verification: `git rev-parse HEAD` and
  `git ls-remote origin refs/heads/codex/problem2-g0-orchestration` both
  returned `8969e5e9ab3b88d0851d2d7c0ae1292892dfc99e`.
- Persistence-record commit:
  `c2743566ae1e9c10b466f0cb18b1f9b2f7c6c3d3`
  (`docs: persist corrected g1 pushed hash`), pushed to
  `origin/codex/problem2-g0-orchestration`; local and remote hashes matched
  after the push.

Fix Round 1 remediation record:

- Scoped re-review found two additional Important fail-open paths: candidate
  `git grep` execution errors above return code 1 were recorded but ignored,
  and resource activation keys outside the experiment/sealed registries were
  not recursively rejected.
- RED verification returned `1 failed, 3 passed` for the simulated Git grep
  return-code-2 case and `4 failed, 30 passed` for cross-registry
  `battery_activation`, `battery_replenishment_enabled`,
  `battery_replenishment`, and `resource_replenishment` mutations.
- Code/test fix commit:
  `91466005f0927a14c408fe5f04da5a87dc78010c`
  (`fix: close g1 audit validation gaps`).
- The candidate audit now accepts only Git grep return codes 0/1 and preserves
  the actual failed command record before raising. The registry validator now
  applies pesticide-only and inactive-battery key checks recursively across
  every loaded registry while allowing ordinary battery-retention prose.
- Focused verification returned `38 passed`; full verification returned
  `45 passed`; both audit CLIs returned `status=pass`; `git diff --check`
  returned no errors.
- Regenerated registry and candidate reports resolve their generator commit as
  `91466005f0927a14c408fe5f04da5a87dc78010c`. The validator SHA-256 is
  `3760676483932e0e9b649b59ec0c4ead277f1303fdd20ac3dc4ef91f7315a74c`;
  the candidate auditor SHA-256 is
  `1d05c29a1addf029d6040e41219bed7d2a0a6edc50adf885e7f6e9545ec4f72f`.
- Maturity remains M1. No training, sealed-test access, external write, push,
  merge, or pull request occurred in Fix Round 1.

G1 handoff-audit reopening record:

- While preparing `HANDOFFG1.md`, two fresh read-only reviewers independently
  checked the accepted G1 state against the tracked YAML registries and the
  SR-MAPPO Problem 2 contracts.
- One reviewer found no Critical issue in the G2 handoff structure after its
  proposed corrections, but identified missing unit/service semantics, event
  ordering, G2/G3 mask ownership, cache invalidation, transition-table,
  per-transfer conservation, and two-stage persistence details. Those details
  are incorporated into `HANDOFFG1.md` as future G2 acceptance requirements.
- The factual reviewer found four additional G1 contract gaps, each confirmed
  directly against the repository and required reference contracts:
  `parameter_registry.yaml` lacks an executable per-service cap and an explicit
  request-threshold/safety-margin contract; `sealed_test_lock.yaml` uses the
  ambiguous `unlock_count: 1`; `artifact_manifest_schema.yaml` permits missing
  execution provenance for validated/locked artifacts and has no output hash;
  and `scenario_seed_manifest.yaml` forbids validation tuning although the
  experiment protocol requires validation scenes for checkpoint selection and
  algorithm tuning.
- These are specification/validator defects at G1, not G2 implementation
  findings. Per the stop-at-first-failed-gate rule, the previous G2 entry
  authorization is paused and G1 is reopened for one bounded remediation.
- The sealed-test range remains locked and unaccessed. The current
  `unlock_count: 1` field is interpreted only as the historical intended
  one-time policy until it is replaced by unambiguous maximum/actual counters.
- No G2 implementation, training, formal experiment, sealed-test access,
  external repository write, Word-file edit, PR merge, or protected-asset
  modification occurred during this handoff audit.
- After the handoff corrections, both scoped reviewers reported no remaining
  Critical or Important handoff-document findings; the G2 contract reviewer
  also reported no remaining Minor finding.
- Fresh controller verification returned `45 passed` for
  `python -m pytest -q`. Both G1 audit CLIs returned `status=pass` when their
  reports were redirected to one-time files under the system temporary
  directory, and `git diff --check` returned no content error. These audit
  passes reproduce the accepted validator behavior but do not clear the four
  newly verified contract gaps, because the current validator does not yet
  encode them.
- The protected first-problem repository remained at
  `1ca9e5ccc5f77ed775cd2b607dd70d635720accf` with the same 13 pre-existing
  modified/untracked paths recorded at G0.

G1.1 bounded remediation persistence record:

- Remediation base: `d5b2c26be017f7063ca71a2041a4ec8e8ef53d1b`.
- Contract/schema/test commit:
  `15f3eb882ba78597d1eb5cfecc2eda3cfb0efc6c`
  (`fix: close g1.1 registry contract gaps`).
- Initial regenerated-evidence commit:
  `288498e7933ac83b5be8b45733b52120f91a2ec4`
  (`docs: regenerate g1.1 audit evidence`).
- Independent full-range review found two successive Important fail-open paths:
  the service-cap/request-margin lower bounds were not independently constrained,
  and non-finite YAML/Python values could create unbounded parameter ranges.
- Lower-bound fix and evidence commits:
  `667ffcf74d625261a0fb0970df1db0e5c0d13a34` and
  `699f33a09906f2a24afa64f2c4d3aad6ab6d5c9a`.
- Finite-number fix and final evidence commits:
  `50a833468d58ba9c85c4588a8062db19a704152c` and
  `1b10457f64316dbd56e2ec2bf64f67db215602b6`.
- TDD RED evidence progressed through `9 failed, 32 passed`, then
  `3 failed, 40 passed`, `2 failed, 41 passed`, and `2 failed, 43 passed` for
  the four original gaps and two review-discovered fail-open paths.
- The final registries define 12 parameters, including a positive per-service
  transfer cap and nonnegative request safety margin, plus machine-readable
  transfer and request-trigger contracts. The sealed lock separates maximum
  (`1`) from actual (`0`) unlock count. Validated/locked artifacts require
  non-null generator commit/time/hash/version and output hash. Validation scenes
  permit checkpoint selection and algorithm tuning; sealed scenes remain locked
  and excluded from tuning.
- Final independent full-range review of `d5b2c26..1b10457` found no Critical,
  Important, or Minor issue and marked the bounded remediation ready at M1.
- Fresh controller verification on `1b10457`: `python -m pytest -q` returned
  `56 passed`; the focused G1 suite returned `49 passed`; both G1 audit CLIs
  returned `status=pass`; the registry audit reported 10 files, 21 metrics,
  12 parameters, 5 sources, 0 errors, and one pending-source warning;
  `git diff --check` returned no errors.
- The final registry report binds generator commit `50a8334`, validator SHA-256
  `0e07afbbe2e68e3a903e3416696c04fba0394ac41820d2e97d025e0029b847d4`,
  and all 10 registry input hashes. The candidate audit remains execution-only,
  inventories 210 paths, and does not accept candidate code or maturity claims.
- Content/evidence head `1b10457f64316dbd56e2ec2bf64f67db215602b6`
  was pushed to `origin/codex/problem2-g0-orchestration`; local HEAD, upstream,
  and `git ls-remote` matched after the push.
- Acceptance-state commit `9ece8297e83fef2cf10811de24e9a65becb26206`
  (`docs: accept g1.1 bounded remediation`) was pushed to the same branch;
  local HEAD, upstream, and `git ls-remote` matched after the push.
- No G2 implementation, training, formal experiment, sealed-test access,
  protected external write, Word-file edit, merge, or force-push occurred.
- The protected first-problem repository remained at
  `1ca9e5ccc5f77ed775cd2b607dd70d635720accf` with the same 13 pre-existing
  modified/untracked paths recorded at G0.

## Completed Tasks

- Completed A-E initial orchestration analysis with four read-only subagents:
  repo explorer, environment explorer, planning analyst, and experiment
  architect.
- Confirmed `Second` is the repository requested for future records.
- Confirmed `Second` current branch is clean before G0 edits.
- Confirmed existing `origin/main` assets cover M1 chapter 4.1/4.2 design and
  document delivery.
- Confirmed `origin/feature/problem2-code-framework` exists and contains
  substantial code/tests/verification assets requiring independent audit before
  integration.
- Confirmed first-problem repository has protected dirty files.
- Confirmed `D:/Pycharm/Locust_rl` is not a Git repository.
- Recorded hashes for planning documents and OSM inputs.
- Confirmed the two G0-generated Python cache files are excluded by the
  repository `.gitignore` and cannot enter the evidence history.
- Committed and pushed G0 content as `7731d37` on
  `codex/problem2-g0-orchestration`.
- Reopened the original G1 completion after independent final review and
  implemented one bounded fail-closed remediation wave at M1.
- Registered a canonical 21-metric contract, exact raw/validated table
  schemas, and 11 explicit fairness booleans.
- Strengthened candidate-branch audit provenance without integrating or
  accepting candidate code, reports, outputs, or maturity claims.
- Reopened G1 during handoff preparation after verifying four newly identified
  registry-contract gaps that the prior scoped reviews did not cover.
- Completed and persisted the bounded G1.1 remediation with fail-closed tests,
  regenerated reports, independent review, and a verified remote content head.

## Pending Tasks

- Decide whether selected candidate-branch assets can be independently
  reverified, copied into controlled modules, or must be rebuilt; no merge is
  implied by the G1 audit.
- Prepare the G2 design/specification and TDD plan, then build or verify
  deterministic G2 components:
  offline road ingestion, projection, topology, physical motion, service state
  machine, request lifecycle, and conservation tests.
- Build or verify G3 heterogeneous MARL components:
  role-local observations, action masks, saved masked log-prob replay,
  structured critic, team GAE, role gradient isolation, normalization freeze,
  and checkpoint round trip.
- Run G4 resource activation and counterfactual probes before any formal claim
  about mobile replenishment.
- Freeze G5 pilot protocol and baseline fairness before formal matrix jobs.
- Run G6/G7 formal and sealed experiments only after all prior gates pass.
- Generate G8 figures, tables, and thesis prose from locked summaries.

## Key Decisions

- `Second` is now the authoritative repository for all future second-problem
  code and documentation records.
- The current working branch is `codex/problem2-g0-orchestration`; no extra Git
  worktree was created because the branch is already isolated from `origin/main`.
- G1.1 is accepted at M1 after bounded remediation, independent full-range
  review, fresh verification, and remote persistence. Candidate-branch reports
  remain untrusted until later branch-local verification.
- First-problem historical results may justify choosing SR-MAPPO as the
  algorithmic base, but they are not formal second-problem causal evidence.
- Fixed-support, rolling-A*, same-source MAPPO, two-stage, sensitivity,
  ablation, and mechanism comparisons must be rerun or generated inside the
  second-problem evidence pipeline under the frozen protocol.
- The main comparison family remains:
  `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`,
  `mappo_mobile`, `sr_mappo_two_stage`.
- Formal six-scale protocol remains:
  `g20x20_d2=150`, `g20x30_d3=180`, `g20x40_d3=220`,
  `g30x30_d3=220`, `g30x40_d4=280`, `g30x50_d4=350`.
- Formal training seeds remain:
  `42`, `123`, `2024`, `3407`, `7919`.
- Validation scenario seeds remain `20000-20049`.
- Sealed-test scenario seeds remain `30000-30099`.
- Primary success threshold remains `reduction_rate >= 0.85`.

## Known Issues

- G2 deterministic-model implementation and evidence have not started.
- The current M1 branch does not include the extensive code framework from
  `origin/feature/problem2-code-framework`.
- The candidate branch contains M2/M3/M4 wording and forbidden-name mentions in
  its own docs/tests; the G1 audit records these as candidate-branch signals,
  not accepted maturity or implementation claims.
- `D:/Pycharm/Locust_rl` lacks Git history, so it cannot by itself provide a
  formal commit-level evidence chain.
- Engineering parameter sources remain incomplete: device manuals, field
  studies, expert confirmation, and source-value conversions are registered as
  pending G1 source records and still require independent verification.
- Resource activation has not been demonstrated in the current M1 evidence
  branch.
- No formal second-problem raw logs, validated tables, paired statistics, or
  locked figures exist in the repository evidence set.
- No claim is currently permitted that simulation outcomes reflect real
  deployment.
- Python cache files may still exist in the local working directory after tests,
  but `.gitignore` excludes them from GitHub evidence and commit boundaries.

## Next Step

Prepare the G2 deterministic-model design/specification and TDD plan from the
accepted G1.1 head. Create or use a dedicated
`codex/problem2-g2-deterministic-validation` branch/worktree before G2
implementation, and stop at the first failed deterministic gate. The highest
maturity remains M1; RL training, formal experiments, and sealed-test evaluation
remain unauthorized.
