# Dynamic G5 Replacement Matrix Audit

Date: 2026-08-30

## Scope

This audit records the contract and dynamic reacceptance preparation for the
replacement G5 development matrix. It is an `M2` engineering record only. It
does not authorize formal G6 execution, validation selection, sealed access, or
efficacy/superiority claims.

The replacement matrix is the minimum scope compatible with the existing
runtime-budget and selected-refit contracts:

```text
8 executable conditions x 2 representative scales x 3 development seeds = 48 jobs
```

The executable condition-to-method pairs are:

| condition | learning method | execution path |
|---|---|---|
| `sr_mappo_mobile` | `sr_mappo_mobile` | learned, joint |
| `sr_mappo_fixed` | `sr_mappo_mobile` | fixed support, UAV-only |
| `sr_mappo_astar` | `sr_mappo_mobile` | rolling A*, UAV-only |
| `mappo_mobile` | `mappo_mobile` | learned, joint |
| `sr_mappo_two_stage` | `sr_mappo_mobile` | learned two-stage |
| `ippo_mobile` | `ippo_mobile` | IPPO mobile |
| `maddpg_mobile` | `maddpg_mobile` | MADDPG mobile |
| `iql_mobile` | `iql_mobile` | IQL mobile |

The twelve diagnostic-only conditions are explicitly excluded from the
replacement matrix and primary selection:

```text
sr_mappo_nearest
sr_mappo_urgency
no_observation_normalization
no_return_normalization
no_network_stabilization
no_robust_value_update
no_learning_rate_decay
learning_rate
clip_range
entropy_coef
gamma
gae_lambda
```

## Simplified Reacceptance Policy

Reacceptance is split into a source-scope gate, a no-training matrix contract
gate, a targeted dynamic runtime gate, and the sequential pilot gate. Full G3
or G4 suites are rerun only when their source or configuration scope changes;
otherwise the persisted dynamic audit is reused after the source-scope and
remote-parity checks pass. Every pilot identity still receives automated
identity, provenance, dynamic-ecology, conservation, artifact-hash, and
boundary checks.

The hard boundaries remain unchanged:

- all primary evidence uses `dynamic_pest_v1`;
- pesticide is the only replenished resource and battery replenishment is false;
- development scenarios are `10000-10019` with training seeds `51001`, `51002`,
  and `51003`;
- validation scenarios `20000-20049` and sealed scenarios `30000-30099` are not
  accessed during this phase;
- old static G5 output and the seven historical Phase 3 pilots are preserved
  as historical diagnostics and are not merged into this matrix;
- pilots remain one job at a time and the matrix is incomplete until all 48
  identities pass audit.

## Contract Implementation

The contract and tests were committed and pushed in:

- `c92b70678727511e8ac19d0531d9b81a54277295`
  (`feat: define dynamic g5 replacement matrix`)

The implementation now exposes eight executable conditions, maps all five
learning methods to real runtime rows, exposes twelve excluded diagnostics,
and rejects incomplete, duplicate, or out-of-contract jobs. The focused TDD
cycle observed the expected RED failure against the partial 30-job draft and
then passed after the minimal mapping change.

## Dynamic Reacceptance Evidence

The evidence content was generated from source commit
`c92b70678727511e8ac19d0531d9b81a54277295` and pushed in:

- `b0ab4cd5719e7fab93a810fdb9f7717b9796cb4a`
  (`test: record dynamic g3-g5 reacceptance`)

Fresh verification:

```text
python -m pytest tests/g5/test_pilot_freeze.py -q --tb=short
20 passed in 53.36s

python -m pytest tests/g5/test_pilot_freeze.py tests/g5/test_experiment_matrix.py tests/g6/test_condition_semantics.py tests/g6/test_controller_wiring.py tests/g6/test_physical_vehicle_isolation.py -q --tb=short
63 passed in 83.63s

python -m pytest tests/g5/test_environment_metrics.py tests/g5/test_physical_candidate_training.py -q --tb=short
67 passed in 187.73s

python -m compileall -q src scripts
exit 0

git diff --check
pass

python scripts/audit_dynamic_pest.py --root . --output outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-g3-g5-reacceptance.json
status=pass

python scripts/run_g5_smoke.py --device cpu --interactions 128 --method sr_mappo_mobile --ecology-mode dynamic
status=pass jobs=1
```

The dynamic audit and smoke both report `validation_accessed=false`,
`sealed_accessed=false`, and `battery_replenishment_enabled=false`. The smoke
and audit source commit is `c92b70678727511e8ac19d0531d9b81a54277295`.

Recorded artifact hashes:

| artifact | bytes | SHA-256 |
|---|---:|---|
| `dynamic-g3-g5-reacceptance.json` | 1892 | `fccc002816bb56fadcb9ab91f952f69c9084c7ce4e8ff9abb57774c74c25a983` |
| `smoke-audit.json` | 4458 | `a2b80604d1e0a7b75135b1c39dd6d865de5a1d183a3a2e1ea9add5956de73463` |
| `smoke-audit-cpu.json` | 4458 | `a2b80604d1e0a7b75135b1c39dd6d865de5a1d183a3a2e1ea9add5956de73463` |
| `smoke/.../manifest.json` | 1678 | `014e5ea336753b8c630e2ecd5052112d995561326d93501f68a3e109f19547ec` |
| `smoke/.../summary.json` | 2992 | `d179515e6b906c827d6896b2b4737e9fd49e21276729b46efb1508bdbab56b35` |
| `smoke/.../checkpoint.pt` | 1295757 | `47a564cd593f665c2209e8f44bb09f57ffc40ae0b830bc4e7e43c9f9788872d` |

