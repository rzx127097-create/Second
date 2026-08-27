# SDD ledger — plan: docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md

Workspace: C:/Users/RZX/Documents/ChatGPT/Second
Branch: codex/problem2-g5-pilot-freeze
Task 1: complete (commits a0d2d64..727ebb8, persisted G4 lineage reconciliation)
Task 2: complete (commits 082a040^2..082a040, persisted G5 Phase 1 contract freeze)

## Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Task 2 | Task 3 | G5 protocol hashes, method IDs, partitions, and dependency lock | Clean: Task 3 binds checkpoint provenance to the frozen Task 2 contracts. |
| Task 3 | Task 4 | HeterogeneousAlgorithm, RoleBatch, shared networks, masked actions, checkpoints | Clean: Task 4 implements on-policy adapters against these shared interfaces. |
| Task 3 | Task 5 | JointReplayBuffer, shared networks, masked distributions, checkpoints | Clean: Task 5 implements off-policy algorithms without redefining shared persistence. |
| Task 3 | Task 6 | role-local transition/evaluation contract and checkpoint ancestry | Clean: Task 6 adapts the verified environment and two-stage ancestry to Task 3 interfaces. |
| Task 3 | Task 8 | atomic checkpoint, provenance hashes, recovery state | Clean with ruling below on previous-checkpoint sibling naming. |
| Task 3 | Task 10 | protocol conformance and checkpoint round trip | Clean: Task 10 consumes, but does not redefine, Task 3 behavior. |
| Task 3 | Task 3 | listed files, APIs, tests, G3 compatibility | Clean except the previous-checkpoint filename is unspecified. |

Task 3: Ruling: retain the previous valid checkpoint at the deterministic same-directory sibling `<checkpoint>.previous`; rotate it only after the new temporary checkpoint reloads and its SHA-256 is verified, then atomically replace the destination. This makes the recovery path auditable. Cost if wrong: a later naming contract would require a compatibility lookup/migration.
Task 3: in progress (base 082a040207b83f3119e4b1e89118235e3cd470a3)
Task 3: implementer complete (commit 7254c1f74aaa55c3113d01d2325588e39a742e38); task review pending.
Task 3: Ruling: G5 checkpoint provenance must have exactly `source_commit` (40 lowercase hexadecimal Git SHA-1), `source_bundle_sha256`, `config_hash`, `protocol_hash`, and `ancestry_hash` (each 64 lowercase hexadecimal SHA-256); save and load both reject omission, extras, invalid format, or drift. This implements the design's source-commit/source-bundle and Task 3's source/config/protocol/ancestry constraints. Cost if wrong: later Task 4-12 checkpoint producers and readers need a one-time field migration.
Task 3: fix round 1/5 started (two Important integrity findings and one Minor defensive-copy finding from review).
Task 3: fix round 1/5 complete (3 addressed; commits 7254c1f74aaa55c3113d01d2325588e39a742e38..3f5f218ff6cde06d75942c5b7b6c8e2df888e8b5); scoped re-review pending.
Task 3: fix round 2/5 started (scoped re-review leaves one Important: direct RoleBatch construction still permits unbound action masks).
Task 3: fix round 2/5 complete (1 addressed, 0 open; commit 618afdcff25cb4853507a7cd10f0c8e0bd9699c1; scoped re-review pending).
Task 3: complete (commits 7254c1f74aaa55c3113d01d2325588e39a742e38..618afdcff25cb4853507a7cd10f0c8e0bd9699c1, review clean).
Task 4: in progress (base 5d4c0b89d15e808fba64adc44ec687a95e7bc3c8; implementation present in working tree; independent review pending).
Task 4: fix round 1/5 started (five Important protocol/config/checkpoint/numeric findings and two Minor determinism/metrics findings; review brief: task-4-review-round-1.md).
Task 4: fix round 1/5 partial (candidate selection, clip wiring, envelope-only boundary, resume equivalence, finite rollback, and shuffle addressed; scoped re-review leaves three Important and one Minor class).
Task 4: fix round 2/5 started (complete team reward/validity/metadata/shape semantics, nested pre-mutation state validation, IPPO metric aggregation, and public protocol export; brief: task-4-review-round-2.md).
Task 4: fix round 2/5 partial (envelope semantics, finite ingest, prevalidation ordering, IPPO aggregation, and public protocol closed; scoped re-review leaves invalid-sample GAE contamination and trainer type-exact validation).
Task 4: fix round 3/5 started (validity-aware GAE trace boundaries and type-exact trainer checkpoint validation; brief: task-4-review-round-3.md).
Task 4: fix round 3/5 complete (invalid-sample GAE and type-exact trainer state addressed; scoped re-review Ready with no Critical/Important findings).
Task 4: implementation and task review complete; fresh controller verification passed (G5 165, G3 65, host full 464, contract audit pass, compileall/diff check exit 0); content commit pending.
Task 4: complete (content commit 0593f17edad38a892115a375c1ac836cf8081e19 pushed with verified remote parity; persistence record pending).
Task 4: persistence complete (record commit dc8fbb09852370f6d99dee4aa34e4ed9f2d69bb4 pushed; local, upstream, and remote heads match; Task 5 is next).

