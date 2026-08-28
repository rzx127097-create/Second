# Project State

Last updated: 2026-08-28

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
- Current branch: `codex/problem2-dynamic-pest-model`.
- Current branch base at start of G0:
  `2643753855c385253951dfad2c225be0b09b7e00`
  (`origin/main`, commit message `docs: mark section 4.2 delivery complete`).
- Existing remote feature branch:
  `origin/feature/problem2-code-framework` at
  `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`.
- Current highest maturity: `M2` implementation and scoped mechanism evidence.
- Current gate: the user has required Problem 2 to inherit the complete
  Problem-1 dynamic pest environment. The approved design reopens G3-G5 before
  any G6 work: Holling-Tanner reaction-diffusion, dynamic wind advection, and a
  persistent decaying pesticide-effect field become mandatory defaults for all
  future primary experiments. The previous G5 linear-local-decrease outputs
  remain byte-preserved historical diagnostics and are not admissible as
  dynamic-environment pilot or formal evidence. G6 and G7 remain blocked until
  the dynamic implementation, renewed G3/G4 acceptance, fair G5 pilot, and new
  method/statistics freeze are committed, pushed, and verified.
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

## G5 Task 5: Heterogeneous Discrete MADDPG and IQL

Task 5 is implemented and reviewed at the existing `M2` maturity boundary.
It does not run pilots, validation tuning, formal jobs, sealed evaluation, or
support efficacy/superiority claims. The public flagship identity remains
`SR-MAPPO`; no HAPPO or `AG-SR-MAPPO` method was added, and pesticide remains
the only replenished resource.

Implementation scope:

- `OffPolicyEnvelope` extends the accepted behavior-bound `RoleBatch` with
  current/next structured centralized state, shared team reward, team/role
  validity, role identities, and vehicle candidate mapping while preserving
  on-policy envelope rejection and actor information isolation.
- `JointReplayBuffer` now stores off-policy envelopes and validates exact
  schema, ring layout, insertion position, size, defensive copies, masks, and
  RNG state before restoration mutation.
- MADDPG implements a shared UAV discrete actor, separate vehicle actor,
  centralized role-Q critics and matching targets, replay, soft target updates,
  masked straight-through Gumbel-Softmax, role-validity filtering, and masked
  deterministic evaluation.
- IQL implements shared UAV and separate vehicle Q/target-Q networks,
  role-local masked epsilon-greedy behavior, independent target schedules,
  replay/checkpoint state, legacy v1 trainer-state migration, masked bootstrap
  maxima, and epsilon-zero deterministic evaluation.
- `build_algorithm` constructs every frozen `c01-c04` candidate for
  `maddpg_mobile` and `iql_mobile` without changing the registries.

TDD and review evidence:

- Focused RED was a collection failure caused by the missing IQL module.
- Initial GREEN: `17 passed` focused off-policy tests; the first independent
  review found two Important issues for role validity and role-local target
  cadence.
- Fix round 1 added reproducing tests and closed both findings;
  `20 passed` focused and `185 passed` G5 tests were recorded.
- Scoped re-review found one Important legacy-checkpoint compatibility
  regression. Fix round 2 added explicit v1 migration and strict new-state
  validation; scoped re-review marked the finding addressed with no new
  Critical/Important issue.
- Three Minor observations remain deferred in the SDD ledger: replay-capacity
  exact-type validation, a stronger non-constant Gumbel-gradient assertion,
  and explicit replay ring/resume coverage.

Fresh controller verification on final content:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_off_policy_algorithms.py -q`:
  `22 passed`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_algorithm_protocol.py tests/g5/test_checkpoint_resume.py -q`:
  `27 passed`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 -q`: `65 passed`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g5 -q`: `187 passed`.
- Host `python -m pytest -q`: `486 passed in 187.37s`.
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts` exited `0`;
  `scripts/audit_g5_contracts.py` returned `status=pass`, validation and
  sealed access `false`, and actual unlock count `0`; `git diff --check`
  exited `0`.
- No pilot, validation scenario, formal job, sealed scenario, protected
  external asset, or Word file was accessed or modified.

Persistence status:

- Content implementation commit
  `caf4277ed1c178565f8bf3995d60871e24fe02d4`
  (`feat: implement heterogeneous maddpg and iql`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`.
- Review-fix commits `9b2518bf8795a071a909812f201a535a1e2979aa`
  (`fix: harden g5 off-policy validity and target cadence`) and
  `52baca35f2c8d6dd3892445fe686b8fa6cf95522`
  (`fix: preserve g5 iql checkpoint compatibility`) were pushed to the same
  branch. The report record is `9c617d3fcc302c323cd1bcd4e348f902f6f36c5c`.
- After the content chain push, local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all return
  `52baca35f2c8d6dd3892445fe686b8fa6cf95522`.

Task 6 is the next authorized work: implement the physical training/evaluation
adapter, formal metrics, and support controllers. G5 pilots and all later
validation/formal/sealed execution remain prohibited until their declared
tasks are completed in order.

## G5 Task 6 Context-Free Handoff

`HANDOFFG6.md` is the current context-free continuation record for the next
conversation. It supersedes the historical Task-5 instruction in
`HANDOFFG5.md` without deleting that provenance record. The handoff SHA-256 is
`64100B02435EC7591710BAE4D56A8D137581A509E996F193B36AF5E924040A96`.

