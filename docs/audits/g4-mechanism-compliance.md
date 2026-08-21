# G4 Mechanism Compliance Audit

Date: 2026-08-21
Gate: G4 resource-scarcity activation and counterfactual mechanism probe
Status: pass for the scoped M2 mechanism evidence

## Contract Coverage

| Requirement | Frozen interface or evidence | Result |
|---|---|---|
| Public algorithm identity | `SR-MAPPO`; air-ground heterogeneous extension | Pass |
| Replenished resource | Pesticide only | Pass |
| Scarcity axis and band | Initial UAV pesticide, `1.0-12.0 L` | Pass |
| Probe coverage | Three scales, three training seeds, three levels | Pass |
| Counterfactual pair | `sr_mappo_fixed` versus `sr_mappo_mobile` | Pass |
| Physical semantics | Frozen G2 road, service, and conservation engine | Pass |
| Learning lineage | Frozen G3 interface lineage only | Pass |
| Validation/sealed access | Both disabled; partitions empty | Pass |

## Evidence Chain

The source/configuration chain is bound by the G4 contract, probe manifest,
G2 configuration hash, and source-tree lineage in the fixed/mobile provenance
files. Raw JSONL probe logs feed the activation summaries; the summaries feed
the recomputed counterfactual summary; the audit verifies the manifest hashes
and boundary flags. The canonical output root is
`outputs/problem2_sr_mappo_v1/g4`.

The audit records 27 matched fixed/mobile pairs and equal activation counts of
27 per arm. It reports the frozen activation band `[1.0, 12.0]` and
`status=pass`. Conservation residuals are retained as numeric audit values.

## Claim Boundary

G4 supports only the statement that the declared scarcity mechanism was
activated in the frozen probe bundle and that descriptive paired deltas were
computed under identical inputs. It does not support significance, superiority,
treatment efficacy, formal experiment, deployment, or universal-optimality
claims.

## Guardrails

The audit is fail-closed for G3 endpoint reuse, path escape, missing or altered
manifest entries, invalid fingerprints or numeric domains, unsupported files,
validation/sealed access, and battery replenishment. The pytest-generated
scratch subtree remains beneath the canonical G4 root and is treated as
structured G4 probe evidence by the manifest; it contains no G3, validation,
or sealed endpoint data.

## G5 Acceptance Dependency

G5 entry requires the handoff and state persistence commits to be pushed and
hash-matched locally, upstream, and on `origin`. G5 must then freeze a fair
pilot and statistics protocol before any formal job, validation tuning, or
sealed evaluation is authorized.