## Task 5 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Task 3 | Task 5 | `HeterogeneousAlgorithm.observe`, `RoleBatch`, `JointReplayBuffer` | Conflict: the abstract ingest accepts only `OnPolicyEnvelope`, replay accepts only `RoleBatch`, and neither carries current/next structured global state for centralized role-Q critics. Task 5 must add a strict typed off-policy envelope while preserving on-policy rejection. |
| Task 3 | Task 5 | `JointReplayBuffer.load_state_dict` | Review target: validate exact keys/types, every row, sparse ring invariants, RNG state, and defensive copies before mutating live state; deterministic sampling after resume is required. |
| Task 2 | Task 5 | frozen `maddpg_mobile` and `iql_mobile` candidates | Clean: the registry supplies four immutable candidates per method; factory wiring must consume them without changing the registry. |
| Task 4 | Task 5 | shared role actions/masks, candidate mapping, checkpoint protocol | Clean: off-policy methods must use the same behavior-bound role contract and preserve on-policy behavior and G3 compatibility. |
| Task 5 | Task 5 | listed algorithm/network/trainer modules and focused tests | Clean: tests precede production code; no Task 6 environment/controller or pilot work is authorized. |

Task 5: Ruling: resolve the protocol hazard with a strict `OffPolicyEnvelope` carrying the exact behavior-bound `RoleBatch`, structured current/next critic state, shared team reward, role/team validity, masks, identities, and vehicle candidate mapping; widen only the abstract annotation/dispatch boundary and keep on-policy implementations rejecting it. Cost if wrong: later environment collection and centralized critics need a one-time transition migration.
Task 5: fix round 1/5 started (two Important findings: MADDPG role-validity filtering and IQL role-local target cadence).
Task 5: minor (deferred): replay capacity exact-type validation, stronger non-constant Gumbel gradient assertion, and explicit replay ring/resume test coverage.
Task 5: fix round 1/5 complete (2 addressed; commit 9b2518bf8795a071a909812f201a535a1e2979aa; scoped re-review found one Important checkpoint-compatibility regression).
Task 5: fix round 2/5 complete (1 addressed, 0 open; commit 52baca35f2c8d6dd3892445fe686b8fa6cf95522; scoped re-review clean).
Task 5: complete (commits caf4277..52baca3, review clean with 3 deferred minors; content chain pushed at 52baca35f2c8d6dd3892445fe686b8fa6cf95522; persistence record 59877f6b440da53b83647a6715390a02c6e06372 pushed with final parity).

## Task 6 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| G2 | Task 6 | `EpisodeState`, stored directional masks, road motion, service events, pesticide ledger | Conflict: G2 vehicle actions are physical directions while G3/G5 vehicle actions are request slots; the adapter needs a traceable semantic-to-physical execution layer without silent action substitution. |
| Task 2 | Task 6 | frozen partitions, metrics, method conditions, resource/fairness contracts | Clean with rulings below: Task 6 must reject undeclared partition/ID pairs and preserve pesticide-only resource equality. |
| Task 3 | Task 6 | `ActionResult`, evaluation mode, full algorithm state and checkpoint ancestry | Clean: evaluation must retain the exact sampled masks/mapping and prove byte identity before/after. |
| Tasks 4-5 | Task 6 | on-policy/off-policy `act`, deterministic evaluation, normalization/exploration state | Clean: the environment consumes the shared action result and does not call `observe` or `update` during evaluation. |
| Task 6 | Task 7 | fixed/A*/nearest/urgency/two-stage condition adapters | Clean: Task 6 exports stable controller and budget-ancestry interfaces; it does not generate experiment families. |
| Task 6 | Task 10 | physical environment and deterministic evaluation runner | Clean: Task 10 may orchestrate these interfaces but must not redefine metric or partition semantics. |
| Task 6 | Task 6 | listed modules, direct event metrics, controller tests, G2/G3/G4 regressions | Clean with rulings below; tests must precede production code and cover real graph/state/event behavior. |

