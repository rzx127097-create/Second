# Project State

Last updated: 2026-08-24

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
- Current branch: `codex/problem2-g5-pilot-freeze`.
- Current branch base at start of G0:
  `2643753855c385253951dfad2c225be0b09b7e00`
  (`origin/main`, commit message `docs: mark section 4.2 delivery complete`).
- Existing remote feature branch:
  `origin/feature/problem2-code-framework` at
  `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`.
- Current highest maturity: `M2` implementation and scoped mechanism evidence.
- Current gate: G5 Tasks 1-4 are accepted at M2. The registry, fairness,
  budget-selection, partition, shared heterogeneous protocol/checkpoint, exact
  on-policy stability-component, and SR-MAPPO/MAPPO/PPO-IPPO implementation
  boundaries are persisted. G4 onboard-pesticide scarcity activation and
  diagnostic support-probe counterfactual remain the preceding accepted
  mechanism evidence. No G5 pilot has run. Formal jobs, validation tuning,
  sealed evaluation, and efficacy/superiority claims remain unauthorized.
- Sealed-test status: locked; maximum unlock count is `1`, actual unlock count
  is `0`, and no sealed-test result may be used for tuning.
- Main resource: pesticide-only replenishment.
- Battery replenishment: inactive until a separate activation audit passes.
- Frozen second-problem output root: `outputs/problem2_sr_mappo_v1`.

## G2 Deterministic Validation Record

The G2 implementation is recorded in `src/problem2/`, `scripts/`, and
`tests/g2/`. The self-contained handoff is `HANDOFFG2.md`; the Section 3-14
mapping is `docs/audits/g2-spec-compliance.md`; the design correction record is
Section 15 of `docs/superpowers/specs/2026-08-20-g2-deterministic-validation-design.md`.

Implementation/provenance:

- Clean generator commit: `d4dc97d02ede579cb6e8aedf4df65f4d5a47c107`.
- Generator tree SHA-256: `e43c84d592e55d0925e747d6edcf1c713eb0a93174bfb2bb510a2908831c16f6`.
- Source GraphML SHA-256: `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`.

Fresh verification:

- `python -m pytest tests/g2 -q`: `102 passed`.
- `python -m pytest -q`: `158 passed`.
- `python -m compileall -q src scripts`: exit 0.
- G2 preprocessor: six scales, status pass.
- G2 auditor: six scales, cross-process replay match, status pass.
- Artifact manifest: 14 entries, zero hash/byte mismatches.
- Maximum conservation error: `2.220446049250313e-16 L` with `1e-9 L` tolerance.

Fix-round review closed the output-root confinement, explicit reservation,
vehicle road-state validation, motion payload, six-cache publication, and cache
provenance findings. No training, formal experiment, validation/sealed scenario
access, protected external write, or deployment/effectiveness claim occurred.

Persistence status: content commit
`c47f157225c0b362828478d6d2d244ed183218a4` was pushed to
`origin/codex/problem2-g2-deterministic-validation`. Local HEAD, upstream HEAD,
and `git ls-remote` all matched this hash. Persistence record commit
`ab31744515eec0135e55054f438a010cbaee8b46` was then pushed, and the final local,
upstream, and remote hashes all match that record. The next authorized gate is
G3; RL training remains prohibited until G3 passes.

## G3 Task 1 Configuration Contract Record

Task 1 freezes the development-only heterogeneous SR-MAPPO configuration in
`configs/problem2/g3_heterogeneous_marl.yaml`, with evidence registered in
`docs/evidence/g3/g3_contract.yaml`. The loader is in `src/problem2/config.py`
and rejects validation or sealed-test training partitions, non-finite
hyperparameters, battery replenishment, and any drift from the frozen role,
action, dimension, stability-flag, or dependency contract. The canonical YAML
SHA-256 is
`421eff64d1161f78c9029dfc6d133b9b66247f3cf905b9577e55965584195f93`.

Verification before persistence:

- `python -m pytest tests/g3/test_g3_config.py -q`: `19 passed`.
- `python -m pytest tests/g2 -q`: `102 passed`.
- `python -m pip install --dry-run -r requirements-g3.lock`: exit 0 with the
  PyPI and CPU PyTorch wheel indexes declared by the lock file.
- `python -m compileall -q src`: exit 0.
- `git diff --check`: exit 0.
- The verified dependency environment is Python `3.11.15` and CPU-only PyTorch
  `2.13.0+cpu`; `requirements-g2.lock` was unchanged.

Persistence status: content commit
`8822edad2f48fc468fc00271e88de8926897cba6` (`feat: freeze g3 heterogeneous
marl contract`) was pushed to `origin/codex/problem2-g3-heterogeneous-marl`.
The local HEAD, upstream HEAD, and `git ls-remote` matched this hash before
this state record. This Task 1 record does not close G3 or authorize training
on validation or sealed scenarios.

Task 1 hardening and planning synchronization:

- Hardening commit `098f119938754947644ae28c5f8adef03394a0d8`
  (`fix: harden g3 contract validation`) closes the Task 1 review findings for
  installable CPU PyTorch locking, independent registry/hash parity, unknown
  and duplicate YAML keys, exact optimization freezes, and immutable stability
  flags.
- Planning commit `176f54925a866846e56bcbad79901b80ddd16313`
  (`docs: add g3 heterogeneous marl plan`) records the G3 design and execution
  plan in `docs/superpowers/`.
- Fresh verification before the push: `python -m pytest
  tests/g3/test_g3_config.py -q` returned `19 passed`; `python -m pytest
  tests/g2 -q` returned `102 passed`; `python -m compileall -q src scripts`
  exited 0; `git diff --check` exited 0.
