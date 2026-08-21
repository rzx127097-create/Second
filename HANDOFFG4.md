# HANDOFF G4

Date: 2026-08-21
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g4-resource-scarcity`

## Gate Result

G4 passed at the existing `M2` evidence boundary. The frozen resource-scarcity
probe activated across the registered pesticide initial-volume band, and the
fixed/mobile SR-MAPPO counterfactual produced same-input descriptive paired
deltas. This is mechanism evidence only; it does not promote the project to
formal treatment-effect evidence.

Permitted claim:

> Under the frozen G2 physical semantics and G4 development probe protocol,
> pesticide scarcity activated over `[1.0, 12.0] L` for the registered probe
> scales and seeds, and the resource-matched fixed-support and road-constrained
> mobile-support SR-MAPPO arms yielded 27 paired descriptive records with
> conservation error within the recorded numerical tolerance.

This claim does not establish that mobile replenishment improves treatment,
that SR-MAPPO is superior, that a result is statistically significant, or that
the simulation represents real deployment.

## Frozen Interface

- Public algorithm name: `SR-MAPPO`.
- Problem identity: air-ground heterogeneous extension of SR-MAPPO.
- Comparator pair: `sr_mappo_fixed` and `sr_mappo_mobile`.
- Scarcity axis: initial UAV pesticide volume, `initial_uav_pesticide_l`.
- Frozen activation band: `[1.0, 12.0] L`.
- Probe scales: `g20x20_d2`, `g20x30_d3`, `g30x30_d3`.
- Probe seeds: `42`, `123`, `2024`.
- Replenished resource: pesticide only.
- Battery replenishment: inactive.
- Validation and sealed-test probe partitions: empty and inaccessible.
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`.
- Contract: `docs/evidence/g4/g4_contract.yaml`.
- Probe manifest: `docs/evidence/g4/g4_probe_manifest.yaml`.

## Verified Evidence

- `outputs/problem2_sr_mappo_v1/g4/activation-summary.json`: root activation
  index, status `descriptive`, band `[1.0, 12.0]`.
- `outputs/problem2_sr_mappo_v1/g4/fixed/activation-summary.json` and
  `mobile/activation-summary.json`: complete fixed/mobile activation records.
- `outputs/problem2_sr_mappo_v1/g4/counterfactual-summary.json`: 27 paired
  records, equal activation counts of 27 per arm, and descriptive deltas.
- `outputs/problem2_sr_mappo_v1/g4/provenance.json`: root lineage and boundary
  flags for the canonical bundle.
- `outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`: audit status
  `pass`; recorded artifact hashes and hard-boundary checks.
- `outputs/problem2_sr_mappo_v1/g4/artifact-manifest.json`: hash and byte
  registration for every supported G4 JSON/JSONL artifact.
- `docs/audits/g4-mechanism-compliance.md`: source-to-claim compliance map.

The counterfactual output is descriptive. It contains no p-values, confidence
intervals, significance labels, formal endpoint decision, or superiority
claim.

## Protected Boundaries

- No G3 smoke or G3 endpoint artifact is accepted as G4 evidence.
- No validation scenario or sealed-test scenario was read.
- No validation tuning, sealed-test unlock, or formal experiment occurred.
- Battery replenishment remains disabled.
- The OSM road data remains simulation input for road-constrained modeling,
  not deployment evidence.
- No external protected asset or thesis Word file was modified.
- G4 outputs remain beneath the frozen problem-2 output root.

## G5 Entry Condition

G5 may begin only after the G4 content and persistence records are present in
`docs/PROJECT_STATE.md` and the three Git references agree. The G5 entry
check must then freeze, before any formal job:

1. the pilot scenarios, resource budgets, horizons, seeds, and information
   conditions shared by every comparison;
2. the fairness matrix for `sr_mappo_mobile`, `sr_mappo_fixed`,
   `sr_mappo_astar`, `mappo_mobile`, and `sr_mappo_two_stage`;
3. the validation-tuning policy, with sealed-test access still disabled;
4. the paired statistical estimands, exclusion rules, and artifact schemas;
5. an independent audit confirming the frozen methods and statistics before
   any formal training or evaluation output is accepted.

G5 remains a pilot-methods gate. Formal jobs, validation tuning, sealed
evaluation, and thesis claims remain unauthorized until their later gates.