Task 6: Ruling: a vehicle slot remains the sampled high-level action; the adapter stores its exact slot and request mapping, derives the deterministic current road direction as execution detail, and rejects any sampled action outside the stored role mask. Cost if wrong: downstream rollouts require a one-time action-execution schema migration.
Task 6: Ruling: emit an adapter-owned dispatch-reservation event when a request slot is committed, carrying request ID, selected service road node, origin road position, and shortest feasible route length; formal rendezvous distance accumulates this direct event, not the later G2 service-start separation. Cost if wrong: Task 8 schemas and historical metric consumers need a field migration.
Task 6: Ruling: compute `reduction_rate` and `success_at_0_85` only when explicit finite initial/final pest totals are supplied by the environment outcome boundary; do not invent pest dynamics or reinterpret sprayed volume as pest reduction. Cost if wrong: a later audited ecological model may require adapting the outcome-provider interface, but no false efficacy signal enters Task 6.
Task 6: Ruling: request waiting uses elapsed decision intervals: service-start wait is `start_step - created_step`, while an unresolved terminal request contributes through the terminal boundary. Cost if wrong: later locked table fixtures need a documented off-by-one migration.
Task 6: in progress (base 02b4b0fa2a842645bf7007596a19644b9664c193).
Task 6: implementer complete (commit a5918b76f8c11ee91dc5be1681776cf73ac42c8c); task review found five implementation-level Important findings.
Task 6: Ruling: the review's missing push and `docs/PROJECT_STATE.md` record is a sequencing item, not an implementation defect — the SDD/AGENTS workflow requires review and fresh controller verification before the content push, followed by a separate persistence-record commit — cost if wrong: the Task 6 completion record is delayed, but no unreviewed code enters remote evidence history.
Task 6: minor (deferred): active A* dispatch converts an unreachable route to zero length instead of failing closed.
Task 6: minor (deferred): fixed-controller coverage exercises `decide()` in isolation rather than through the physical environment/`ActionResult` boundary.
Task 6: fix round 1/5 started (deep exception-safe evaluation restoration, executable A* replanning and sampled/tie coverage, strict G5 partition contract reuse, non-bypassable exact fixed-resource matching, and frozen reduction epsilon semantics).
Task 6: fix round 1/5 (4 addressed, 1 open — the metric registry still lacks a numeric epsilon and callers can supply arbitrary positive values; commits a5918b7..6048683).
Task 6: Ruling: freeze `reduction_rate` denominator epsilon as `1.0e-12` in `configs/problem2/g5/metrics.yaml`, expose and validate it through the strict G5 contract loader, and remove caller freedom to choose another value — the design mandates `initial_total_pest + epsilon` but no accepted source currently supplies the number; `1.0e-12` is a dimensionless numerical guard negligible at every nonzero pest-total scale and no pilot/formal rows exist yet — cost if wrong: migrate the metric contract and regenerate later Task 6 fixtures before any pilot, with no current scientific result to recompute.
Task 6: fix round 2/5 started (freeze and enforce the canonical reduction epsilon through registry, strict loader, metric implementation, and regression tests).
Task 6: fix round 2/5 (1 addressed, 0 open — canonical `1.0e-12` epsilon is registry-owned and caller override is removed; commit 044209c84803b0ab9e9c6ff51dddbca83ff03228; scoped re-review clean).
Task 6: implementation and task review complete; fresh controller verification passed (focused 63, G3/G5 290, G2/G4 178, G5 contract audit pass, compileall/diff check exit 0); content push pending.
Task 6: content complete (commits a5918b76f8c11ee91dc5be1681776cf73ac42c8c..044209c84803b0ab9e9c6ff51dddbca83ff03228 pushed; local, upstream, and remote heads matched 044209c84803b0ab9e9c6ff51dddbca83ff03228).
Task 6: complete (persistence record f58cda0ee5516745a2b4e86bbe0c17ad2aa92d6b pushed; final local/upstream/remote parity verified; Task 7 is next and was not started).

