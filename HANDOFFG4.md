# HANDOFF G4

Date: 2026-08-21
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g4-resource-scarcity`

## Gate Result

G4 passed at the existing `M2` evidence boundary after final-review
remediation. The accepted evidence is diagnostic support-probe mechanism
evidence only. It does not establish mobile-treatment efficacy, SR-MAPPO
superiority, statistical significance, a formal experiment result, G3 actor
execution, or deployment evidence.

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

## Verified Evidence

- Content/evidence commit:
  `c80541f26a09c82d2bb0ce680016428149e43152`
  (`docs: regenerate g4 evidence for final verification`), pushed to
  `origin/codex/problem2-g4-resource-scarcity`.
- Generator/code commit bound in the canonical artifacts:
  `317fe18c97d37c92d1a71a597139d2b462c3b2e0`
  (`test: cover g4 service-start distance call path`).
- Canonical output root: `outputs/problem2_sr_mappo_v1/g4`.
- Provenance binds source commit `317fe18`, source tree
  `64d6a06049ff0d3ff6302ee9a3287ca50a1735df`, and contract SHA-256
  `dba968f8ff85e071e7029bd9ce0f1e6c6f4249f4d2cf895170115bd75b4adc6c`.
- The audit verifies the exact `3 x 3 x 3` raw matrix per arm, raw/summary and
  counterfactual consistency, active service cycle, common activation window,
  provenance hashes, manifest hashes/bytes, and duplicate-path rejection.
- Fresh controller verification:
  `python -m pytest tests/g4 -q` returned `55 passed`;
  `python -m pytest -q` returned `276 passed`;
  `python -m compileall -q src scripts` exited `0`;
  `git diff --check` exited `0`;
  `python scripts/run_g4_mechanism_probe.py` returned `[1.0, 12.0]`; and the
  G4 audit returned `status=pass artifacts=10`.
- Content-push verification: local HEAD, upstream HEAD, and
  `git ls-remote origin refs/heads/codex/problem2-g4-resource-scarcity` all
  returned `c80541f26a09c82d2bb0ce680016428149e43152` after the content push.

## Claim Boundary

The only permitted claim is that the diagnostic support probes exercised the
frozen vehicle-inventory scarcity mechanism and produced paired descriptive
deltas under the G2 simulation semantics. This is not a mobile-treatment
efficacy, SR-MAPPO superiority, statistical-significance, formal-result,
deployment, or G3 actor-execution claim.

## G5 Entry Condition

G5 may begin as a pilot-protocol freeze gate only. It must freeze, before any
formal job or sealed evaluation:

1. pilot scenarios, resource budgets, horizons, seeds, and information
   conditions shared by every comparison arm;
2. the fairness matrix for `sr_mappo_mobile`, `sr_mappo_fixed`,
   `sr_mappo_astar`, `mappo_mobile`, and `sr_mappo_two_stage`;
3. validation-tuning rules with sealed-test access disabled;
4. paired statistical estimands, exclusion rules, and artifact schemas;
5. an independent audit confirming the frozen methods and statistics.

Formal jobs, validation tuning, sealed evaluation, and thesis
efficacy/superiority claims remain unauthorized until their later gates.