Handoff content commit `96ec0f1a7e748c488eb7b7c83a14c648dae60b0a`
(`docs: add g5 task 6 handoff`) was pushed to
`origin/codex/problem2-g5-pilot-freeze`; local HEAD, upstream HEAD, and
`git ls-remote` matched this hash before the persistence-record commit.

It records the final Task-5 implementation/review/verification chain, the
current branch and three-way parity, the protected `_tmp_docx_assets/` path,
the M2 boundary, and the exact Task-6 files, interfaces, metric semantics,
TDD order, stop conditions, and persistence contract. Task 6 remains G5
implementation work; no pilot, validation tuning, formal job, or sealed-test
access is authorized. No external protected asset or Word file was modified
while creating this handoff.

## G5 Task 6: Physical Adapter, Metrics, And Support Controllers

Task 6 is implemented, independently reviewed, verified, and content-persisted
at the existing `M2` maturity boundary. It does not run a pilot, access
validation or sealed scenarios, queue a formal job, or support an efficacy,
superiority, significance, or deployment claim.

Implemented boundaries:

- `Problem2CooperativeEnv` reuses the accepted G2 road, physical motion,
  service-state, and pesticide-ledger components while emitting the verified
  G3 role observations and behavior-time masks. A sampled vehicle request slot
  and its mapping remain unchanged; deterministic road direction is recorded
  separately as physical execution detail.
- Adapter-owned reservation events record request ID, origin road state,
  selected service road node, sampled slot, and shortest feasible road-route
  length. Episode metrics separately accumulate this rendezvous distance and
  realized service travel, including route detours.
- `EpisodeMetrics` directly records pending/reserved waiting through the
  terminal boundary, completed-request wait, pesticide-disabled UAV-time,
  return UAV-time, positive effective spray steps, partial/zero service,
  transfer/inventory totals, conservation residual, and decision-only runtime.
- Primary outcomes require explicit finite initial/final pest totals. The
  registered denominator epsilon is frozen as `1.0e-12`; the strict G5 loader
  rejects missing, extra, non-finite, non-positive, or drifted values, and
  callers cannot override it.
- Deterministic evaluation reloads the strict partition contract before reset,
  denies validation/sealed access, deep-snapshots policy state, and restores it
  on success, mutation, reset failure, or action failure before returning the
  byte-identity proof.
- Fixed, rolling-A*, nearest, and urgency controllers use current observable
  request/road state only with deterministic ties and service feasibility.
  Fixed support enforces exact mobile-resource matching at construction; A*
  exposes an auditable frozen replanning cadence and agrees with Dijkstra on
  the tested graph panel.
- The two-stage schedule requires positive stage budgets summing exactly to
  the joint SR-MAPPO interaction budget and records both budgets in checkpoint
  ancestry under method ID `sr_mappo_two_stage`.

TDD and independent review evidence:

- Initial RED: two collection errors because the Task-6 evaluation and
  heuristic modules did not exist; initial focused GREEN: `20 passed`.
- Review fix round 1 reproduced `7 failed, 8 passed` for environment/metric
  cases and `7 failed, 10 passed` for controller cases, then closed deep
  policy restoration, strict partition reuse, A* cadence, and non-bypassable
  fixed-resource matching. Scoped re-review left only the missing numeric
  metric epsilon open.
- Review fix round 2 reproduced `3 failed, 5 passed`, froze and enforced the
  canonical epsilon, and returned `8 passed`; the scoped re-review marked the
  last finding addressed with no new Critical or Important breakage.
- Two Minor observations remain deferred in the SDD ledger for the later
  whole-branch review: fail-closed handling of an active A* route that becomes
  unreachable, and an environment-level fixed-controller integration test.

Fresh controller verification on content head
`044209c84803b0ab9e9c6ff51dddbca83ff03228`:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_environment_metrics.py tests/g5/test_heuristics.py tests/g5/test_g5_contracts.py -q`:
  `63 passed in 18.74s`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`:
  `290 passed in 46.35s`.