## Task 7 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Task 2 | Task 7 | `G5Contract`, frozen methods/conditions, partitions, candidates, fairness, and protocol hash inputs | Clean: Task 7 consumes the strict frozen contract and must not mutate its scientific values. |
| Task 6 | Task 7 | `Problem2CooperativeEnv`, heuristics, two-stage ancestry, and required condition IDs | Clean: Task 7 references stable condition IDs and budget ancestry but does not redefine physical execution or metrics. |
| Task 7 | Task 8 | canonical training identity, experiment identity, family references, unique job graph, manifest paths/hashes | Clean: Task 8 consumes Task 7 identities/manifests; Task 7 must not add orchestration, recovery, validation, or sealed execution. |
| Task 7 | Task 7 | listed identity/family/matrix/ablation/sensitivity modules, configs, generator, tests | Clean: tests cover the exact APIs and generated counts; no listed file is later required to be edited outside this task. |

Task 7: in progress (base f58cda0ee5516745a2b4e86bbe0c17ad2aa92d6b).
Task 7: review round 1 findings — Critical canonical training identity is raw serialization instead of the required SHA-256 digest; Important family/dedup references are omitted from manifests, tracked manifest Git provenance is stale versus the generator HEAD, safe deduplication does not validate canonical identity drift, frozen family/ablation/sensitivity registries are not consumed or hashed, project-state persistence is missing, and manifest summary lacks raw/decomposition/provenance metadata. Minor findings: ablation full-group truth is not strict, sensitivity center drift is not rejected, and identity field normalization/control-character validation is permissive.
Task 7: fix round 1 complete (9 technical findings addressed; 1 process item remains for controller bookkeeping; commits 32dedfd..7d3d635, scoped re-review clean for technical fixes except PROJECT_STATE and source-tree hash scope).
Task 7: fix round 2 started — include `src/problem2/experiments/g5_contract.py` in canonical source-tree provenance (and document the complete hash scope); keep the output-only drift rule and no-execution boundary.
Task 7: fix round 2 complete (provenance scope finding addressed; no new Critical/Important findings; final content/report parity at c609b8713ed9589b4a5f754dadcc1afa8a56d6cb; scoped re-review clean).
Task 7: complete (commits 82e5775..c609b871, review clean; PROJECT_STATE persistence record remains to be committed separately before Task 8).
Task 7: persistence complete (PROJECT_STATE record commit 53092e1fce52664a2a52dbd8acd5ffb7486081a3 pushed; local/upstream/remote parity verified; Task 8 is next authorized work).

## Task 8 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Task 7 | Task 8 | `TrainingJob`, canonical identity, frozen manifests, protocol/registry hashes | Clean: Task 8 consumes the exact SHA-256 identities and rejects stale or incomplete job inputs; it does not regenerate or mutate the scientific manifest. |
| Task 2 | Task 8 | frozen partitions, pesticide-only resource contract, metric definitions | Clean with ruling below: validators bind records to the strict G5 contract and reject sealed IDs, battery replenishment, resource mismatch, and metric drift. |
| Task 3 | Task 8 | checkpoint ancestry and atomic persistence | Clean with ruling below: recovery stores append-only attempt events and uses same-identity retry only; input/hash drift is stale and never resumed. |
| Task 6 | Task 8 | direct episode mechanism metrics and deterministic evaluation boundary | Clean: raw schemas preserve direct logged measures and evaluation state proofs; validators do not reinterpret sprayed volume as pest reduction. |
| Task 7 | Task 8 | G6/G7 skeleton manifests and output root | Clean: preflight verifies provenance and output confinement, while dry-run CLIs cannot execute or read sealed rows. |
| Task 8 | Task 8 | listed ledger, schema, validator, recovery, artifact, and lock modules | Clean: tests define strict public boundaries first; no pilot, formal training, validation tuning, or sealed evaluation is authorized. |

