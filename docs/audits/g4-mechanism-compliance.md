# G4 Resource-Scarcity Mechanism Compliance Audit

Date: 2026-08-21

## Status

G4 passed at `M2` after corrective final-review remediation. This is
diagnostic support-probe mechanism evidence for limited onboard UAV pesticide,
not formal treatment-effect evidence. G5 pilot-protocol freezing is the next
authorized gate after final review and push verification.

- Gate: `G4` onboard-pesticide scarcity mechanism acceptance
- Hardened audit: `pass`
- Public algorithm identity: `SR-MAPPO`
- Problem identity: air-ground heterogeneous extension
- Corrective evidence commit:
  `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5`
- Generator/code commit:
  `0f4003f1d9146187f827537e770a307c22ee687a`
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`
- Matrix: `3 scales x 3 seeds x 3 initial-UAV-pesticide levels` per arm
- Paired diagnostic records: `27`

## Corrected Contract

| Contract item | Frozen or verified condition |
|---|---|
| Resource scope | Pesticide only; battery replenishment is `false` |
| Executed scarcity axis | `initial_uav_pesticide_l` |
| UAV-pesticide levels | `0.05`, `0.2875`, and `0.525 L` |
| G2 usable UAV capacity | `1.08 L`; all G4 levels are within this cap |
| Fixed vehicle inventory | `20.0 L`; not swept and not claimed as scarce |
| Diagnostic arms | `fixed_support_probe`, `mobile_support_probe` |
| Probe scales | `g20x20_d2`, `g20x30_d3`, `g30x30_d3` |
| Probe seeds | `42`, `123`, `2024` |
| Validation and sealed access | `false`; no reserved seed is accessed |
| G3 endpoint reuse | rejected in artifact paths and string values |
| G3 actor/checkpoint execution | `false`; no such execution is claimed |

## Metric Semantics

- `started_service_waiting_time_s` is the wait from request creation until
  service start for requests that reached service start. It is not a censored
  wait for pending requests at horizon end.
- `euclidean_service_start_distance_m` is the Euclidean UAV-vehicle separation
  at service start. It is not vehicle road-travel distance.
- `total_requested_l`, `total_transferred_l`, `final_vehicle_inventory_l`, and
  `vehicle_inventory_used_l` are raw activation fields used to verify that
  active records contain real demand and completed transfer under a fixed
  vehicle-inventory support capability.

## Evidence And Audit Coverage

The activation JSONL is the raw evidence. The audit requires the exact frozen
matrix per arm and rejects missing, duplicate, or extra rows. It verifies raw
records against arm summaries, the root probe matrix, and the recomputed
counterfactual summary; confirms a positive request/reservation/service cycle
for active rows; requires positive requested and transferred pesticide in active
rows; verifies that `initial_uav_pesticide_l` equals `scarcity_level_l`; keeps
`initial_vehicle_inventory_l` fixed at `20.0 L`; requires finite metrics and
conservation error at or below `1e-9 L`; and enforces equal input fingerprints
across each paired row.

The audit also verifies the contract, probe-manifest, and G2-config hashes;
resolvable Git commit/tree provenance; all manifest SHA-256 and byte counts;
missing-manifest rejection; duplicate, traversal, nested-manifest,
unsupported-file, and G3 endpoint-reference rejections. The regenerated audit
reports `status=pass` with 10 registered evidence artifacts.

Fresh controller verification returned `60 passed in 31.80s` for `tests/g4`,
`281 passed in 67.01s` for the full suite, exit `0` for `compileall`, exit `0` for
`git diff --check`, `[0.05, 0.525]` from the G4 generator, and
`status=pass artifacts=10` from the G4 audit.

## Claim Boundary

The evidence supports only that diagnostic support probes exercised the frozen
onboard-pesticide scarcity mechanism and emitted paired descriptive deltas
under the G2 simulation semantics. It does not support a mobile-treatment
efficacy claim, SR-MAPPO superiority claim, significance claim, formal result,
deployment claim, vehicle-inventory scarcity claim, or G3 actor/checkpoint
execution claim.

## G5 Boundary

G5 may freeze the pilot protocol and fairness/statistics contracts only after
final G4 review and push verification. Formal jobs, validation tuning,
sealed-test evaluation, thesis efficacy claims, superiority claims, G3
actor-execution claims, and deployment claims remain outside the G4 evidence
boundary.
