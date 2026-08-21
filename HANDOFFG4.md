# HANDOFF G4

Date: 2026-08-21
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g4-resource-scarcity`

## Gate Status

G4 is not accepted and G5 is not authorized. The final-review remediation is
locally complete and the regenerated diagnostic bundle passes its hardened
audit, but controller-run independent verification and push/persistence
confirmation remain required.

## Corrected Frozen Interface

- Public algorithm identity: `SR-MAPPO`; Problem 2 remains its air-ground
  heterogeneous extension.
- Executed scarcity axis: `initial_vehicle_inventory_l`, sampled at `1.0`,
  `6.5`, and `12.0 L`.
- Separate frozen request-trigger setting: `initial_uav_pesticide_l = 0.05 L`.
- Executed arms: `fixed_support_probe` and `mobile_support_probe`. They are
  diagnostic support probes; no G3 actor or checkpoint is loaded or claimed.
- Waiting metric: `started_service_waiting_time_s`, for requests that reached
  service start only.
- Distance metric: `euclidean_service_start_distance_m`, not road distance.
- Resource scope: pesticide only; battery replenishment is inactive.
- Probe scales: `g20x20_d2`, `g20x30_d3`, `g30x30_d3`; seeds `42`, `123`,
  `2024`. Validation and sealed-test partitions remain inaccessible.

## Local Evidence

- Fixed-generator commit: `5a65bbca1a95bda6db7a4cf9688af755891acac0`
  (`fix: harden g4 diagnostic evidence contract`).
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`.
- Provenance binds source commit `5a65bbc`, source tree
  `1f43f3636952019585f5036b56c85a77ae619959`, and contract SHA-256
  `dba968f8ff85e071e7029bd9ce0f1e6c6f4249f4d2cf895170115bd75b4adc6c`.
- The audit verifies the exact `3 x 3 x 3` raw matrix per arm, raw/summary and
  counterfactual consistency, active service cycle, common activation window,
  provenance hashes, manifest hashes/bytes, and duplicate-path rejection.

## Claim Boundary

The only permitted claim is that the diagnostic support probes exercised the
frozen vehicle-inventory scarcity mechanism and produced paired descriptive
deltas under the G2 simulation semantics. This is not a mobile-treatment
efficacy, SR-MAPPO superiority, statistical-significance, formal-result,
deployment, or G3 actor-execution claim.

## Controller Follow-Up

1. Run the independent final verification against the local commits.
2. Push the content and persistence commits without rewriting history.
3. Verify local, upstream, and `git ls-remote` hashes agree.
4. Add the actual pushed persistence hash to `docs/PROJECT_STATE.md`.

No final remote or persistence hash is recorded here because this worker did
not push.