Task 8: Ruling: use a JSONL append-only ledger with one immutable event per transition and a materialized in-memory view rebuilt from the log; lease ownership is `(identity, attempt, lease_id)` and a second worker cannot acquire an active lease. Cost if wrong: a later persistence migration would need to preserve event ordering and lease identity, but no scientific result is affected.
Task 8: Ruling: quarantine records retain the exact original UTF-8 bytes, source locator, reason code, and SHA-256 source hash; validators return failures without deleting or rewriting invalid rows. Cost if wrong: downstream audit readers would need a one-time schema adapter, so the exact byte-preservation contract is tested now.
Task 8: in progress (base 53092e1fce52664a2a52dbd8acd5ffb7486081a3).
Task 8: steps 1-3 complete — added failing ledger/orchestration, schema/validator, quarantine, recovery, and sealed-guard tests; every public sealed-input path is parameterized for IDs 30000/30099, sealed paths, and truthy access flags.
Task 8: step 4 RED confirmed — focused collection fails with `ModuleNotFoundError` for the new `evaluation.schema` and `evaluation.sealed_lock` APIs before implementation.
Task 8: implementation complete locally at c22d5b2 plus compatibility fix debb9ba; controller focused verification initially passed (33), but independent review found 3 Critical and 9 Important findings; no push or acceptance.
Task 8: fix round 1 started — add regression tests for frozen provenance binding, complete raw metrics, legal ledger replay and retry chain, strict method/action/resource domains, arbitrary-byte quarantine, descendant path checks, Path sealed guards, strict lock counters, and finite GPU telemetry. Review package/report: task-8-review.md.
Task 8: fix round 1 implementation complete at 451ffd9 plus 900dc0a; focused regression `44 passed`, compileall and diff checks passed; scoped re-review pending.
Task 8: fix round 2 started after scoped review — require provenance on evidence validation, reject duplicate initial events, stale completed drift, exact preflight/lock binding, default inter-process GPU lease, validated artifact content hashes, and recomputed canonical identities.
Task 8: fix round 2 implementation complete at bb81a7d; focused Task8 `47 passed`; final scoped re-review pending.
Task 8: fix round 3 started after final scoped probe — separate recomputed evaluation identity from canonical training identity so scenario-level rows remain unique while preserving Task 7 training identity binding.
Task 8: fix rounds 3-4 complete — strict ledger provenance formats, exact Task 7 registry-key matching, canonical output-root confinement, non-bypassable identity validation, malformed-manifest fail-closed handling, and numeric-string sealed-ID rejection were implemented and independently re-reviewed clean for `bb81a7d..c62c9a8`.
Task 8: final verification complete — focused Task8 `60 passed`; G3/G5 `358 passed`; G2/G4 `178 passed`; G5 contract audit pass; compileall, all CLI help, and diff check passed; structured G6/G7 preflight both `all_pass=true`, `queue_created=false`, `sealed_accessed=false`.
Task 8: persistence complete — content head `945dc97badafbcbfcc131cb50ea8e20d589c840e` and state-record head `ed94abbcdb55a8f48a10f1e96057f860a3ea7b07` were pushed with local/upstream/remote parity verified. No pilot, formal training, validation tuning, or sealed evaluation occurred; Task 9 is next authorized work.
Task 9: preflight interface scan — clean. Task 9 consumes only validated evidence mappings and the frozen statistics contract; it produces pure summaries for Task 10/11 and does not mutate Task 8 schemas, manifests, partitions, or sealed locks.
Task 9: in progress (base ed94abbcdb55a8f48a10f1e96057f860a3ea7b07).
Task 9: implementation complete at `5b8064c61391d2a10ad51f5a76d6d573bba9e2bc`; independent review found two Critical and four Important boundary/type findings.
Task 9: fix round 1 complete at `c56fc3d`; paired A-B direction, CLI import/provenance, convergence finite/censoring, mechanism typing/scale coherence, diagnosis completeness, and Holm/equivalence validation were corrected. Scoped re-review left two boundary findings open.
Task 9: fix round 2 complete at `f18d71dba97fd10218082feb86b4f1f4bec769ef`; explicit development provenance, token-based raw/sealed path rejection before I/O, and unknown diagnosis-stage rejection were added. Scoped re-review marked all findings addressed with no new Critical/Important breakage.
Task 9: fresh verification — focused statistics `12 passed` twice; deterministic serialized adapter outputs byte-identical; G3/G5 `370 passed`; G2/G4 `178 passed`; G5 contract audit `status=pass`; both CLI help commands, compileall, and `git diff --check` passed. No experiments, validation tuning, formal jobs, or sealed access occurred.
Task 9: complete (commits `5b8064c..f18d71d`, review clean; content and PROJECT_STATE persistence pushed with parity). Next authorized work: Task 10 smoke acceptance; G6/G7 execution remains unauthorized.