- Host `python -m pytest tests/g2 tests/g4 -q`:
  `178 passed in 95.16s`.
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts`: exit `0`.
- `.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py`:
  `status=pass`, all 17 fairness flags true, validation/sealed access false,
  actual unlock count `0`, and metric-contract SHA-256
  `c1761358f1bd4638ff879cc29acf9dac3c754e149f0d0fe2a4d51323ab6ec8bb`.
- `git diff 02b4b0fa2a842645bf7007596a19644b9664c193..HEAD --check`:
  exit `0`.

Persistence status:

- Content commits `a5918b76f8c11ee91dc5be1681776cf73ac42c8c`
  (`feat: add g5 environment metrics and support controllers`),
  `60486832ef7bb10e9b1c90a70b0c33d4f8197542`
  (`fix: harden g5 evaluation and support contracts`), and
  `044209c84803b0ab9e9c6ff51dddbca83ff03228`
  (`fix: freeze g5 reduction epsilon`) were pushed to
  `origin/codex/problem2-g5-pilot-freeze`.
- After the content push, local HEAD, upstream HEAD, and `git ls-remote` all
  returned `044209c84803b0ab9e9c6ff51dddbca83ff03228`.
- The user-owned `_tmp_docx_assets/` path remains untracked and untouched. No
  protected external asset, OSM input, first-problem file, output artifact, or
  Word file was modified.

The Task-7 content head before this state record is
`c609b8713ed9589b4a5f754dadcc1afa8a56d6cb`; this record persists its review,
verification, and manifest evidence. Pilots, validation tuning, formal
execution, and sealed access remain unauthorized.

## G5 Task 7: Experiment Families And Deduplicated Job Graph

Task 7 is implemented, independently reviewed, freshly verified, and persisted
at the existing `M2` maturity boundary. It generates planning manifests only;
it does not run pilots, access validation or sealed scenarios, queue formal
jobs, or support efficacy, superiority, significance, or deployment claims.

Implementation and contract boundaries:

- `src/problem2/experiments/{identity,families,matrix,ablation,sensitivity}.py`
  preserve the G1 serialization as an explicit intermediate and use its
  lowercase SHA-256 digest as the canonical training identity. Family-bound
  identities add `family|condition_id|protocol_hash|canonical_digest` without
  changing the base digest.
- The graph covers six scales, five formal training seeds, five frozen learning
  methods, the five required Problem-2 conditions, nearest/urgency heuristics,
  five remove-one groups, and five three-level algorithmic sensitivity axes.
  It contains exactly `375` unique jobs with decomposition
  `150 + 90 + 60 + 25 + 50`, plus `645` deterministic family references.
- The strict G5 loader consumes and hashes
  `configs/problem2/g5/{families,ablations,sensitivity}.yaml`. Registry drift,
  malformed identities, unsafe deduplication, and source Git unavailability or
  non-output source drift fail closed. The manifest source tuple is
  `source_commit=a868e6d5d3220aed1e128d052204a4ba74cb5969`,
  `source_tree_sha256=f058b0cc84d6b335fc2e3c57ae92d388ea505fc1e7107c0f228614015a832e6c`,
  and frozen protocol hash
  `63b8637ec0cb2d8cccde5e030e6b5d61ca5b812e075f5da3ac7c4f4a4c24bfe4`.
- Generated artifacts remain below
  `outputs/problem2_sr_mappo_v1/g5/manifests`. The tracked manifest hashes are:
  `development-smoke.json` `ff85a34467958ac58567730a537d5877103bb0fbe869e9e50cee9efc3222a210`;
  `pilot-manifest.json` `52f6fde87712df522d976137d05e7025f5e85243c61566e33895588e40447991`;
  `g6-training-jobs.json` `ff4d20a347be565f974d39ba24ec382b231d6def326243c06943bd81f2733553`;
  `g6-validation-evaluations.json` `4e57689500337d11f86da351ae65314500a6012286b671988f68b66fd3863936`;
  `g7-sealed-evaluations.json` `47ab883d64e932081d82be303b2a49303341ad5b7ea04bce8146a22309e59fe0`;
  `g7-analysis.json` `0e91e59df68046c79d0b274514fd453024f843eb4a314c218c846debae0e7129`;
  `manifest-summary.json` `328363aa284150a5e3f098d50b05e253992881f5f6b413445fc299bce375aa47`.

Fresh verification and review:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_experiment_matrix.py -q`:
  `8 passed`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g5 -q`: `233 passed`;
  `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`:
  `298 passed`; host `python -m pytest tests/g2 tests/g4 -q`:
  `178 passed`.
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts`: exit `0`;
  `scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed access
  false, actual unlock count `0`; `git diff --check`: exit `0`.
- Two independent generator runs produced seven byte-identical files; all
  `375` canonical digests recompute, all `645` references resolve, the exact
  decomposition holds, and scans contain no `30000`, `30099`,
  `sealed_scenario`, or `evaluation_results` payload. No pilot, validation,
  formal, or sealed execution occurred.
- Independent Task 7 review and two scoped fix re-reviews closed all
  Critical/Important technical findings. The only deferred item was the
  required project-state persistence, completed by this record.

Persistence status:

- Task 7 content and correction commits were pushed without force-push across
  the range `82e5775..c609b871`; the content head persisted by this record is
  `c609b8713ed9589b4a5f754dadcc1afa8a56d6cb`.
- Local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all match
  the state-record commit after this document update is pushed.
- The user-owned `_tmp_docx_assets/` path remains untracked and untouched. No
  protected external asset, OSM input, first-problem file, or Word file was
  modified.

## G5 Task 8: Orchestration And Evidence Validation Acceptance Record

Task 8 is accepted at M2 after independent scoped review and fresh controller
verification. It establishes the append-only orchestration, artifact schemas,
fail-closed evidence validation, recovery, quarantine, and sealed-lock guards
required before any G6 formal execution. It did not run pilots, formal jobs,
validation tuning, or sealed evaluation, and it does not support efficacy,
superiority, or deployment claims.

Implementation boundaries now persisted:

- JSONL ledger replay/register requires legal transitions, exclusive leases,
  same-identity retry, stale drift handling, and complete required/optional
  SHA-256/SHA-1 provenance formats.
- Raw and validated evidence recomputes both Task 7 training identity and the
  scenario-bound evaluation identity; callers cannot disable identity checks.
  Metric/resource/action/counter/partition/terminal and artifact hash/path
  checks fail closed, while quarantine preserves exact source bytes.
- G6/G7 preflight is read-only and execution-blocked at G5. Registry hashes
  require the exact frozen Task 7 key set, output confinement is bound to this
  repository's configured root, malformed manifests fail closed, and numeric
  sealed scenario IDs/access flags are rejected while the declarative sealed
  skeleton marker remains allowed.

Fresh verification:

- Final scoped review `bb81a7d..c62c9a8`: clean; no Critical, Important, or
  actionable Minor findings. Focused independent probes: `TASK8_PROBES_PASS`.
- `python -m pytest tests/g5/test_orchestration_and_validation.py
  tests/g5/test_sealed_guards.py -q`: `60 passed`.
- `python -m pytest tests/g3 tests/g5 -q`: `358 passed`.
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed`.
- `python scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed
  access false, actual unlock count `0`.
- `python -m compileall -q src scripts`, `git diff --check`, and all eight
  public CLI `--help` calls: passed.
- Sealed lock SHA-256 remained
  `78c9caa7d432f56f91b67195eb413eddab4e9f84c9fd214eb7a9373f48a73226`; no
  queue was created and no sealed data was read.

Persistence status:

- Task 8 content and corrective commits from `c22d5b2` through
  `945dc97badafbcbfcc131cb50ea8e20d589c840e` were pushed without force-push
  to `origin/codex/problem2-g5-pilot-freeze`.
- Before this state-record commit, local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all matched
  `945dc97badafbcbfcc131cb50ea8e20d589c840e`.
- The protected user-owned `_tmp_docx_assets/` path remains untracked and
  untouched. No protected external asset or sealed output was modified.

Task 9 is accepted and persisted at M2. The next authorized work is Task 10
smoke acceptance. Pilot execution, validation tuning, G6 formal jobs, and G7
sealed evaluation remain unauthorized until the declared gate order permits
them.

## G5 Task 9: Statistics And Mechanism Summaries Acceptance Record

Task 9 is accepted at M2 after two independent scoped review rounds and fresh
controller verification. The implementation provides pure deterministic
convergence, hierarchical paired bootstrap, Holm adjustment, complete-interval
equivalence, mechanism sign-coherence, and ordered negative-result diagnosis
helpers. It consumes validated row mappings only; the library opens no files,
reads no sealed data, filters no observations, and does not run experiments.

Implementation and boundary fixes:

- Content commits `5b8064c61391d2a10ad51f5a76d6d573bba9e2bc`,
  `c56fc3d`, and `f18d71dba97fd10218082feb86b4f1f4bec769ef` implement the
  frozen statistics interfaces and close review findings for explicit A-B
  direction, finite/censoring semantics, typed mechanism metrics and scale
  coherence, ordered diagnosis, Holm/equivalence validation, and fail-closed
  CLI provenance/path boundaries.
- CLI adapters require `validated: true`, `provenance.status=validated`, and
  `provenance.partition=development`; they reject raw/sealed path tokens before
  input or output I/O and confine explicit paths to the frozen output root.
- Method-form paired rows require an explicit ordered `method_order`, preserving
  the registered A-B estimand. Mechanism summaries require the mobile/fixed
  method pair and report direct scenario, training-seed, scale, and aggregate
  coherence without causal-mediation language.

Fresh verification:

- `python -m pytest tests/g5/test_statistics.py -q`: `12 passed`, run twice;
  repeated adapter JSON outputs were byte-identical.
- `python -m pytest tests/g3 tests/g5 -q`: `370 passed`.
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed`.
- `python scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed
  access false, actual unlock count `0`.
- Both Task9 CLI `--help` commands, `python -m compileall -q src scripts`,
  and `git diff --check` passed. Scoped reviews of `ed94abb..5b8064c`,
  `5b8064c..c56fc3d`, and `c56fc3d..f18d71d` closed with no open
  Critical/Important findings.

Persistence status:

- Task9 content and plan commits through
  `47c4ebb17e113acb0171b7aa902893b2fdb3c8a0` were pushed to
  `origin/codex/problem2-g5-pilot-freeze`.
- Before this state-record commit, local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all matched
  `47c4ebb17e113acb0171b7aa902893b2fdb3c8a0`.
- State-record commit `408da43ee8f9e39162fc9f8e6b0bd54903576517` was pushed with
  parity; the subsequent persistence synchronization commit
  `03deaa733a008146accd27dc3bdb0105918bdf21` was also pushed successfully.
- No pilot, formal training, validation tuning, sealed evaluation, or protected
  external asset access occurred. The user-owned `_tmp_docx_assets/` path
  remains untracked and untouched.

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
- Implemented and independently reviewed G5 Task 5 heterogeneous discrete
  MADDPG/IQL with strict off-policy replay, role-valid updates, deterministic
  evaluation, and checkpoint compatibility.
- Implemented and independently reviewed G5 Task 6 physical environment,
  direct metric, partition, evaluation-freeze, fixed/A*/nearest/urgency, and
  two-stage budget-ancestry contracts; content commits are pushed at M2.

## Pending Tasks

- Task 7 is complete and persisted: the exact experiment families,
  configuration diffs, and deduplicated 375-job graph are recorded below
  `outputs/problem2_sr_mappo_v1/g5/manifests`.
- Task 8 is complete and persisted: append-only orchestration, strict evidence
  schemas/validation, recovery, quarantine, and sealed-lock guards are recorded
  in `src/problem2/`, `scripts/`, tests, and the Task 8 report.
- Task 9 is complete and persisted: deterministic convergence, paired
  statistics, multiplicity correction, equivalence, mechanism summaries, and
  ordered diagnosis are recorded in `src/problem2/statistics/`, CLI adapters,
  tests, and the Task 9 report.
- Task10 smoke and Task11 development pilot/candidate freeze are complete and
  persisted. Execute only Task12 validation tuning, selected-configuration
  development refit, and final G5 freeze from the persisted plan.
- Keep the frozen candidate, budget, statistics, and partition contracts
  immutable while Task12 performs its one-way validation access.
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
  differences, five learning algorithms, and Task-6 environment/metric/support
  controllers and Task-7 experiment-family/job-graph manifests are frozen at
  M2. The reduction denominator epsilon is contract owned at `1.0e-12`; Task 8
  orchestration and evidence-validation implementation is accepted, and Task 9
  statistics/mechanism summaries are accepted at M2. Task10 smoke and Task11
  development-pilot/candidate-freeze acceptance are complete. Task12
  validation tuning and final G5 freeze are the next authorized work. No G6
  formal or G7 sealed execution is authorized by this record.
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

## G5 Task 10: Shared CPU/CUDA Smoke Acceptance Record

Task10 is accepted at M2 as a development-only engineering smoke gate. The
runner binds the algorithm to `method`, rejects non-development training seeds
and validation/sealed partitions, fails closed on contract/preflight errors,
and requires uninterrupted policy/metric/diagnostic digests for resume
equivalence. All smoke manifests use `g5-smoke-artifact-v1` with method,
algorithm, condition, partition, seed, provenance, and artifact hashes.

Fresh verification:

- `python -m pytest tests/g5/test_end_to_end_smoke.py -q`: `15 passed`.
- CPU smoke command with `--all-methods --all-condition-types`: `85 jobs`,
  `status=pass`.
- CUDA smoke command from the isolated G5 environment: `5 jobs`,
  `status=pass`; preflight recorded the RTX 4060 Laptop GPU, Torch `2.13.0+cu126`,
  CUDA `12.6`, deterministic flags, and non-zero peak memory for every method.
- Persisted audit status: `smoke-audit.json` `pass/85`,
  `smoke-audit-cpu.json` `pass/85`, and `smoke-audit-cuda.json` `pass/5`.
- Audit of `outputs/problem2_sr_mappo_v1/g5/smoke`: `85` job directories,
  homogeneous schema and identity fields, hash/path consistency, and
  `validation_accessed=false`, `sealed_accessed=false`,
  `battery_replenishment_enabled=false` for every manifest.
- `python scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed
  access false, `actual_unlock_count=0`; `compileall` and `git diff --check`
  passed.