## Gate Status

The dynamic G3/G4 reacceptance preparation and the 48-job matrix contract are
accepted at `M2`. The replacement G5 matrix itself is **not complete**:

```text
matrix_complete=false
completed_identities=7 historical identities only
replacement_freeze=not generated
Phase 4 preflight=blocked
formal G6=blocked
sealed unlock count=0
```

The seven historical Phase 3 identities and the preserved untracked index-7
IPPO artifact remain outside the replacement aggregate. The next authorized
action is to execute the new 48 identities one at a time under the committed
contract, preserve failed attempts, audit each completion, and generate the
replacement freeze only after all 48 identities pass.

## Runner Hardening Before Execution

Commit `83c14073ad1a2f8300dda61c288aa4554991b4ee` hardens the replacement
execution boundary before any replacement identity is run. `run_pilot_matrix`
now rejects missing or non-development partitions, non-physical training,
non-executed scenarios, missing completion validation, non-pesticide resource
claims, and incomplete or malformed dynamic ecology provenance. Its artifact
verification cross-checks every recorded identity against the canonical 48-job
matrix and requires the audit's expected/completed identity sets and
replacement scope to agree. Historical static G5 paths remain readable only
under the legacy compatibility branch and cannot satisfy the new replacement
contract.

The CLI now dispatches all replacement jobs through the physical dynamic refit
runner, injects controller semantics from `resolve_condition_execution`, fixes
candidate `c01`, and writes below
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/replacement-48/`.
Focused and affected verification on the pushed commit returned `46 passed`
and `139 passed`, respectively, with successful `compileall`, `git diff
--check`, and CLI help checks. This hardening checkpoint does not change the
gate status: `matrix_complete=false` until all 48 physical identities pass.

## Dynamic Replacement Freeze Acceptance

On 2026-08-30, the complete replacement matrix was executed and frozen under
the dynamic ecology namespace. The freeze is independent of the historical
static G5 validation/refit payloads and binds only the replacement pilot
evidence, candidate/budget manifests, and dynamic G6 manifests:

```text
freeze=outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/freeze-manifest.json
schema=g5-dynamic-replacement-freeze-v1
matrix_complete=true
jobs=48
episodes=960
conditions=8
scales=g20x20_d2,g30x50_d4
training_seeds=51001,51002,51003
partition=development
ecology=dynamic_pest_v1
replenished_resource=pesticide
validation_accessed=false
sealed_accessed=false
battery_replenishment_enabled=false
actual_unlock_count=0
```

The freeze source is commit `1cc9748b9143a604bd89a5bf754e118b6cab6c6c`
with source-scope SHA-256
`eb654f00d9ee1e61c8c1d43574759748098155ffb2b6c7252ae28b644ed6557a`.
The replacement evidence was generated from ancestor commit
`7390e891d54ff8eb141a2a4ff02fd2666ba4e316`; no validation or sealed payload
was read. The freeze artifact itself is 12,910 bytes with SHA-256
`3b881d9a096580c0a3e95c3ebecb22e7c5c71e2fb75af8302667fbf639786e26`.

Bound artifact hashes:

| artifact | bytes | SHA-256 |
|---|---:|---|
| `pilots/replacement-48/audits/pilot-audit.json` | 13,505 | `02dff0dc1f2f74ac639dabd0396a8afac36e1dd214ecc72cb22219dd29a3acaf` |
| `pilots/replacement-48/audits/pilot-artifact-manifest.json` | 761 | `f1e1c25615560aaaae585a7cc712053703250530d7bd466d6da682814e40055b` |
| `pilots/replacement-48/validated/pilot-episodes.jsonl` | 6,448,460 | `bafc575453c3ceb9a9ff56e1ccacb26d805a166cc181a004565a52b9624683ac` |
| `manifests/validation-candidates.json` | 16,942 | `c5aee01a2ad180301aa8f2d2d39b067500f6297ac3ac1b503f68814334ba8918` |
| `manifests/pilot-budget.json` | 1,622 | `6c97e5e882dfbbba3cba133185f1a589268d9191beb51f2874a0202cbcc0920d` |
| `manifests/g6-training-jobs.json` | 1,121,360 | `9ef2224c669f20277e2085843679508aa5b37abefc88f3be2ba9b1f16adcc225` |
| `manifests/g6-validation-evaluations.json` | 1,521 | `e8b67d5e54ae5bc6b740b9434ba759db6c032db39c21cff4509721e3c8b34a31` |

The evidence/freeze content commit is
`2c6663d06ab58c56bf7c0577398303c67d1bb8ea` and the source-scope CLI rebind
is `890255c7710e97ce88b098cd4c1e9ff8be7931d1`. The read-only preflight
against the exact freeze returned `all_pass=true`, including
`dynamic_g5_freeze=true`, `dynamic_replacement_matrix=true`,
`no_sealed_identities=true`, and remote parity. This closes the replacement
G5 freeze prerequisite at `M2`; it does not execute formal G6, unlock G7,
access validation scenarios, or support efficacy/superiority claims.