## Task 10 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Tasks 3-5 | Task 10 | `build_algorithm`, role-aware `act/observe/update`, checkpoint state | Clean: smoke runner must instantiate only frozen G5 methods and preserve role masks, deterministic evaluation, and checkpoint round trips. |
| Task 6 | Task 10 | development environment, condition adapters, direct metrics | Clean with boundary: smoke may exercise condition types with development IDs but must not convert smoke metrics into efficacy or pilot evidence. |
| Task 7 | Task 10 | job identities, family/condition IDs, source/protocol hashes | Clean: runner must bind artifacts to frozen job identity and reject drift rather than regenerate scientific configuration. |
| Task 8 | Task 10 | raw/validated schemas, quarantine, output root, sealed guards | Clean: smoke artifacts must be confined to the frozen output root, explicitly development-only, and validated fail-closed. |
| Task 9 | Task 10 | diagnostics and convergence summaries | Clean: Task10 may emit finite/update diagnostics; no Task9 endpoint inference or formal statistics is authorized. |
| Task 10 | Task 10 | CPU/CUDA preflight, runner, CLI, smoke audit | Clean: tests and CLI must cover all five learning methods, all condition types, checkpoint reload, deterministic freeze, interruption/resume, and resource telemetry without silent config edits. |

Task 10: in progress (base 37221602c6b3566f877ab4269e094e82c5b8ac2e).
Task 10: implementation and fix review complete — runner contract failures,
development-seed enforcement, algorithm/condition identity binding, resume
digest comparison, homogeneous smoke manifests, and CPU/CUDA audit persistence
were verified. Final smoke audits are CPU/main `pass/85` and CUDA `pass/5`.
Task 10: complete (content/artifact head `dc6ceab29bedcba9936617d6022fae37b10f2ee5`; state record `8dfe19b7e2305a554b4c124fbb3ae984deed9641` pushed with parity). Task 11 is next authorized.

## Task 11 Preflight Interface Scan

| Producer task | Consumer task | Shared file/interface | Finding |
|---|---|---|---|
| Task 2 | Task 11 | development partitions, budget rule, tuning candidates | Clean: pilot uses only `51001-51003` and `10000-10019`, then calls the frozen largest-feasible budget selector. |
| Task 10 | Task 11 | `run_training_job`, checkpoint/logging path, method/condition identity | Clean after correction: pilot passes scale and scenario identity through the runner log and keeps the algorithm owned by `method`. |
| Task 8 | Task 11 | output confinement and evidence status flags | Clean: pilot records are descriptive development artifacts with validation/sealed/battery flags false; no sealed lock mutation. |
| Task 9 | Task 11 | runtime summaries and later statistics | Clean: Task 11 only aggregates runtime and freezes candidates; it does not compute efficacy or infer method ranking. |

Task 11: implementation in progress — tests first for exact 10,200-job matrix,
conservative runtime aggregation, four-candidate freeze, bounded runner
identity, and descriptive audit output. Full neural pilot execution remains a
resource-bound runtime operation and is intentionally not replaced by
synthetic evidence.

Task 11: complete — implementation commit `b11298b39d7996a2f46d0c98e9dec774b18a96b4`
and smoke provenance refresh commit `9fca4f2a64845a1cddbeda018d906e5d53a3da25`
were pushed. The full CPU pilot returned `status=pass` with `510` training
jobs and `10,200` development episode records, covering the two required
scales, five methods, 17 conditions, three training seeds, and scenarios
`10000-10019`. Runtime aggregation selected `200000` interactions,
`10000`-step checkpoints, and `20` checkpoints. Four content-hashed candidates
were frozen for each of the five learning methods before validation access.
Fresh regression verification passed: G5 `325`, G3/G5 `390`, G2/G4 `178`,
compileall, diff check, contract audit, and artifact dry-run. Pilot, validation,
sealed, and battery boundary audits all remain false; actual sealed unlock count
remains `0`. Task11 content and evidence persistence is still to be committed
and pushed before Task12 may begin.

## Task 12 Recovery And Pre-Validation Failure

Task 12 pre-validation implementation is persisted through
`374bacbb3bb3a0db25015c88f98340cdfe73cfdc`. Local, upstream, and remote
parity, the immutable candidate/budget hashes, and sealed lock
`maximum=1/actual=0` were reverified before execution. No validation JSONL row
was written and no sealed content was accessed.