Review and persistence:

- Scoped Task10 review and fix review closed all runtime findings; the final
  audit rerun corrected the fail-closed probe files before persistence.
- Content and smoke-artifact commits through
  `dc6ceab29bedcba9936617d6022fae37b10f2ee5` were pushed to
  `origin/codex/problem2-g5-pilot-freeze` without force-push. Local HEAD,
  upstream HEAD, and `git ls-remote` all match this hash before this state
  record.
- No validation scenario, sealed scenario, formal training job, or protected
  external asset was accessed. `_tmp_docx_assets/` remains untracked and
  untouched.

Task10 does not raise maturity above M2 and does not authorize formal claims.

## G5 Task 11: Pilot-Freeze Acceptance Record

Task11 is accepted at M2. The `problem2.training.pilot` module expands an exact
510-training-job development matrix (`5 x 17 x 2 x 3`) over the two required
scales, five methods, 17 conditions, and three development training seeds. Each
training task covers the 20 development scenarios `10000-10019`, producing
10,200 descriptive episode records. It preserves scale/scenario identity
through the Task10 runner, aggregates conservative runtime, applies the frozen
budget rule, and freezes four hashed validation candidates per learning method
before validation access. Candidate freezing contains validation IDs only as a
hashed panel definition; it does not read validation scenario content.

