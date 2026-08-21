# G4 Resource-Scarcity Mechanism Compliance Audit

Date: 2026-08-21

## Status

This is a local final-review remediation record, not G4 gate acceptance. The
regenerated bundle passes the hardened G4 audit, but controller-run independent
verification, push, and persistence confirmation remain required. G5 is not
authorized.

- Gate: `G4` final-review remediation
- Local audit: `pass`
- Public algorithm identity: `SR-MAPPO`
- Problem identity: air-ground heterogeneous extension
- Generator commit: `5a65bbca1a95bda6db7a4cf9688af755891acac0`
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`
- Matrix: `3 scales x 3 seeds x 3 vehicle-inventory levels` per arm
- Paired diagnostic records: `27`

## Corrected Contract

| Contract item | Frozen or verified condition |
|---|---|
| Resource scope | Pesticide only; battery replenishment is `false` |
| Executed scarcity axis | `initial_vehicle_inventory_l` |
| Vehicle-inventory levels | `1.0`, `6.5`, and `12.0 L` |
| Request-trigger setting | `initial_uav_pesticide_l = 0.05 L` |
| Diagnostic arms | `fixed_support_probe`, `mobile_support_probe` |
| Probe scales | `g20x20_d2`, `g20x30_d3`, `g30x30_d3` |
| Probe seeds | `42`, `123`, `2024` |
| Validation and sealed access | `false`; no reserved seed is accessed |
| G3 endpoint reuse | rejected |
| G3 actor/checkpoint execution | `false`; no such execution is claimed |

## Metric Semantics

- `started_service_waiting_time_s` is the wait from request creation until
  service start for requests that reached service start. It is not a censored
  wait for pending requests at horizon end.
- `euclidean_service_start_distance_m` is the Euclidean UAV-vehicle separation
  at service start. It is not vehicle road-travel distance.

## Evidence And Audit Coverage

The activation JSONL is the raw evidence. The audit requires the exact frozen
matrix per arm and rejects missing, duplicate, or extra rows. It verifies raw
records against arm summaries, the root probe matrix, and the recomputed
counterfactual summary; confirms a positive request/reservation/service cycle
for active rows; requires finite metrics and conservation error at or below
`1e-9 L`; and enforces equal input fingerprints across each paired row.

The audit also verifies the contract, probe-manifest, and G2-config hashes;
resolvable Git commit/tree provenance; all manifest SHA-256 and byte counts;
and duplicate, traversal, nested-manifest, unsupported-file, and G3-path
rejections. The regenerated audit reports `status=pass` with 10 registered
evidence artifacts.

## Claim Boundary

The evidence supports only that diagnostic support probes exercised the frozen
vehicle-inventory scarcity mechanism and emitted paired descriptive deltas
under the G2 simulation semantics. It does not support a mobile-treatment
efficacy claim, SR-MAPPO superiority claim, significance claim, formal result,
deployment claim, or G3 actor/checkpoint execution claim.

## Required Controller Follow-Up

The controller must independently verify the local commits, push without
rewriting history, confirm local/upstream/remote hash agreement, and then add
the actual persistence hash to `docs/PROJECT_STATE.md`. No post-remediation
remote or persistence hash is recorded here.