- Push verification after the push: local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g3-heterogeneous-marl` all
  returned `176f54925a866846e56bcbad79901b80ddd16313`.
- This synchronization still does not close G3; the role-learning acceptance
  suite, controlled development smoke, gate report, and HANDOFFG3 remain open.

Content-push verification:

- `python -m pytest tests/g2 -q`: `102 passed`.
- `python -m pytest -q`: `158 passed`.
- `python -m compileall -q src scripts`: exit 0.
- `python scripts/preprocess_g2_roads.py --config configs/problem2/g2_deterministic.yaml`: six scales, status pass.
- `python scripts/audit_g2_deterministic.py --config configs/problem2/g2_deterministic.yaml --report outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json`: six scales, replay match, status pass.
- `git diff --check`: exit 0.
- Content-push check: `git rev-parse HEAD`, `git rev-parse '@{upstream}'`, and
  `git ls-remote origin refs/heads/codex/problem2-g2-deterministic-validation`:
  all `c47f157225c0b362828478d6d2d244ed183218a4`.
- Final persistence check: the same three commands all returned
  `ab31744515eec0135e55054f438a010cbaee8b46`; `git status --short --branch`
  showed a clean worktree.

## G3 Heterogeneous MARL Acceptance Record

G3 now passes at maturity `M2`. The implementation remains engineering
evidence only; it does not promote the project to M3 and does not support
mobile-treatment efficacy, superiority, formal-experiment, or deployment
claims.

Implementation and evidence:

- Implementation hardening commit:
  `092b7f3e965a24979bac65c8304cd9d7dc142f73`.
- G3 configuration hash:
  `421eff64d1161f78c9029dfc6d133b9b66247f3cf905b9577e55965584195f93`.
- Source-tree commit bound to the canonical smoke:
  `092b7f3e965a24979bac65c8304cd9d7dc142f73`.
- Implementation source-tree hash:
  `a3b5f20c6935cf29c0c0edb627cf64a0b4b5c7b96a3ca94449c205da1b5f2a95`.
- Scenario seed manifest:
  schema `g1.v1`,
  SHA-256
  `ab993f19e1ae4cb9d7ba4f4f862639901581be057e0a251e5c113d957f6059ce`.
- Acceptance result: `17/17`, audit `status=pass`.

Canonical smoke artifacts:

- `outputs/problem2_sr_mappo_v1/g3/training-smoke.jsonl`:
  SHA-256
  `9885e24a0e58191fdd7975b55d72487d3f817985c8a0ec585d737af5228e2972`,
  `2204` bytes.
- `outputs/problem2_sr_mappo_v1/g3/provenance.json`:
  SHA-256
  `10da75b9c01d485ece3e6214de10367ba5356d80e4be97e38a1e399afb9ed69d`,
  `756` bytes.
- `outputs/problem2_sr_mappo_v1/g3/checkpoints/g3-smoke.pt`:
  SHA-256
  `832ddd1350ff82a0642b144c4d962e762f47b294dcc00873354e2df99159d0b3`,
  `1293261` bytes.
- `outputs/problem2_sr_mappo_v1/g3/g3-marl-audit.json`:
  SHA-256
  `b9e2829f02372235bba856317767b8d0703d83e5841c75befab68d092ddc6b2c`,
  `4874` bytes.

Fresh verification:

- `python -m pytest tests/g3 -q`: `63 passed`.
- `python -m pytest -q`: `221 passed`.
- `python -m compileall -q src scripts`: exit 0.
- `git diff --check`: no content errors.
- Canonical development smoke: seed `9017`, `2` updates, finite losses,
  `source_tree_clean: true`, validation/sealed access false.
- Canonical G3 auditor: `17/17` acceptance nodes, `status=pass`.

The next authorized gate is G4. G4 must begin with resource-scarcity
activation and counterfactual mechanism probes. The G3 smoke must not be used
as treatment efficacy evidence. Formal jobs, validation tuning, and sealed
evaluation remain unauthorized.

Persistence status:

- Implementation hardening commit
  `092b7f3e965a24979bac65c8304cd9d7dc142f73` was pushed to
  `origin/codex/problem2-g3-heterogeneous-marl`.
- Evidence content commit
  `5d7fa5e2ae4ee490ca9ab02c2956a82ccb77118f` was pushed to the same branch.
- For the evidence content commit, `git rev-parse HEAD`,
  `git rev-parse '@{upstream}'`, and
  `git ls-remote origin refs/heads/codex/problem2-g3-heterogeneous-marl` all
  returned `5d7fa5e2ae4ee490ca9ab02c2956a82ccb77118f`.
- The separate persistence-record commit is the final required G3
  synchronization before G4 work begins.

## G4 Resource-Scarcity Mechanism Acceptance Record

G4 passes at the existing `M2` maturity boundary after corrective final-review
remediation and controller verification. The accepted evidence is diagnostic
support-probe mechanism evidence for limited onboard UAV pesticide only; it
does not authorize formal jobs, validation tuning, sealed evaluation,
mobile-treatment efficacy claims, SR-MAPPO superiority claims,
vehicle-inventory scarcity claims, G3 actor-execution claims, or deployment
claims.

- Canonical evidence content commit:
  `189e22744579001915919af24ed2bdfd099ff2f2`
  (`docs: accept g4 after final verification`), prepared on
  `codex/problem2-g4-resource-scarcity`.
- Generator/code commit bound in the canonical G4 artifacts:
  `09d361994100741a9ae834b63ba07c9b5db953e7`
  (`docs: finalize g4 round 2 report`).
- Executed scarcity axis: `initial_uav_pesticide_l`, sampled at `0.05`,
  `0.2875`, and `0.525 L`, all within the frozen G2 usable UAV capacity
  `1.08 L`.
- Fixed support inventory: `initial_vehicle_inventory_l = 20.0 L`, matching the
  G1 parameter registry and frozen G2 configuration. Vehicle inventory is not
  swept and no vehicle-inventory scarcity or depletion claim is permitted.
- Executed arms: `fixed_support_probe` and `mobile_support_probe`. They are
  deterministic diagnostic support probes, not loaded G3 actor/checkpoint
  executions; SR-MAPPO remains the public project identity only.
- Metric semantics: `started_service_waiting_time_s` counts waits for requests
  that reached service start, while `euclidean_service_start_distance_m` is
  Euclidean separation at service start, not road-travel distance.
- Canonical G4 evidence is preserved below
  `outputs/problem2_sr_mappo_v1/g4` with source commit `09d361994100741a9ae834b63ba07c9b5db953e7`, source tree
  `5a61825001e92fae112579ae05f5c778deedcab3`, source bundle SHA-256
  `d2a8a4a4dced015a8f77483d30077b5a24948a97ac1f82b979d6ba968f9df3ed`, and contract SHA-256
  `2847f32a64b3d8b80a1e8ec8c5ff56b407ba3abc05cfb1d5780c8a31e18f11ea`.
- Hardened audit result: `status=pass`, exact matrix shape `3 x 3 x 3` per
  arm, 27 same-input pairs, 10 manifest artifacts, validation/sealed access
  false, battery replenishment false, no G3 endpoint evidence, and no G3
  actor/checkpoint execution.
- Final-review remediation also rejects realistic G3 paths, root or nested
  manifest bypasses, truthy G3 execution flags, and reserved validation/sealed
  seed IDs in manifested JSON/JSONL. Generation rejects dirty source paths and
  emits per-file plus deterministic source-bundle hashes verified by the audit.
- The audit now fails closed if `artifact-manifest.json` is missing, rejects
  G3 endpoint references in artifact paths and string values, verifies raw
  records execute the declared UAV-initial-pesticide axis, and requires active
  records to show positive request/reservation/service, requested pesticide,
  transferred pesticide, and vehicle inventory use.
- Permitted claim: the diagnostic support probes exercised the frozen
  onboard-pesticide scarcity mechanism and emitted paired descriptive deltas.
  No efficacy, superiority, formal-result, deployment, vehicle-inventory
  scarcity, or G3 actor-execution claim is permitted.
- Fresh controller verification:
  `python -m pytest tests/g4 -q`: `76 passed in 78.54s`;
  `python -m pytest -q`: `297 passed in 115.76s`;
  `python -m compileall -q src scripts`: exit `0`;
  `git diff --check`: exit `0`;
  `python scripts/run_g4_mechanism_probe.py`: `[0.05, 0.525]`;
  `python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`:
  `status=pass artifacts=10`.

Persistence status:

- Acceptance-state commit
  `189e22744579001915919af24ed2bdfd099ff2f2`
  (`docs: accept g4 after final verification`) was pushed to
  `origin/codex/problem2-g4-resource-scarcity`.
- After the push, `git rev-parse HEAD`, `git rev-parse '@{upstream}'`, and
  `git ls-remote origin refs/heads/codex/problem2-g4-resource-scarcity` all
  returned `189e22744579001915919af24ed2bdfd099ff2f2`.

G5 is the next authorized gate. It may begin as a pilot-protocol freeze gate
and must pre-register fair
pilot scenarios, comparison budgets, validation-tuning rules, paired
statistical estimands, exclusions, and artifact schemas before any formal or
sealed evaluation is accepted.

## G5 Phase 0: G4 Lineage Reconciliation

The G4 entry lineage blocker is resolved by
`docs/audits/g4-lineage-reconciliation.md` and
`scripts/audit_g4_lineage.py`. The canonical bundle is preserved because every
embedded lineage resolves to one exact tuple:

- generator commit: `09d361994100741a9ae834b63ba07c9b5db953e7`;
- generator tree: `5a61825001e92fae112579ae05f5c778deedcab3`;
- source bundle SHA-256: `d2a8a4a4dced015a8f77483d30077b5a24948a97ac1f82b979d6ba968f9df3ed`;
- G4 contract SHA-256: `2847f32a64b3d8b80a1e8ec8c5ff56b407ba3abc05cfb1d5780c8a31e18f11ea`;
- artifact manifest SHA-256/bytes: `7ec50bd98dedf948cca03179decb09f89071df3cb8d64b699726bc7434a6f56c` / `1718`;
- canonical artifact count: `10`.

The current G4 handoff, compliance audit, and this acceptance section now
reference the same tuple. The nonexistent long object previously recorded in
the narrative is no longer an accepted evidence identifier. Phase-0 fresh
verification returned `78 passed` for
`python -m pytest tests/g4 tests/g5/test_g4_lineage_reconciliation.py -q`,
`status=pass artifacts=10` from the G4 CLI, `status=pass` from the lineage
CLI, exit `0` from `python -m compileall -q src scripts`, and no content errors
from `git diff --check`. No G5 pilot, validation, formal job, or sealed-test
access occurred.

The phase content commit and its remote parity are recorded in the required
follow-up persistence commit before Task 2 begins.

Persistence verification for this phase:

- Content commit: `cc3dc9115e6d963b01834ec17d7cd8915084ff3f`
  (`fix: reconcile g4 evidence lineage`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`.