Acceptance and verification:

- Full pilot returned `status=pass`, `job_count=510`, `episode_count=10200`,
  and `failures=0`; every job directory contains checkpoint, manifest, summary,
  and training log files.
- Frozen budget: `200000` interactions, checkpoint interval `10000`, checkpoint
  count `20`, projected slowest runtime `0.7708476562500424` hours.
- Candidate manifest: exactly 20 content-hashed candidates, four per learning
  method, with the hashed 50-ID validation panel and frozen selection rule.
- Final artifact SHA-256 hashes (also recorded in
  `docs/audits/g5-task11-pilot-freeze-implementation.md`) are:
  `pilot-episodes.jsonl` `7609183B3B8945BC019F63F361C5FEBE7D00E9E7E4E8042BB07530A9C013DE72`,
  `pilot-audit.json` `4A14FE3B3518ECD0E864DDD79FADFCE7311E829BB1E505E76925AE162EF58CF2`,
  `pilot-artifact-manifest.json` `1B757397A28240C567CBADC5AD56B64C533E316558CE2924935C4D33B1ACC61E`,
  `pilot-budget.json` `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`,
  and `validation-candidates.json`
  `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`: `402 passed`;
  `python -m pytest tests/g2 tests/g4 -q`: `178 passed`;
  `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_pilot_freeze.py
  tests/g5/test_end_to_end_smoke.py -q`: `32 passed`.
