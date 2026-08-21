# HANDOFF G4

Date: 2026-08-21
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g4-resource-scarcity`

## Gate Result

G4 is an `M2` acceptance candidate after corrective final-review remediation.
The candidate evidence is diagnostic support-probe mechanism evidence for
limited onboard UAV pesticide only. It does not establish mobile-treatment
efficacy, SR-MAPPO superiority, statistical significance, a formal experiment
result, vehicle-inventory scarcity, G3 actor execution, or deployment evidence.
Final acceptance remains pending the controller's final review and
non-rewriting push verification.

## Corrected Frozen Interface

- Public algorithm identity: `SR-MAPPO`; Problem 2 remains its air-ground
  heterogeneous extension.
- Executed scarcity axis: `initial_uav_pesticide_l`, sampled at `0.05`,
  `0.2875`, and `0.525 L`.
- The sampled UAV-pesticide band is within the frozen G2 usable UAV capacity
  `1.08 L`.
- Fixed support inventory: `initial_vehicle_inventory_l = 20.0 L`, matching the
  G1 registry and frozen G2 configuration. It is not swept as the scarcity axis.
- Executed arms: `fixed_support_probe` and `mobile_support_probe`. They are
  diagnostic support probes; no G3 actor or checkpoint is loaded or claimed.
- Waiting metric: `started_service_waiting_time_s`, for requests that reached
  service start only.
- Distance metric: `euclidean_service_start_distance_m`, not road distance.
- Resource scope: pesticide only; battery replenishment is inactive.
- Probe scales: `g20x20_d2`, `g20x30_d3`, `g30x30_d3`; seeds `42`, `123`,
  `2024`. Validation and sealed-test partitions remain inaccessible.

## Verified Evidence

- Corrective evidence commit:
  `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5`
  (`docs: regenerate g4 onboard scarcity evidence`).
- Generator/code commit bound in the canonical artifacts:
  `f53b86b05372a142a9b4796db2e7c3fc9be901a1`
  (`perf: cache g4 source bundle verification`).
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`.
- Provenance binds source commit `f53b86b`, source tree
  `743d8cd30508af265a9232dd5b52402d7025ede2`, source bundle SHA-256
  `6e4f959610f9a3ab29eda6cdf44bf3da916f8e4e5db9b6323450bb7c26e28878`, and
  contract SHA-256 `2847f32a64b3d8b80a1e8ec8c5ff56b407ba3abc05cfb1d5780c8a31e18f11ea`.
- The audit verifies the exact `3 x 3 x 3` raw matrix per arm, raw/summary and
  counterfactual consistency, active service cycle, positive request and
  transfer evidence, common activation window, provenance hashes, manifest
  hashes/bytes, missing-manifest rejection, G3 endpoint-reference rejection,
  and duplicate-path rejection.
- Fresh fix-worker verification before controller persistence:
  `python -m pytest tests/g4 -q` returned `70 passed in 69.38s`;
  `python -m pytest -q` returned `291 passed in 105.23s`;
  `python -m compileall -q src scripts` exited `0`;
  `git diff --check` exited `0`;
  `python scripts/run_g4_mechanism_probe.py` returned `[0.05, 0.525]`; and the
  G4 audit returned `status=pass artifacts=10`.

## Claim Boundary

The only permitted claim is that the diagnostic support probes exercised the
frozen onboard-pesticide scarcity mechanism and produced paired descriptive
deltas under the G2 simulation semantics. This is not a mobile-treatment
efficacy, SR-MAPPO superiority, statistical-significance, formal-result,
deployment, vehicle-inventory scarcity, or G3 actor-execution claim.

## G5 Entry Condition

G5 is not authorized. It may begin as a pilot-protocol freeze gate only after
final G4 review and non-rewriting push verification. It must freeze, before
any formal job or sealed evaluation:

1. pilot scenarios, resource budgets, horizons, seeds, and information
   conditions shared by every comparison arm;
2. the fairness matrix for `sr_mappo_mobile`, `sr_mappo_fixed`,
   `sr_mappo_astar`, `mappo_mobile`, and `sr_mappo_two_stage`;
3. validation-tuning rules with sealed-test access disabled;
4. paired statistical estimands, exclusion rules, and artifact schemas;
5. an independent audit confirming the frozen methods and statistics.

Formal jobs, validation tuning, sealed evaluation, and thesis
efficacy/superiority claims remain unauthorized until their later gates.