- `git rev-parse HEAD`, `git rev-parse '@{upstream}'`, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all returned
  `cc3dc9115e6d963b01834ec17d7cd8915084ff3f` before this persistence commit.
- Phase status: accepted at M2 provenance consistency; no G5 pilot,
  validation, formal job, or sealed-test access occurred.

## G5 Phase 1: Experiment Contract Freeze

G5 Phase 1 freezes the registries and fail-closed loaders needed before any
algorithm implementation or pilot execution. It does not run a pilot and does
not raise maturity beyond `M2`.

Frozen contract boundaries:

- learning algorithms are exactly `sr_mappo_mobile`, `mappo_mobile`,
  `ippo_mobile`, `maddpg_mobile`, and `iql_mobile`; Problem-2 comparison
  conditions remain registered separately;
- development identities are training seeds `51001`, `51002`, `51003` and
  scenarios `10000-10019`; formal training, validation, and sealed identities
  remain unchanged and pairwise disjoint;
- validation and sealed access flags remain false, and sealed actual unlock
  count remains `0`;
- the primary fairness budget is environment interactions, all 17 frozen
  fairness invariants are true, and candidate selection uses four immutable
  configurations per learning algorithm;
- formal-budget candidates remain `[50000, 100000, 200000]`, with a maximum
  projected slowest-job runtime of 12 hours and 20 checkpoints;
