# G4 Final-Review Fix Report

Status: DONE_WITH_CONCERNS

## Scope And Boundary

This remediation was performed on `codex/problem2-g4-resource-scarcity` from
`c0bcfbeda80f341a299ec7e8c751b28dd49ecca8`. It did not access validation
seeds `20000-20049`, sealed seeds `30000-30099`, formal jobs, protected
external assets, or Word files. Pesticide remains the only replenished
resource; battery replenishment remains inactive. No push was performed.

## Root Cause And Fix

The generator executed `scarcity_level_l` as the vehicle's initial inventory
while the frozen contract incorrectly named initial UAV pesticide as the
scarcity axis. The corrected contract freezes
`initial_vehicle_inventory_l` at `1.0`, `6.5`, and `12.0 L`, and separately
records the request-trigger setting `initial_uav_pesticide_l = 0.05 L`.

Current executed arms are labelled `fixed_support_probe` and
`mobile_support_probe`. They are diagnostic support probes, not loaded G3
actor/checkpoint executions. The public project identity remains SR-MAPPO.
The metric labels now state their actual semantics:
`started_service_waiting_time_s` and
`euclidean_service_start_distance_m`.

The audit now validates the exact `3 x 3 x 3` raw matrix per arm, duplicate,
missing, and extra records; raw/summary/probe-matrix/counterfactual equality;
active service-cycle counts; finite metrics and conservation tolerance;
same-input fingerprints; source provenance and frozen-input hashes; manifest
hashes and byte counts; and duplicate or nested manifest paths. The generator
fails closed when Git provenance cannot be resolved.

## TDD Evidence

RED command:

```text
python -m pytest tests/g4 -q
9 failed, 37 passed in 24.96s
```

The intended failures covered the missing executed-axis fields, old support
labels, contract semantic drift acceptance, raw/summary mismatch acceptance,
duplicate manifest paths, manifest-byte drift, and unknown provenance.

GREEN commands:

```text
python -m pytest tests/g4/test_g4_activation.py -q -n 4
7 passed in 23.02s

python -m pytest tests/g4/test_g4_contract.py tests/g4/test_g4_audit.py -q
41 passed in 5.50s
```

## Regenerated Evidence

Generator commit: `5a65bbca1a95bda6db7a4cf9688af755891acac0`
(`fix: harden g4 diagnostic evidence contract`).

Regenerated canonical bundle:

```text
python scripts/run_g4_mechanism_probe.py
[1.0, 12.0]

python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json
status=pass artifacts=10
```

The bundle provenance records source commit `5a65bbc`, source tree
`1f43f3636952019585f5036b56c85a77ae619959`, and corrected contract SHA-256
`dba968f8ff85e071e7029bd9ce0f1e6c6f4249f4d2cf895170115bd75b4adc6c`.

## Commits

- `5a65bbc fix: harden g4 diagnostic evidence contract`

## Remaining Intentional Pending Work

The regenerated `outputs/problem2_sr_mappo_v1/g4` bundle, updated
`HANDOFFG4.md`, updated `docs/PROJECT_STATE.md`, and this report are left
uncommitted after the user interruption. They require controller review,
remaining documentation completion, final verification, local commits, push,
and a real persistence hash. No final remote hash is invented here; G4 remains
pending final acceptance and G5 remains unauthorized.

## Fix Closure

The pending evidence and documentation closure was completed locally on
2026-08-21. `docs/audits/g4-mechanism-compliance.md`, `HANDOFFG4.md`, and the
live decision sections of `docs/PROJECT_STATE.md` now agree that the executed
axis is `initial_vehicle_inventory_l`, `initial_uav_pesticide_l = 0.05 L` is a
separate request-trigger setting, the executed arms are diagnostic support
probes, and no G3 actor/checkpoint execution is claimed. They also retain the
controller-only push and persistence requirement without inventing a hash.

Fresh closure verification:

```text
python -m pytest tests/g4 -q
48 passed in 28.09s

python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json
status=pass artifacts=10

git diff --check
exit 0; no content errors
```

This closure is local only. The controller must still independently review the
commits, push them, verify local/upstream/remote agreement, and record the
actual persistence hash before G4 is accepted or G5 begins.

## Residual Repair

This bounded repair closes the three re-review findings on the frozen G4
contract, Windows-safe manifest duplicate detection, and service-start distance
timing. The regenerated bundle is bound to generator commit
`75e5bcfe64a2fd26c874472f22d43d8dcc6fae9f` (`fix: preserve g4 contract
diagnostics`) and source tree `e49be77ea7c235c0cc6d26714c703506ce85a064`.

RED evidence, before the residual implementation:

```text
python -m pytest tests/g4/test_g4_contract.py::test_g4_contract_rejects_exact_frozen_semantic_drift tests/g4/test_g4_audit.py::test_g4_audit_rejects_case_variant_manifest_path_alias tests/g4/test_g4_activation.py::test_service_start_distance_uses_post_step_vehicle_position -q
6 failed
```

GREEN evidence after the implementation:

```text
python -m pytest tests/g4/test_g4_contract.py::test_g4_contract_rejects_exact_frozen_semantic_drift tests/g4/test_g4_audit.py::test_g4_audit_rejects_case_variant_manifest_path_alias tests/g4/test_g4_activation.py::test_service_start_distance_uses_post_step_vehicle_position -q
6 passed in 0.87s

python -m pytest tests/g4 -q
54 passed in 26.73s
```

Fresh regeneration and audit from `75e5bcf`:

```text
python scripts/run_g4_mechanism_probe.py
[1.0, 12.0]

python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json
status=pass artifacts=10
```

The full repository suite was started with `python -m pytest -q -n 4` but did
not complete within the available execution window and was stopped; it is not
recorded as passing. No push was performed. The controller must independently
verify and push this local evidence/documentation closure before recording an
actual persistence hash or accepting G4.