- `python scripts/audit_g5_contracts.py`: `status=pass`,
  `actual_unlock_count=0`; compileall and diff check passed.
- `python scripts/validate_g5_artifacts.py --root outputs/problem2_sr_mappo_v1/g5 --dry-run`:
  dry-run only, no jobs executed.
- Refreshed Task10 smoke audits: CPU/main `pass/85`, CPU `pass/85`, CUDA
  `pass/5`; all 85 manifests bind source commit
  `33ba716aacedeff4e90a6d6f604f103732a970fd` and retain false boundary flags.
- All pilot records, nested training results, candidate manifests, and audits
  prove `validation_accessed=false`, `sealed_accessed=false`, and
  `battery_replenishment_enabled=false`; `actual_unlock_count=0`.

Persistence:

- Task11 implementation commit
  `b11298b39d7996a2f46d0c98e9dec774b18a96b4`, boundary hardening commit
  `6394a677ac422e2f6fb215d43bd52e64cebbac2b`, and smoke provenance refresh
  `74a3fef219e507d5e5b57f57a4bf8ed86620480c` and final provenance hardening
  `33ba716aacedeff4e90a6d6f604f103732a970fd` are pushed to
  `origin/codex/problem2-g5-pilot-freeze`; the full pilot evidence was
  generated against that source commit.
- Pilot evidence content commit `34f0941ca1d4d167c65e234e8313f421b05f3eaa`
  was pushed to `origin/codex/problem2-g5-pilot-freeze`. Fresh verification
  bound to that evidence returned pilot artifact verification `pass`,
  32 focused Task11 tests passed, 178 G2/G4 regression tests passed, CPU
  smoke `pass/85`, CUDA smoke `pass/5`, and all 510 pilot job manifests passed
  the required provenance/boundary scan. Local, upstream, and
  `git ls-remote` matched `34f0941` before this state-record commit.
- This state-record persistence commit is the final Task11 synchronization;
  after it, local, upstream, and `git ls-remote` hashes must match before
  Task12 begins.

No synthetic records, smoke records, validation tuning, G6 formal jobs, or G7
sealed evaluation were substituted for the pilot evidence. Task12 is the next
authorized G5 activity: validation tuning may consume the frozen 20-candidate
manifest on `20000-20049` only under its equal-budget and immutable-candidate
contract. G6 formal jobs and G7 sealed evaluation remain unauthorized.
The highest maturity remains M2 implementation and scoped mechanism evidence.
Formal jobs, sealed-test evaluation, and thesis efficacy/superiority claims
remain unauthorized until their later gates.

## Task11-to-Task12 Session Handoff Record

The context-free continuation document is `HANDOFF_TASK12.md`. It records the
accepted Task11 scope and evidence, exact Task12 plan and stop conditions,
protected paths, working-tree exclusions, validation/sealed boundaries, and
the implementation and provenance pitfalls observed during Task11 closure.

Persistence and integrity:

- Handoff content commit
  `08a66f1b74e5667c1730d68c41082854f53aa398`
  (`docs: add Task12 context-free handoff`) was pushed to
  `origin/codex/problem2-g5-pilot-freeze`.