- `requirements-g3.lock` remains CPU-only, while the isolated `.venv-g5`
  resolves `torch==2.13.0+cu126` and supports both CPU and RTX 4060 CUDA tensor
  execution;
- eight Problem-1 source blobs resolve read-only at commit
  `1ca9e5ccc5f77ed775cd2b607dd70d635720accf`; runtime, checkpoint, and result
  imports from the protected repository remain prohibited.

Fresh verification before the content push:

- TDD CLI RED: `20 passed, 1 failed`, with the sole failure caused by the
  missing `scripts/audit_g5_contracts.py`; after implementation the G5 suite
  returned `21 passed`;
- required `.venv-g5` focused suite: `70 passed in 21.55s`;
- full host regression: `320 passed in 181.64s`;
- G1 registry audit: `status=pass`, 10 files, 21 metrics, 12 parameters,
  5 sources, 0 errors, and one warning for four pending external sources;
- candidate-branch audit: `status=pass`, base `2643753`, candidate `52a92c0`,
  and 210 inventoried changed paths; this remains an execution-only audit and
  does not accept candidate maturity claims;
- G5 contract CLI: `status=pass`, 16 contract hashes, all fairness flags true,
  validation access false, sealed access false, and actual unlock count `0`;
- CUDA/CPU check: `torch==2.13.0+cu126`, NVIDIA GeForce RTX 4060 Laptop GPU,
  CPU and CUDA tensor operations passed;
- compileall and `git diff --check` exited `0`.

The formula-symbol scanner reported 31 findings in the executable plan. Each
finding was context-checked as a code identifier, path, configuration key, or
literal test example because the scanner does not remove Markdown code spans;
there was no prose formula or mojibake defect to rewrite. A full test run from
`.venv-g5` is not a declared gate and stops during collection because the
legacy chapter-4.2 artifact test imports Pillow, which is present in the host
document environment but intentionally absent from the exact G5 lock.

Persistence status:

