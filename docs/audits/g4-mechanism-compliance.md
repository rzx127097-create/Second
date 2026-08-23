# G4 Resource-Scarcity Mechanism Compliance Audit

Date: 2026-08-21

## Status

G4 passes at the existing `M2` maturity boundary after corrective final-review
remediation and controller verification. This is diagnostic support-probe
mechanism evidence for limited onboard UAV pesticide, not formal
treatment-effect evidence. G5 is the next authorized gate.

- Gate: `G4` onboard-pesticide scarcity mechanism accepted
- Hardened audit: `status=pass`, final acceptance recorded
- Public algorithm identity: `SR-MAPPO`
- Problem identity: air-ground heterogeneous extension
- Canonical evidence content commit:
  `189e22744579001915919af24ed2bdfd099ff2f2`
- Generator/code commit:
  `09d361994100741a9ae834b63ba07c9b5db953e7`
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
resolvable Git commit/tree provenance; per-file and deterministic source-bundle
hashes; all manifest SHA-256 and byte counts; missing-manifest rejection;
duplicate, traversal, nested-manifest, unsupported-file, realistic G3 endpoint
and execution-flag, and reserved-seed rejections. The regenerated audit reports
`status=pass` with 10 registered evidence artifacts.

Fresh controller verification returned `297 passed in 115.76s` for the full
suite, `76 passed` for `tests/g4`, exit `0` for `git diff --check` and
`python -m compileall -q src scripts`, `[0.05, 0.525]` from the G4 generator,
and `status=pass artifacts=10` from the G4 audit.

## Claim Boundary

The evidence supports only that diagnostic support probes exercised the frozen
onboard-pesticide scarcity mechanism and emitted paired descriptive deltas
under the G2 simulation semantics. It does not support a mobile-treatment
efficacy claim, SR-MAPPO superiority claim, significance claim, formal result,
deployment claim, vehicle-inventory scarcity claim, or G3 actor/checkpoint
execution claim.

## G5 Boundary

G5 may now freeze the pilot protocol and fairness/statistics contracts.
Formal jobs, validation tuning, sealed-test evaluation, thesis efficacy claims,
superiority claims, G3 actor-execution claims, and deployment claims remain
outside the G4 evidence boundary.
