# G4 Resource-Scarcity Mechanism Compliance Audit

Date: 2026-08-21

## Result

The G4 resource-scarcity and fixed/mobile counterfactual boundary passes at
maturity `M2`. The evidence is a development-only mechanism probe built on the
frozen G2 physical foundation and the G3 heterogeneous SR-MAPPO interface.

- Gate: `G4`
- Audit: `g4-mechanism-compliance`
- Audit status: `pass`
- Public algorithm: `SR-MAPPO`
- Problem identity: air-ground heterogeneous extension
- Scarcity band: `[1.0, 12.0] L`
- Comparator: `sr_mappo_fixed` versus `sr_mappo_mobile`
- Paired records: `27`
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`

## Contract And Probe Coverage

| Contract | Frozen or verified condition |
|---|---|
| Resource scope | Pesticide replenishment only; battery replenishment is `false` |
| Scarcity axis | `initial_uav_pesticide_l` |
| Activation band | Complete contiguous probe coverage at `1.0`, `6.5`, and `12.0 L` |
| Scales | `g20x20_d2`, `g20x30_d3`, `g30x30_d3` |
| Seeds | `42`, `123`, `2024` |
| Counterfactual inputs | Matching scale, seed, scarcity level, and input fingerprint |
| Validation access | `false`; validation partition is empty |
| Sealed access | `false`; sealed partition is empty |
| G3 endpoint reuse | Rejected by the audit boundary |

## Evidence Chain

The contract and probe manifest freeze the G4 interface. The fixed and mobile
activation summaries and JSONL records provide the raw mechanism observations.
The counterfactual summary recomputes paired deltas from those summaries. The
audit verifies the recomputed summary, boundary flags, path containment, and
SHA-256/byte manifest before writing `g4-mechanism-audit.json`.

The current bundle contains 27 fixed/mobile pairs and equal activation counts
of 27 per arm. The recorded maximum conservation error is
`3.552713678800501e-15 L` in the aggregate counterfactual summary. These are
descriptive probe values, not formal evaluation outcomes.

## Artifact Set

- `activation-summary.json`
- `counterfactual-summary.json`
- `provenance.json`
- `g4-mechanism-audit.json`
- `artifact-manifest.json`
- `fixed/` and `mobile/` activation summaries, provenance, and raw JSONL
- `probe-matrix-summary.json`

All endpoint artifacts are JSON or JSONL files under the canonical G4 output
root. The artifact manifest records each path, byte count, and SHA-256 hash.

## Claim Boundary

The evidence supports only the statement that the frozen pesticide scarcity
mechanism activated and that fixed/mobile arms produced paired descriptive
deltas under the registered development probe. It does not support a mobile
treatment improvement claim, an SR-MAPPO superiority claim, a significance
claim, a formal endpoint result, or a deployment claim.

The next authorized gate is G5. G5 entry requires persisted G4 content and
state records, matching local/upstream/remote references, and a pre-registered
pilot protocol with resource budgets, horizons, scenario/seed protocol,
information conditions, baseline fairness, validation-tuning rules, and
paired statistical estimands independently audited before formal jobs.