Task 12: first candidate-training attempt stopped before validation access.
Fifteen of sixty synthetic runner units had summaries when the stop occurred;
all are rejected as validation-selection inputs. The attempt exposed three
load-bearing defects:

1. `run_training_job` saved its checkpoint before `algorithm.update()`, so the
   checkpoint loaded for validation was the pre-update policy while the summary
   described the post-update policy. A four-interaction IQL reproduction gave
   unequal summary/checkpoint policy digests.
2. Task 12 called the Task 10 runner whose module contract explicitly limits it
   to synthetic development smoke and says it is not pilot or evaluation
   evidence. Its observations and reward were synthetic constants rather than
   transitions from the frozen physical development environment.
3. Saving the complete 200,000-transition pending/replay state before update
   produced 0.8-1.9 GB checkpoints. Seventeen checkpoint files consumed about
   20.9 GB; projected completion exceeded available disk and ordinary GitHub
   file limits.

Task 12: Ruling: the stopped outputs remain a preserved failed pre-validation
attempt and must never be recovered as candidate evidence. Repair Task 12 with
a dedicated physical development-training path, rollout/update cadence owned
by the frozen candidate configuration, update-before-terminal-evaluation
checkpoint semantics, bounded recoverable training state, and a transactional
validation row/ledger commit. Add failing regression tests before production
changes and rerun all 60 candidate identities from a new attempt root. Cost if
wrong: the candidate-training matrix must be rerun again, but validation remains
unaccessed and the immutable candidate/statistics contracts remain unchanged.

Task 12: independent pre-access review not ready. Critical findings cover the
synthetic/pre-update training path, missing canonical validation long table,
non-atomic and subsettable first access, freeze-manifest self-reference and
missing audits, and incomplete G6/G7 manifest execution fields. Important
findings cover one-way access governance, exact identity/refit recomputation,
the `0.2875 L` mechanism condition and stale next observations, and immutable
failure-attempt retention.

Task 12: Ruling: G6/G7 execution remains blocked throughout G5, as required by
the gate order. Task 12 must nevertheless freeze executable-complete job and
evaluation identity inputs (including budget/checkpoint/dependency fields) and
make preflight validate them. The later G6 gate may remove the execution block
only after both G5 content and persistence commits pass remote parity. Cost if
wrong: one narrow G6 authorization commit is required before queueing, but no
formal job can run prematurely during G5.

Task 12 remediation 1: in progress (physical development training,
post-update bounded evaluation checkpoint, and invalid stopped-attempt
rejection; brief `task-12-remediation-1-brief.md`).

Task 12 remediation 1 fix round 1/5: C1 and I1-I6 closed by the physical
completion manifest validator, canonical source/root/budget guards, complete
evaluation digest, mask-derived actor validity, strict physical scenario
contract, and guarded wrapper/factory paths. Affected focused verification
passed `81` tests and protocol/checkpoint regression passed `27` tests; no
canonical training or validation operation ran. I3 controller ruling: the
ecological constants are provisional simulation assumptions only; if they are
wrong or changed, all 60 candidates require retraining, while validation
remains untouched. The fix-round work is intentionally uncommitted and
unpushed.

Task 12 remediation 1: persisted in `c77c7904030117881ceb98f9398b94038ecfd815`
and pushed; the stale contract-hash test was corrected in
`dca3466e0c8a72fb4b29a78cc0b9bcf9ed6adf6f` and pushed. Fresh main-worktree
verification is `403 passed` for `tests/g5`; the clean-worktree matrix check is
`8 passed` after preserving the ignored fixture boundary. The clean-worktree
full regression attempt is not evidence because it lacked ignored G5/G4
fixtures and used the wrong working directory for the first probe; no source or
protected user directory was changed by that probe. The invalid first attempt
was inventoried, moved to `g5/quarantine/task12-first-attempt`, and reduced to
40 JSON/log metadata files. Task 12 remediation 2 is now in progress from base
`dca3466`; validation and sealed access remain false/forbidden.
Task 12 remediation 2 fix round 1 status: focused TDD implementation completed
with `128 passed` in the affected G5 suite. No canonical validation, G6/G7,
refit, formal, sealed, commit, or push operation ran. I3 controller ruling:
the gamma-shape/scale, normalized initial pest total, and spray-mortality
coefficient remain provisional simulation assumptions with no empirical or
deployment claim; if ecological assumptions are wrong or changed, all 60
candidates require retraining, while validation remains untouched.
