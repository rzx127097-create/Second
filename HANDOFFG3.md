# HANDOFF G3

Date: 2026-08-20
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g3-heterogeneous-marl`

## Gate Result

G3 passed at maturity `M2` after the hardened heterogeneous-MARL acceptance
suite and the canonical development smoke passed. The implementation commit,
evidence commit, and persistence record are recorded in
`docs/PROJECT_STATE.md`.

Permitted claim:

> The heterogeneous SR-MAPPO learning interface passed the registered G3
> implementation and replay acceptance suite, including role isolation,
> team-valid sample filtering, saved-mask replay, team GAE, normalization
> freezing, checkpoint round trip, G2 mask conversion, candidate-slot
> identity validation, provenance binding, and a finite development-only
> training smoke.

This is not evidence that mobile replenishment improves treatment, that
SR-MAPPO outperforms a comparator, that formal experiments exist, or that the
simulation represents real deployment.

## Frozen Interface

- Public algorithm name: `SR-MAPPO`.
- Problem identity: air-ground heterogeneous extension.
- One shared UAV actor for `N=2` UAVs.
- One independent vehicle actor with `hold + slot-0..slot-3`.
- One structured centralized team critic.
- UAV observation dimension: `179`.
- Vehicle observation dimension: `28`.
- Critic state dimension: `185`.
- G3 configuration hash:
  `421eff64d1161f78c9029dfc6d133b9b66247f3cf905b9577e55965584195f93`.
- Pesticide is the only replenished resource; battery replenishment is
  inactive.
- Scenario seed manifest:
  schema `g1.v1`,
  SHA-256
  `ab993f19e1ae4cb9d7ba4f4f862639901581be057e0a251e5c113d957f6059ce`.

## Verified Evidence

- Audit report:
  `outputs/problem2_sr_mappo_v1/g3/g3-marl-audit.json`.
- Compliance report:
  `docs/audits/g3-marl-compliance.md`.
- Raw development log:
  `outputs/problem2_sr_mappo_v1/g3/training-smoke.jsonl`.
- Provenance:
  `outputs/problem2_sr_mappo_v1/g3/provenance.json`.
- Checkpoint:
  `outputs/problem2_sr_mappo_v1/g3/checkpoints/g3-smoke.pt`.
- Smoke source-tree commit:
  `092b7f3e965a24979bac65c8304cd9d7dc142f73`.
- Implementation source-tree hash:
  `a3b5f20c6935cf29c0c0edb627cf64a0b4b5c7b96a3ca94449c205da1b5f2a95`.
- Acceptance result: `17/17`, audit `status=pass`.
- Smoke: development seed `9017`, `2` updates, finite losses.
- Audit report SHA-256:
  `b9e2829f02372235bba856317767b8d0703d83e5841c75befab68d092ddc6b2c`,
  `4874` bytes.

Artifact hashes:

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| `training-smoke.jsonl` | `9885e24a0e58191fdd7975b55d72487d3f817985c8a0ec585d737af5228e2972` | 2204 |
| `provenance.json` | `10da75b9c01d485ece3e6214de10367ba5356d80e4be97e38a1e399afb9ed69d` | 756 |
| `checkpoints/g3-smoke.pt` | `832ddd1350ff82a0642b144c4d962e762f47b294dcc00873354e2df99159d0b3` | 1293261 |

## Fresh Verification

- `python -m pytest tests/g3 -q`: `63 passed`.
- `python -m pytest -q`: `221 passed`.
- `python -m compileall -q src scripts`: exit 0.
- `git diff --check`: no content errors.
- `python scripts/run_g3_training_smoke.py --config
  configs/problem2/g3_heterogeneous_marl.yaml --output-root
  outputs/problem2_sr_mappo_v1/g3 --seed 9017 --updates 2`: finite smoke,
  canonical output root, source-tree-bound checkpoint and raw log.
- `python scripts/audit_g3_marl.py --config
  configs/problem2/g3_heterogeneous_marl.yaml --output-root
  outputs/problem2_sr_mappo_v1/g3 --report
  outputs/problem2_sr_mappo_v1/g3/g3-marl-audit.json`: `status=pass`,
  `17/17` acceptance nodes.

## Protected Boundaries

No formal matrix jobs, validation tuning, sealed-test unlock, validation or
sealed scenario access, battery activation, resource-activation claim,
endpoint comparison, or deployment claim occurred in G3.

The G3 smoke is engineering evidence only. It must not be reused as treatment
efficacy evidence or as a pilot result.

## G4 Entry

After the G3 evidence and persistence records are pushed and recorded, G4 is
authorized as the next gate. G4 must begin with:

1. resource-scarcity activation using the G2 physical foundation;
2. counterfactual mechanism probes for fixed versus mobile support;
3. a fail-closed record of the parameter range where scarcity is active.

G4 must use the frozen G3 learning interface and must not access sealed-test
scenarios. Formal training, validation tuning, and sealed evaluation remain
unauthorized until their later gates.