- content commit `cc6d0985895a4ab3e9c85a6d19b963ed5a58e2dd`
  (`feat: freeze g5 experiment contracts`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the content push, local HEAD, upstream HEAD, and `git ls-remote` all
  returned `cc6d0985895a4ab3e9c85a6d19b963ed5a58e2dd`;
- no pilot, validation tuning, formal job, sealed-test access, protected
  external write, or Word-file edit occurred.

Phase 1 authorized Task 3 shared heterogeneous algorithm protocol work. Its
implementation and persistence hash are now verified; Task 4 is the next
authorized work.

## G5 Task 3: Shared Heterogeneous Protocol

Task 3 adds the method-neutral two-role protocol and persistence primitives at
M2. It does not implement any of the five learning algorithms, run pilots, or
access validation or sealed scenarios.

Implemented contracts:

- `HeterogeneousAlgorithm` exposes role-local `act`, `observe`, `update`,
  evaluation mode, state, and diagnostics operations;
- `ActionResult` binds sampled actions to the exact behavior-time masks, and
  `RoleBatch` requires that binding so an independently substituted legal mask
  cannot enter replay;
- role-local `RoleNetwork`, serializable diagnostics, and `JointReplayBuffer`
  preserve mask, transition identity, ring position, size, and replay RNG;
- `g5-training-checkpoint-v1` writes through a same-directory temporary file,
  reloads and hashes before replacement, retains `<checkpoint>.previous`,
  captures Python/NumPy/CPU-Torch/CUDA RNG state, and rejects incomplete,
  extra, malformed, or drifted provenance;
- G3 `g3-checkpoint-v1` save/load behavior remains unchanged.

Fresh verification:

- TDD RED for the initial APIs: 2 collection errors for the missing protocol
  modules/functions;
- review-fix RED: `11 failed, 15 passed` for the three integrity regressions;
- exact-mask binding RED: one direct-construction bypass test failed before the
  final fix;
- G5 Task 3 focused suite: `27 passed`;
- G3 regression suite: `63 passed`;
- host full regression: `347 passed in 190.86s`;
- compileall and `git diff --check`: exit `0`.

Independent review found and required fixes for three integrity issues: exact
behavior-mask provenance, complete fail-closed checkpoint provenance, and
replay defensive copies. Two scoped re-reviews marked all three addressed and
found no new Critical or Important issue. The checkpoint provenance contract
is exactly `source_commit` (40 lowercase hexadecimal characters),
`source_bundle_sha256`, `config_hash`, `protocol_hash`, and `ancestry_hash`
(each 64 lowercase hexadecimal characters).

The isolated `.venv-g5` full repository suite remains unable to collect the
legacy chapter-4.2 artifact test because the exact G5 lock intentionally omits
Pillow; the required G5 and G3 suites pass in that environment, and the host
environment supplies Pillow for the complete regression.

Persistence status:

- implementation commits `7254c1f74aaa55c3113d01d2325588e39a742e38`,
  `3f5f218ff6cde06d75942c5b7b6c8e2df888e8b5`, and
  `618afdcff25cb4853507a7cd10f0c8e0bd9699c1`
  (subjects `feat: add shared g5 heterogeneous algorithm protocol`,
  `fix: close g5 protocol review gaps`, and `fix: require bound g5 behavior
  results`) were pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the implementation push, local HEAD, upstream HEAD, and
  `git ls-remote` all returned
  `618afdcff25cb4853507a7cd10f0c8e0bd9699c1`;
- no pilot, validation tuning, formal job, sealed-test access, protected
  external write, or Word-file edit occurred.

Task 3's protocol and checkpoint interfaces remain the required shared
boundary. Task 4 consumed that boundary as recorded below; Task 5 is the
current next authorized work.

## G5 Task 4 Prerequisite: On-Policy Stability Contract Correction

Task 4 plan review found that its required SR-MAPPO-versus-MAPPO
configuration-diff proof could not be constructed from the accepted G5
registry: `methods.yaml` registered the method family but did not freeze the
stability-component values named by Task 4. The preceding contract layer was
therefore corrected before algorithm implementation.

The corrected contract freezes all seven executable flags for the three
on-policy methods. `sr_mappo_mobile` requires every flag true;
`mappo_mobile` and `ippo_mobile` require every flag false. The strict loader
rejects missing, extra, non-boolean, or drifted flags and exposes nested
read-only mappings.

Fresh verification before the content push:

- TDD RED: `4 failed, 21 passed`, caused by the absent registry field and
  loader property;
- corrected G5 contract suite: `25 passed`;
- G5/G1 registry regression: `74 passed in 15.39s`;
- G5 contract CLI: `status=pass`, validation access false, sealed access
  false, and actual unlock count `0`;
- compileall and `git diff --check`: exit `0`.

Persistence status:

- correction commit
  `6504f671a942f74452a3c4e170202d35e3cbfea9`
  (`fix: freeze g5 on-policy stability contract`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the push, local HEAD, upstream HEAD, and `git ls-remote` all returned
  `6504f671a942f74452a3c4e170202d35e3cbfea9`;
- no pilot, validation tuning, formal job, sealed-test access, protected
  external write, or Word-file edit occurred.

Task 4 on-policy algorithm implementation is recorded below.

## G5 Task 4: On-Policy Comparison Algorithms

Task 4 implements the protocol-conforming on-policy comparison family at M2:
`sr_mappo_mobile`, `mappo_mobile`, and `ippo_mobile`. It does not run a pilot,
access validation or sealed scenarios, or support an algorithm-ranking claim.

Implemented and verified boundaries:

- `build_algorithm` constructs every frozen `c01-c04` candidate for all three
  methods and rejects unregistered methods or candidates;
- SR-MAPPO retains shared UAV and separate vehicle actors, a centralized team
  critic, GAE/PPO, and all frozen stability groups; same-source MAPPO reuses the
  same implementation and differs only through the registered stability flags;
- PPO uses the `ippo_mobile` implementation identity with shared UAV and
  separate vehicle role-local actor/value pairs and no centralized critic
  input;
- `OnPolicyEnvelope` is the sole algorithm training-ingest boundary. It binds
  exact behavior actions, masks, replayed log probabilities, team reward,
  team/role validity, identities, candidate-slot mapping, normalization
  versions, and centralized or role-local value inputs;
- invalid team or role-agent samples cut the matching GAE trace, produce
  neutral targets, and cannot contaminate preceding valid targets;
- frozen clip radii, role-valid advantage populations, shuffled minibatches,
  sample-weighted metrics, deterministic evaluation freeze, and exact update
  counts are executable and tested;
- G5 method state is validated completely before live mutation, includes
  networks, optimizers, schedulers, normalizers, pending envelopes, counters,
  trainer RNG, and frozen configuration, and reproduces the next update after
  checkpoint recovery;
- non-finite envelope data, losses, or gradients fail closed, with transactional
  rollback protecting parameters and optimizer state;
- the G3 return-normalized critic regression now compares current predictions,
  old values, and return targets in one normalized domain while keeping physical
  critic output and GAE semantics unchanged.

TDD and review evidence:

- review-fix RED progressed through `15 failed, 23 passed`, a missing-envelope
  collection error, targeted resume/rollback failures, `49 failed, 33 passed`,
  and `10 failed, 101 passed` before the corresponding fixes;
- three scoped fix rounds closed behavior binding, frozen candidate/clip
  execution, fail-closed resume, finite rollback, metric aggregation,
  team-valid GAE, and type-exact checkpoint findings;
- the final independent scoped review returned `Ready`, with no open Critical
  or Important finding.

Fresh controller verification on the pushed content commit:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5 -q`:
  `165 passed in 19.72s`;
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 -q`:
  `65 passed in 22.72s`;
- host `python -m pytest -q`: `464 passed in 140.02s`;
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts`: exit `0`;
- G5 contract audit: `status=pass`, all 17 fairness flags true, validation and
  sealed access false, and actual sealed unlock count `0`;
- `git diff --check`: exit `0`.

Persistence status:

- content commit `0593f17edad38a892115a375c1ac836cf8081e19`
  (`feat: implement g5 on-policy comparison algorithms`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the content push, local HEAD, upstream HEAD, and `git ls-remote` all
  returned `0593f17edad38a892115a375c1ac836cf8081e19`;
- the user-owned `_tmp_docx_assets/` path remains untracked and untouched; no
  pilot, validation tuning, formal job, sealed-test access, protected external
  write, or Word-file edit occurred.

Task 5 heterogeneous discrete MADDPG and IQL implementation is the next
authorized work. G5 as a whole remains open at M2.

## G5 Task 5 Context-Free Handoff Record

`HANDOFFG5.md` is rewritten as the current self-contained continuation record
for a conversation with no prior context. It authorizes only Task 5
heterogeneous discrete MADDPG/IQL implementation and explicitly forbids Task 6,
pilots, validation tuning, formal jobs, sealed-test access, and
efficacy/superiority claims.

The handoff records the Task-4 persistence baseline, Tasks 1-4 completion
summary, exact Task-5 files and interfaces, frozen `c01-c04` MADDPG/IQL grids,
TDD/review/verification order, commit/push/state requirements, M2 claim
boundary, and stop conditions. It also identifies the accepted protocol hazard:
the abstract `observe` boundary is currently on-policy-only while
`JointReplayBuffer` stores `RoleBatch`, which lacks MADDPG current/next
structured critic state. Task 5 must resolve that hazard with a strict typed
off-policy envelope or reviewed general transition protocol without weakening
`OnPolicyEnvelope`, actor information isolation, behavior-mask binding, or
checkpoint/replay integrity.

Document verification before the content push:

- `git diff --check`: exit `0`;
- `audit_formula_symbols.py HANDOFFG5.md`: exit `0`, no findings;
- stale-current-state scan found no remaining instruction to start Task 1,
  seek design approval, or defer code implementation;
- staged diff contained only `HANDOFFG5.md`; the user-owned untracked
  `_tmp_docx_assets/` directory remained untouched.

Persistence status:

- handoff content commit
  `316e0e60e9982a33ba810670fa8fb22cc20334bc`
  (`docs: update g5 task 5 handoff`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the content push, local HEAD, upstream HEAD, and `git ls-remote` all
  returned `316e0e60e9982a33ba810670fa8fb22cc20334bc`;
- current handoff SHA-256:
  `D681387F91FC7BB57105C1A69EECE71F4B9D98D5B2F0F87EA14F2BDD20BB623E`;
- no source/configuration file changed, so no code test suite was rerun for
  this documentation-only handoff update;
- no pilot, validation tuning, formal job, sealed-test access, protected
  external write, or Word-file edit occurred.

This handoff record does not complete Task 5, pass G5, or raise maturity above
M2. Task 5 remains the only next authorized work.

## G5-G7 Written Design Record

The approved-in-chat G5-G7 architecture has been split into three formal
written specifications for user review:

- `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md`, SHA-256
  `1F6C4A8ECC90D63D9D81A0858286F555BA3E3365342A26BF77423E72C53EC0FD`;
- `docs/superpowers/specs/2026-08-22-g6-formal-jobs-design.md`, SHA-256
  `958975DAA4F8875DFC59280B5B4A03A1F11AD922683A4CCCC7FA45F48CB11B20`;
- `docs/superpowers/specs/2026-08-22-g7-sealed-analysis-design.md`, SHA-256
  `CD6BC6EE8F7A2BFE9C2ED6829CEFC36B813558B2FA8FAF9BFAFAED5A2E276005`.

The design freezes these main boundaries:

- G5 implements and pilots all five heterogeneous algorithms, Problem-2
  comparators, vehicle heuristics, remove-one ablations, sensitivity support,
  orchestration, validation, recovery, and statistics code before freezing
  the G6/G7 manifests;
- G6 executes exactly 375 deduplicated immutable formal training jobs and
  validation-based checkpoint selection without sealed-test access;
- G7 consumes the one permitted sealed unlock, executes exactly 42,500
  deduplicated sealed episode evaluations, and locks paired statistics and
  mechanism/ablation/sensitivity summaries for G8;
- the five-algorithm family is SR-MAPPO, MAPPO, PPO implemented as
  heterogeneous IPPO, MADDPG, and IQL, with explicit UAV/vehicle observation,
  action, mask, network, optimizer, transition, and checkpoint handling for
  every method.

The specification self-review found no placeholder, unbalanced code fence,
gate leakage, or unresolved matrix-count contradiction. The formula-symbol
audit found only literal underscore-containing code paths/identifiers inside
backticks; formula-like prose and equations use editable LaTeX notation.

Fresh verification before the design-content push:

- `python -m pytest -q`: `297 passed in 171.36s`;
- `python -m compileall -q src scripts`: exit `0`;
- `git diff --check`: exit `0`;
- sealed scenarios were not accessed and no protected external asset was
  modified.

Persistence status:

- design-content commit
  `a12cbdd0bf479d93bd1788497d82447313933d39`
  (`docs: define g5-g7 experiment gates`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the push, local HEAD, upstream HEAD, and `git ls-remote` all matched
  `a12cbdd0bf479d93bd1788497d82447313933d39`.

This record does not pass G5 or raise maturity. The user authorized entry into
the G5 workflow on 2026-08-22, and the executable plan record below supersedes
the earlier pending-plan status.

## G5 Executable Plan Record

The reviewed G5/G6/G7 design is decomposed into the executable plan
`docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`, SHA-256
`DBAC425E908E9DCB79C21174484B1DD5ED430CF028876A56AD12C1C719FED11E`.
The plan contains 12 gated tasks and 87 executable TDD/verification steps. It
starts with G4 lineage reconciliation and then covers G5 registries, five
heterogeneous algorithms, physical metrics and controllers, the exact
375-training-job graph, orchestration/recovery/validation, paired statistics,
CPU/CUDA smoke, development pilots, validation tuning, and G6/G7 manifest
freezing while sealed access remains disabled.

Environment inspection during planning found an RTX 4060 Laptop GPU with
8188 MiB and driver 572.70, while the current host Python intentionally uses
the G3 evidence lock `torch==2.13.0+cpu`. The official PyTorch index contains
the matching Windows CPython 3.11 CUDA build `torch==2.13.0+cu126`; the plan
therefore preserves the G3 lock and creates an isolated `.venv-g5` with a
separate G5 CUDA lock before GPU smoke. No dependency was installed or replaced
during planning.

Fresh verification before the plan-content push:

- `python -m pytest -q`: `297 passed in 141.49s`;
- `python -m compileall -q src scripts`: exit `0`;
- `git diff --check`: exit `0`;
- plan self-review: 12 tasks, 87 executable steps, zero placeholder patterns;
- formula-symbol audit findings were confined to literal code paths,
  identifiers, function names, and configuration keys.

Persistence status:

- plan-content commit
  `e2508eddef0b1d20ae9ddd282807395511e1b58d`
  (`docs: add g5 implementation plan`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the push, local HEAD, upstream HEAD, and `git ls-remote` all matched
  `e2508eddef0b1d20ae9ddd282807395511e1b58d`.

This plan record does not pass G5, change maturity, authorize validation before
candidate-manifest freezing, or authorize formal/sealed execution.

At the executable-plan checkpoint, `HANDOFFG5.md` had SHA-256
`066428AEC27BCCEB0D133A8542BB0998FE2E13012F4C5CAE9202915447C64743`
and directed a context-free worker to Task 1. That handoff is a historical
snapshot and is superseded by the Task-5 handoff record above; it must not be
used as the current continuation instruction.

## Original HANDOFFG5 Record

The self-contained G5 handoff for a new context is
`HANDOFFG5.md`, SHA-256
`0681C3A0DB2B5CF1523F20F547B34CF77C1405DDFE5B45F280DAABA35C9A5AB9`.
It records the completed G0-G4 evidence, G4 lineage blocker, written G5-G7
design hashes, five-algorithm heterogeneous contract, declared `375`/`42,500`
design counts, G5 work packages, pilot protocol, verification requirements,
and the exact next action for a context-free conversation. At that historical
checkpoint it stated that G5 implementation and the executable plan had not
started; the executable-plan record above supersedes that current-status
statement without deleting the original evidence record.

Persistence status:

- HANDOFF content commit
  `80fccb1350a4c3f1df221730335be1fb1263496b`
  (`docs: add g5 implementation handoff`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`;
- after the push, local HEAD, upstream HEAD, and `git ls-remote` all matched
  `80fccb1350a4c3f1df221730335be1fb1263496b`;
- verification before the content push: `python -m pytest -q` returned
  `297 passed in 161.36s`, `python -m compileall -q src scripts` exited `0`,
  and `git diff --check` exited `0`.

This handoff record does not pass G5, change the maturity level, authorize
validation tuning, or authorize formal/sealed evaluation.

## Superseded Pre-Final-Review G4 Record

The following historical record is superseded by the final-review remediation
above and must not be used as the current G4 contract or claim boundary.

G4 passes at the existing maturity boundary `M2`: its frozen pesticide
resource-scarcity mechanism activated across the registered development probe,
and the fixed/mobile SR-MAPPO counterfactual produced descriptive paired
deltas. This is not formal treatment-effect, significance, superiority, or
deployment evidence.

Frozen interface and canonical evidence:

- Public algorithm: `SR-MAPPO`; Problem 2 is its air-ground heterogeneous
  extension.
- Resource scope: pesticide only; battery replenishment is inactive.
- Contract: `docs/evidence/g4/g4_contract.yaml`, SHA-256
  `6e9049414421dcf03be373fe7c53bae5ed4576c2b9e94bc45168a266cfeb936a`.
- Probe manifest: `docs/evidence/g4/g4_probe_manifest.yaml`, SHA-256
  `f6b2ba647d5b7302c200f816acd995978d5695dcee27a35a34995d5c7dc5b4f1`.
- Historical vehicle-inventory sweep: `[1.0, 12.0] L`; its initial UAV
  pesticide was `0.05 L`. This superseded record is not the current scarcity
  axis. Probe scales were `g20x20_d2`, `g20x30_d3`, `g30x30_d3`; seeds `42`,
  `123`, `2024`.
- Counterfactual pair: `sr_mappo_fixed` and `sr_mappo_mobile`, with 27
  same-input descriptive pairs and equal activation counts of 27 per arm.
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`, including
  `activation-summary.json`, `counterfactual-summary.json`, `provenance.json`,
  `g4-mechanism-audit.json`, and `artifact-manifest.json`.
- The fail-closed audit records `status=pass`, `10` supported JSON/JSONL
  artifacts, validation/sealed access false, battery replenishment false, and
  G3 endpoint evidence rejected.

Fresh verification after the G4 evidence-bundle fix round:

- `python -m pytest tests/g4 -q`: `40 passed in 24.54s`.
- `python -m pytest -q`: `261 passed in 63.18s`.
- `python -m compileall -q src scripts`: exit `0`.
- `git diff --check`: exit `0`.
- `python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`: `status=pass artifacts=10`.

Persistence status: final persistence-record commit
`97f92bf2d93f662963f47ffce43e412bbbe33e4a`
(`docs: record g4 persistence verification`) was pushed to
`origin/codex/problem2-g4-resource-scarcity`. After this state record,
`git rev-parse HEAD`, `git rev-parse '@{upstream}'`, and
`git ls-remote origin refs/heads/codex/problem2-g4-resource-scarcity` all
returned `97f92bf2d93f662963f47ffce43e412bbbe33e4a`.

G5 is the next authorized gate. It must freeze a
fair pilot protocol before any formal job: identical environment, pesticide
budget, horizon, scenario/seed identity, observability, and information
conditions across comparison arms; declared validation-tuning rules; sealed
access disabled; and paired statistical estimands, exclusions, and artifact
schemas independently audited. No formal job, validation tuning, sealed
evaluation, or thesis efficacy/superiority claim is authorized yet.

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
- Implemented and reviewed the G2 deterministic foundation: offline road source,
  metric projection/topology, physical motion, explicit reservation/service
  states, pesticide ledger, transactional replay, and fail-closed audit CLIs.
- Regenerated six cache pairs, the 183-event deterministic trace, audit report,
  and 14-entry artifact manifest from clean generator commit `d4dc97d`.
- Reconciled the G4 evidence lineage, then froze and verified the G5 Phase 1
  method, partition, fairness, tuning, budget, metric, statistics, exclusion,
  checkpoint-selection, dependency, and Problem-1 lineage contracts.
- Implemented and independently reviewed the G5 Task 4 SR-MAPPO, same-source
  MAPPO, and role-local PPO/IPPO comparison algorithms with behavior-bound
  rollout, exact checkpoint resume, and validity-aware GAE contracts.
- Rewrote and pushed the context-free G5 handoff so the next conversation
  starts at Task 5 with the frozen off-policy scope, protocol hazard, candidate
  grids, verification sequence, and M2 stop boundary.

## Pending Tasks

- Execute Task 5 of the persisted G5 plan: implement heterogeneous discrete
  MADDPG and IQL with TDD against the shared protocol.
- Implement later G5 algorithms, baselines, orchestration, statistics, smoke,
  pilots, and validation tuning only in the plan's declared order.
- Run G6/G7 formal and sealed experiments only after all prior gates pass.
- Generate G8 figures, tables, and thesis prose from locked summaries.

## Key Decisions

- `Second` is now the authoritative repository for all future second-problem
  code and documentation records.
- The current working branch is `codex/problem2-g5-pilot-freeze`.
- G1.1 was accepted at M1; G2 deterministic implementation now passes at M2
  with content and persistence push records verified. Candidate-branch reports
  remain untrusted until later branch-local verification.
- G3 heterogeneous-MARL implementation and acceptance passed at M2 on
  implementation commit `092b7f3e965a24979bac65c8304cd9d7dc142f73`; the
  canonical smoke and audit artifacts are recorded above. G4 is accepted at
  M2 as diagnostic support-probe mechanism evidence for onboard UAV pesticide
  scarcity. Its long-hash/provenance narrative discrepancy is reconciled. The
  G5 experiment contracts, shared algorithm protocol, exact on-policy stability
  differences, and Task 4 SR-MAPPO/MAPPO/PPO-IPPO implementations are frozen;
  Task 5 heterogeneous discrete MADDPG/IQL implementation is the next
  authorized work.
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

- The accepted G4 lineage is reconciled to one generator commit/tree/source-bundle
  tuple; the reconciliation report is recorded in
  `docs/audits/g4-lineage-reconciliation.md`.
- The candidate branch still contains unaccepted M2/M3/M4 wording and forbidden
  names; it was not merged or used as G2 evidence.
- The candidate branch contains M2/M3/M4 wording and forbidden-name mentions in
  its own docs/tests; the G1 audit records these as candidate-branch signals,
  not accepted maturity or implementation claims.
- `D:/Pycharm/Locust_rl` lacks Git history, so it cannot by itself provide a
  formal commit-level evidence chain.
- Engineering parameter sources remain incomplete: device manuals, field
  studies, expert confirmation, and source-value conversions are registered as
  pending G1 source records and still require independent verification.
- G4 demonstrates only development-probe onboard-pesticide resource activation
  and descriptive paired deltas; it does not support a mobile-treatment
  efficacy claim or any vehicle-inventory scarcity claim.
- No formal second-problem raw logs, validated tables, paired statistics, or
  locked figures exist in the repository evidence set.
- No claim is currently permitted that simulation outcomes reflect real
  deployment.
- Python cache files may still exist in the local working directory after tests,
  but `.gitignore` excludes them from GitHub evidence and commit boundaries.
- The host Python remains intentionally CPU-only for the G3 evidence lock. The
  isolated `.venv-g5` now contains the separately verified CUDA 12.6 wheel and
  must remain the G5 environment without mutating the Codex/Hermes host
  environment. Its exact G5 lock omits the legacy Pillow document dependency,
  so cross-gate full regressions continue in the host environment.

## Next Step

Execute Task 5 of
`docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md`: implement
heterogeneous discrete MADDPG and IQL with test-first development against the
accepted shared protocol. Keep pilots, validation tuning, formal jobs, and
sealed-test evaluation unauthorized until their later gates.
The highest maturity remains M2 implementation and scoped mechanism evidence.
Formal jobs, sealed-test evaluation, and thesis efficacy/superiority claims
remain unauthorized until their later gates.