- Before this persistence record, local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g5-pilot-freeze` all
  returned `08a66f1b74e5667c1730d68c41082854f53aa398`.
- `HANDOFF_TASK12.md` SHA-256 is
  `4F8C230CB198141C30F77D469CB78CE7C9A2123E36392EBC72D3D02AE1FED9AA`.
- All ten mandatory startup references named by the handoff exist; the five
  recorded Task11 core artifact hashes match the persisted files; G5 contract
  audit remains `status=pass`, `validation_accessed=false`,
  `sealed_accessed=false`, and `actual_unlock_count=0`; `git diff --check`
  reports no content error.

Known Task12 entry issue:

- `verify_pilot_artifacts` currently compares the recorded Task11 generation
  commit `33ba716aacedeff4e90a6d6f604f103732a970fd` with the repository's current
  HEAD. The check passes at generation time but fails after correct evidence
  and documentation persistence advances HEAD. The generation commit remains
  an ancestor and the frozen `src`/`scripts`/`configs`/`docs/evidence`/lock
  scope is unchanged through the Task11 persistence commit. Task12 must add a
  failing regression test and repair the lineage-verification semantics before
  final `freeze_g5 --check-only`; it must not rewrite the evidence manifest to
  claim generation at a later commit.

This handoff does not authorize G6 or G7. Task12 remains the only next
authorized activity. After this persistence commit is pushed, local,
upstream, and remote hashes must agree before a new conversation begins work.

## Task12 Pre-Validation Authorization

Task12 implementation reached the pre-access boundary on 2026-08-27. The
candidate and budget artifacts remain byte-identical to the Task11 freeze:

- validation candidates SHA-256:
  `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`;
- pilot budget SHA-256:
  `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`;
- sealed lock SHA-256:
  `78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226`,
  with maximum unlock count `1` and actual unlock count `0`.

The Task11 pilot verifier lineage defect is repaired by requiring the recorded
generation commit to be an ancestor of the current commit and by rejecting
drift in the immutable contract scope. Task12 now has a validation-only,
action-driven pest metric adapter over the frozen G2 road cache, exact
candidate-ID propagation, scale-dependent `d2/d3/d4` observation dimensions,
an immutable validation-access ledger, the frozen mechanical selection rule,
and fail-closed G6/G7 count construction. Validation authorization is enabled
for IDs `20000-20049`; `validation_accessed` remains false until the first
persisted validation row. Sealed access remains forbidden.

Pre-access verification: Task12 focused tests `14 passed`; authorization and
partition regression tests `18 passed`; candidate, budget, and sealed-lock
hashes match the values above; `git diff --check` has no content error. This is
an implementation and governance transition only. It contains no validation
result, no G6 job, no sealed content, and no efficacy or superiority claim.

## G5 Task 12: Validation Tuning And Final Freeze

Task12 is accepted at G5 as an implementation, validation-process, and
development-refit freeze while the highest research maturity remains `M2`.
The content freeze commit is
`9965860ca8d92678d01240c57be4dc887f779760`
(`feat: freeze g5 fair-pilot experiment system`), pushed to
`origin/codex/problem2-g5-pilot-freeze`. Before this state-record commit,
local HEAD, upstream HEAD, and `git ls-remote` all returned that hash.

Task12 evidence and boundaries:

- Canonical physical candidate training completed `60` identities: five
  methods x four frozen candidates x three development training seeds at
  `g30x50_d4`, with `200000` interactions per identity and all terminal
  manifests passing.
- Validation tuning evaluated the 20 byte-locked candidates on the fixed
  validation panel `20000-20049` with three training seeds, producing exactly
  `3000` action-driven rows and zero technical failures. The candidate and
  budget bytes were locked before the first validation row; sealed content was
  never accessed.
- Every candidate had `success_probability=0.0`. This is a weak/negative
  validation diagnosis retained in the evidence set, not a formal ranking,
  efficacy result, superiority result, or statistical conclusion.
- Mechanical selections are `sr_mappo_mobile=c02`, `mappo_mobile=c01`,
  `ippo_mobile=c01`, `maddpg_mobile=c04`, and `iql_mobile=c03`.
- Selected-configuration development refit completed `510` physical jobs and
  `10200` development scenario-reference rows, with validation and sealed
  access false in the refit records.
- Frozen G6 manifests contain `150` base jobs and `375` unique jobs, with
  `375000` planned G6 validation identities. G7 contains `42500` planned
  sealed evaluation identities and no sealed scenario content or results.
- The sealed lock remains unchanged at maximum unlock count `1` and actual
  unlock count `0`; pesticide is the only replenished resource and battery
  replenishment remains disabled.

Fresh verification on the pushed content commit:

- `.venv-g5/Scripts/python.exe -m pytest tests/g5 -q`: `428 passed`.
- `python -m pytest -q` in the documented host regression environment:
  `727 passed`.
- `.venv-g5/Scripts/python.exe -m compileall -q src scripts`: exit `0`.
- `.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py`: `status=pass`,
  `sealed_accessed=false`, `actual_unlock_count=0`.
- `.venv-g5/Scripts/python.exe scripts/validate_g5_artifacts.py --root
  outputs/problem2_sr_mappo_v1/g5 --dry-run`: dry-run completed with no jobs
  executed.
- `.venv-g5/Scripts/python.exe scripts/freeze_g5.py --check-only`:
  `status=pass`, with validation rows `3000`, refit jobs/episodes `510/10200`,
  G6 `150/375`, G7 `42500`, and sealed access false.
- `git diff --check`: no content errors.

The isolated G5 environment's exact lock intentionally omits legacy Chapter
4.2 document-rendering dependencies, so its repository-wide collection
command reports missing `PIL`/`matplotlib`; the cross-gate full regression was
therefore run in the documented host environment and passed `727` tests.
This environment issue does not affect the G5 implementation suite or any
Task12 evidence artifact. No protected external asset, OSM input, sealed
scenario, G6 formal job, or G7 sealed evaluation was modified or executed.

G6 is the next authorized gate only after this state-record persistence commit
is pushed and parity is rechecked. Until then, no formal efficacy, superiority,
statistical-significance, or real-deployment claim is permitted.

## G6 Readiness Audit And Session Handoff

On 2026-08-28, a read-only G5-to-G6 readiness audit was completed and persisted
in `HANDOFF_G6_READINESS.md`. The initial handoff commit was
`01a2f9b9ab9a62931b67b33256f108b8cfe46ef7`; the final handoff clarification
commit is `3594b13c3661c8dcb1325c655532bd71d4b13170` (`docs: clarify validation
access handoff`), pushed to `origin/codex/problem2-g5-pilot-freeze`. After that
push, local HEAD, upstream HEAD, and `git ls-remote` all matched the final
handoff commit.

For completeness, the preceding Task12 persistence commit is explicitly
recorded here as `93fa732c60196e3ffb3b59d035a80edb1a7db138`
(`docs: record g5 freeze persistence`). After that persistence push, local HEAD,
upstream HEAD, and `git ls-remote` all matched `93fa732...` before the handoff
commits above.

The audit confirms that G5 Task12 evidence is present and that no G6 formal job,
G7 sealed evaluation, or sealed scenario content was accessed. It also confirms
that G6 formal execution is not ready: `run_g6_jobs.py` and
`resume_g6_jobs.py` remain blocking stubs; the G6 evaluator hash is bound to
that stub; the current preflight does not cover the complete G6 entry contract;
the G6 manifest lacks frozen scheduler/storage/GPU estimates; and the real
ledger/recovery/validation execution loop is not connected. Selected-refit
condition semantics also require a focused ruling before the G5 freeze can be
trusted for formal execution.

The next authorized work is G6 readiness remediation. It must reopen and
re-freeze G5 after implementing and testing the real runner, recovery path,
validation evaluator, complete preflight, resource estimates, and condition
semantics. No formal G6 execution may begin until the new G5 content and
persistence commits are pushed, their hashes are recorded, and fresh parity and
all required audits pass. The current highest maturity remains `M2`.

## Dynamic Pest Model Design And Gate Reopening

On 2026-08-28, the user required every future Problem-2 primary experiment to
run in the dynamic pest environment inherited from Problem 1 and approved the
complete Holling-Tanner design. Static pest behavior is now restricted to an
explicitly labeled development diagnostic and cannot be used for a primary,
formal, or sealed result.

The approved written design is
`docs/superpowers/specs/2026-08-28-problem2-dynamic-pest-model-design.md`.
It freezes a self-contained Problem-2 implementation route for Holling-Tanner
reaction-diffusion, dynamic wind advection, radius-weighted pesticide effect
and decay, deterministic scenario/RNG identity, action-complete ecological
observations, signed ecological reward, and negative reduction-rate support.
It also requires all algorithms, controllers, ablations, sensitivities,
scales, G6 jobs, and G7 evaluations to share byte-identical dynamic scenarios.

Problem-1 lineage is read only at commit
`1ca9e5ccc5f77ed775cd2b607dd70d635720accf`. The design records exact committed
blob IDs for the dynamics, subsystem, environment, and settings sources and
excludes the protected repository's current uncommitted reward-sensitivity
work. No protected external file was modified.

Persistence and verification:

- Isolation-preparation commit
  `c362c3c58bcc754a30389c085d33273ace1f85f8` (`chore: ignore local worktrees`)
  was pushed to `origin/codex/problem2-g5-pilot-freeze`.
- Design content commit
  `d924f38259463344d8b9f1b9200d7fd3e2f2bd3c`
  (`docs: design dynamic pest integration`) was pushed to
  `origin/codex/problem2-dynamic-pest-model`; local, upstream, and
  `git ls-remote` hashes all matched before this state record.
- Fresh authoritative-directory baseline: `python -m pytest -q` returned
  `727 passed` in `494.42 s`.
- `git diff --cached --check` passed before the design commit.
- All four recorded Problem-1 source blobs resolved exactly at the declared
  source commit.
- A linked-worktree baseline was rejected because frozen historical manifests
  bind the authoritative absolute source root and byte hashes, while Windows
  checkout line-ending conversion changed frozen bytes. The empty linked
  worktree was removed after verification; the dedicated branch continues in
  the authoritative checkout so historical evidence is not rewritten.

The highest maturity remains `M2`. The next authorized activity is user review
of the written design, followed by an implementation plan. Production-code
implementation must use test-driven development. G3-G5 are reopened for the
new ecological semantics; G6 formal execution and G7 sealed access remain
unauthorized.

## Dynamic Pest Implementation Plan Approval

On 2026-08-29, the user confirmed the approved design and authorized continued
work with dynamic ecology as the default environment for every future primary
experiment. The executable TDD plan is
`docs/superpowers/plans/2026-08-29-problem2-dynamic-pest-model.md`.

The plan defines ten independently verifiable tasks covering the versioned
ecology and source-lineage contracts, independent Holling-Tanner numerical
gold tests, persistent pesticide effect, scenario-owned dynamic wind,
deterministic scenario identities, complete ecology/RNG state restoration,
accepted physical spray-event integration, fixed-size observation semantics,
signed reward and dynamic endpoint validation, fail-closed experiment
defaults, the `dynamic_pest_v1` output namespace, and bounded G3-G5
revalidation.

Plan self-review found complete coverage of the approved design, consistent
cross-task type names, no unresolved placeholder, and no task that overwrites
historical `outputs/problem2_sr_mappo_v1/g5` evidence. The plan explicitly
keeps validation refreezing, G6 formal execution, G7 sealed access, paired
formal statistics, and thesis efficacy claims outside this implementation
phase.

Persistence and verification:

- Plan commit `1560d1b250678e89fd3245c46dff5fd18c196aa1`
  (`docs: plan dynamic pest implementation`) was pushed to
  `origin/codex/problem2-dynamic-pest-model`.
- Local HEAD, upstream HEAD, and `git ls-remote` all matched
  `1560d1b250678e89fd3245c46dff5fd18c196aa1` after the push.
- `git diff --check` passed for the plan.
- The plan contains checkbox steps, exact file ownership, interfaces, RED and
  GREEN commands, expected outcomes, commit boundaries, a coverage review,
  and a placeholder scan.
- No production code, protected external repository, OSM source, historical
  G5 output, validation scenario, or sealed scenario was modified or accessed
  during plan creation.

The next authorized activity is TDD implementation of the plan on
`codex/problem2-dynamic-pest-model`. The highest maturity remains `M2`;
G3-G5 remain reopened for dynamic semantics, G6 stays blocked, and the G7
sealed unlock count remains `0`.
