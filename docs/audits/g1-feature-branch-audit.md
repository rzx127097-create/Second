# G1 Candidate Branch Audit

> Read-only Git-object audit. `status=pass` means the audit executed successfully;
> it does not accept candidate maturity claims or implementation evidence.

## Identity And Provenance

- Base ref: `origin/main`
- Base commit: `2643753855c385253951dfad2c225be0b09b7e00`
- Candidate ref: `origin/feature/problem2-code-framework`
- Candidate commit: `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`
- Generator commit: `667ffcf74d625261a0fb0970df1db0e5c0d13a34`
- Auditor SHA-256: `1d05c29a1addf029d6040e41219bed7d2a0a6edc50adf885e7f6e9545ec4f72f`
- Auditor version: `g1-candidate-final-review-remediation.v1`
- Generated UTC: `2026-08-20T10:35:58.060407+00:00`
- Read-only: `True`
- Current maturity: `M1`
- Current gate: `G1`

## Inventory

- Changed paths: `210`
- Rendered changed paths: `210`
- Omitted changed paths: `0`
- Candidate tree paths: `239`
- Changed class counts: `{"configuration": 11, "documentation": 21, "report": 20, "source": 110, "test": 48}`
- Admissibility counts: `{"admissible_design_input": 21, "not_admissible_as_evidence": 20, "requires_independent_reverification": 169}`

## Contract Inspection

- `parameter` `configs/parameter_registry.yaml` blob `db6257d4387afd443a173a204ea9b26b14d289ef`: complete=`True`, missing=`[]`, conflicts=`["uav_onboard_pesticide is not independently verified", "uav_spray_flow is not independently verified", "uav_usable_fraction is not independently verified", "uav_speed is not independently verified", "vehicle_inventory is not independently verified", "vehicle_transfer_rate is not independently verified", "vehicle_service_capacity is not independently verified", "service_setup_time is not independently verified", "request_safety_margin is not independently verified", "rendezvous_radius is not independently verified", "vehicle_speed is not independently verified", "decision_dt is not independently verified"]`
- `seed` `configs/scenarios.yaml` blob `925bdb72e3bc990e7a1be20abc2a5d82e62528c9`: complete=`True`, missing=`[]`, conflicts=`["candidate sealed-test seed offsets do not match the locked 30000-30099 range"]`
- `experiment` `configs/experiments/formal_matrix.yaml` blob `905b9e15511e03d4d9b59ea8457ecb425c2e5ddd`: complete=`True`, missing=`[]`, conflicts=`["candidate training seeds [0, 1, 2, 3, 4] conflict with frozen G1 seeds [42, 123, 2024, 3407, 7919]", "candidate scale IDs do not match the frozen six-scale G1 protocol"]`
- `artifact` `src/problem2/artifacts/evidence_manifest.py` blob `eba995288a2d9896191d1a924d3c42380fd8f80b`: complete=`True`, missing=`[]`, conflicts=`["candidate artifact generator code is not an accepted G1 artifact schema"]`
- `sealed` `src/problem2/experiments/freeze.py` blob `3930e35178f182c8b1e4583fc93eeb5bdcfa896e`: complete=`True`, missing=`[]`, conflicts=`["candidate executable sealed-unlock implementation remains unavailable at M1/G1"]`

Candidate training seeds `[0, 1, 2, 3, 4]` conflict with frozen G1 seeds `[42, 123, 2024, 3407, 7919]`.

## Maturity Scan

- `\bM[234]\b`: 152 match(es)
- `formal experiments show`: 0 match(es)
- `significantly outperforms`: 0 match(es)
- `\bproves?\b`: 2 match(es)
- `real deployment verified`: 0 match(es)
- `universally optimal`: 0 match(es)

## Forbidden-Name Scan

- `HAPPO`: 16 match(es)
- `happpo`: 4 match(es)
- `AG-SR-MAPPO`: 14 match(es)

Guardrail mentions are recorded separately from substantive references; neither introduces a current implementation or public rename.

## Unresolved Findings

- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "uav_onboard_pesticide is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "uav_spray_flow is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "uav_usable_fraction is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "uav_speed is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "vehicle_inventory is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "vehicle_transfer_rate is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "vehicle_service_capacity is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "service_setup_time is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "request_safety_margin is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "rendezvous_radius is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "vehicle_speed is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_parameter_contract_conflict`: `{"code": "candidate_parameter_contract_conflict", "detail": "decision_dt is not independently verified", "path": "configs/parameter_registry.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_seed_contract_conflict`: `{"code": "candidate_seed_contract_conflict", "detail": "candidate sealed-test seed offsets do not match the locked 30000-30099 range", "path": "configs/scenarios.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_experiment_contract_conflict`: `{"code": "candidate_experiment_contract_conflict", "detail": "candidate training seeds [0, 1, 2, 3, 4] conflict with frozen G1 seeds [42, 123, 2024, 3407, 7919]", "path": "configs/experiments/formal_matrix.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_experiment_contract_conflict`: `{"code": "candidate_experiment_contract_conflict", "detail": "candidate scale IDs do not match the frozen six-scale G1 protocol", "path": "configs/experiments/formal_matrix.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_training_seed_conflict`: `{"candidate_value": [0, 1, 2, 3, 4], "code": "candidate_training_seed_conflict", "g1_value": [42, 123, 2024, 3407, 7919], "path": "configs/experiments/formal_matrix.yaml", "resolution": "requires_independent_reverification"}`
- `candidate_artifact_contract_conflict`: `{"code": "candidate_artifact_contract_conflict", "detail": "candidate artifact generator code is not an accepted G1 artifact schema", "path": "src/problem2/artifacts/evidence_manifest.py", "resolution": "requires_independent_reverification"}`
- `candidate_sealed_contract_conflict`: `{"code": "candidate_sealed_contract_conflict", "detail": "candidate executable sealed-unlock implementation remains unavailable at M1/G1", "path": "src/problem2/experiments/freeze.py", "resolution": "requires_independent_reverification"}`
- `candidate_forbidden_name_substantive_references`: `{"code": "candidate_forbidden_name_substantive_references", "count": 10, "resolution": "not_admissible_as_evidence"}`
- `candidate_premature_maturity_claims`: `{"code": "candidate_premature_maturity_claims", "count": 154, "resolution": "not_admissible_as_evidence"}`

## Changed-Path Classification

- `A` `.gitignore` -> `configuration` / `requires_independent_reverification`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-1-report.md` -> `documentation` / `admissible_design_input`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-3-report.md` -> `documentation` / `admissible_design_input`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-4-report.md` -> `documentation` / `admissible_design_input`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-5-report.md` -> `documentation` / `admissible_design_input`
- `M` `README.md` -> `documentation` / `admissible_design_input`
- `A` `configs/algorithms/sr_mappo.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/environment.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/experiments/chapter4_5.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/experiments/formal_matrix.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/field_dynamics.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/parameter_registry.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/scales.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/scenarios.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `configs/simulation_profile.yaml` -> `configuration` / `requires_independent_reverification`
- `A` `data/roads/jodhpur_cropped_metric.graphml` -> `documentation` / `admissible_design_input`
- `A` `docs/evidence/field-dynamics-calibration-plan.md` -> `documentation` / `admissible_design_input`
- `A` `docs/evidence/parameter-source-ledger.yaml` -> `documentation` / `admissible_design_input`
- `A` `docs/evidence/search-log-2026-08-15.md` -> `documentation` / `admissible_design_input`
- `A` `docs/plans/2026-08-14-problem2-code-framework.md` -> `documentation` / `admissible_design_input`
- `A` `docs/plans/2026-08-14-section-4-2-integration.md` -> `documentation` / `admissible_design_input`
- `A` `docs/plans/2026-08-14-section-4-3-demand-rendezvous.md` -> `documentation` / `admissible_design_input`
- `A` `docs/plans/2026-08-14-section-4-4-sr-mappo.md` -> `documentation` / `admissible_design_input`
- `A` `docs/plans/2026-08-14-section-4-5-experiment-system.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/plans/2026-08-14-complete-problem2-project.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/plans/2026-08-14-section-4-4-integration.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/plans/2026-08-15-formal-readiness.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/plans/2026-08-17-simulation-preflight-implementation.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/plans/2026-08-18-m3-pilot-pipeline.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/specs/2026-08-17-simulation-preflight-design.md` -> `documentation` / `admissible_design_input`
- `A` `docs/superpowers/specs/2026-08-18-m3-pilot-pipeline-design.md` -> `documentation` / `admissible_design_input`
- `A` `docs/verification/complete-project-runbook.md` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/field-dynamics-hash.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/formal-readiness-after-fixes.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/formal-readiness-final.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/formal-readiness-report.md` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/formal-readiness-web-evidence.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/formal-readiness-with-pilot.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/frozen-road-jodhpur.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/parameter-audit-after-fixes.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/parameter-audit-web-evidence.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/parameter-audit.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/readiness-with-resource.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/readiness-without-resource.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/resource-pilot-frozen.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/road-audit-frozen.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/road-audit-jodhpur.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/scenario-audit-after-fixes.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/scenario-audit.json` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/section-4-5-runbook.md` -> `report` / `not_admissible_as_evidence`
- `A` `docs/verification/step4-shared-validation-report.md` -> `report` / `not_admissible_as_evidence`
- `A` `pyproject.toml` -> `configuration` / `requires_independent_reverification`
- `A` `scripts/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/analyze_paired_results.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_m3_pilot.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_parameters.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_readiness.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_resource_activation.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_road_source.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_scenarios.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/audit_simulation_preflight.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/build_artifacts.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/build_chapter45_artifacts.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/build_frozen_road.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/build_m3_pilot_artifacts.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/evaluate.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/evaluate_matrix.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/freeze_sealed_test.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/prepare_m3_pilot.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/run_matrix.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/run_resource_pilot.py` -> `source` / `requires_independent_reverification`
- `A` `scripts/train.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/common/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/common/checkpoint.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/common/gae.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/common/masked_distribution.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/common/normalization.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/actors.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/algorithm.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/critic.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/losses.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/rollout.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/algorithms/sr_mappo/trainer.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/chapter45.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/evidence_manifest.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/figures.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/m3_pilot.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/statistics.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/summarize.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/tables.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/artifacts/validate_logs.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/fixed_support.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/policies.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/priority_dispatch.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/rolling_astar.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/teleport_service.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/baselines/unlimited_supply.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/config.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/candidate_slots.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/endurance.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/eta.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/feasibility.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/planning.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/rendezvous.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/demand/urgency.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/events.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/requests.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/resources.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/state.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/types.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/domain/units.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/action_masks.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/air_ground_env.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/movement.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/observations.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/rewards.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/service_state_machine.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/environment/transition.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/evaluation.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/freeze.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/job_identity.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/m3_audit.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/m3_pilot.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/methods.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/metrics.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/orchestrator.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/policy_protocol.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/process.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/process_liveness.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/readiness.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/recovery.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/resource_activation.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/rollout_runner.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/runner.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/simulation_preflight.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/experiments/specification.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/field/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/field/pest_dynamics.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/field/pesticide_field.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/field/wind_field.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/graph.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/graphml.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/projection.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/shortest_path.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/road/topology.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/scenarios/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/scenarios/factory.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/scenarios/interventions.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/section4_2/__init__.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/section4_2/adapter.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/section4_2/audit.py` -> `source` / `requires_independent_reverification`
- `A` `src/problem2/section4_2/road_executor.py` -> `source` / `requires_independent_reverification`
- `A` `tests/artifacts/test_traceability.py` -> `test` / `requires_independent_reverification`
- `A` `tests/baselines/test_baselines.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_artifact_pipeline.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_baseline_protocol.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_chapter45_smoke.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_cli_and_recovery.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_complete_project.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_evaluation_smoke.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_frozen_gis_factory.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_review_fixes.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_scenario_factory.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_training_methods.py` -> `test` / `requires_independent_reverification`
- `A` `tests/e2e/test_training_smoke.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_chapter45_artifacts.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_experiment_specification.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_m3_artifacts.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_m3_pilot.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_method_profiles.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_metrics_and_activation.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_orchestrator.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_parameter_audit.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_readiness_gate.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_resource_pilot.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_scenario_audit.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_scenario_interventions.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_sealed_freeze.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_simulation_preflight.py` -> `test` / `requires_independent_reverification`
- `A` `tests/experiments/test_statistics.py` -> `test` / `requires_independent_reverification`
- `A` `tests/integration/test_environment_step.py` -> `test` / `requires_independent_reverification`
- `A` `tests/integration/test_job_recovery.py` -> `test` / `requires_independent_reverification`
- `A` `tests/integration/test_section_4_2_integration.py` -> `test` / `requires_independent_reverification`
- `A` `tests/m3_fixtures.py` -> `test` / `requires_independent_reverification`
- `A` `tests/marl/test_checkpoint_roundtrip.py` -> `test` / `requires_independent_reverification`
- `A` `tests/marl/test_masks_and_gae.py` -> `test` / `requires_independent_reverification`
- `A` `tests/marl/test_role_gradient_isolation.py` -> `test` / `requires_independent_reverification`
- `A` `tests/marl/test_sr_mappo_contract.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_config.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_conservation.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_field_dynamics.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_graphml_audit.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_observations_masks.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_rendezvous.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_requests.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_resources.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_rewards.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_road_demand_helpers.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_road_graph.py` -> `test` / `requires_independent_reverification`
- `A` `tests/unit/test_section_4_3_demand.py` -> `test` / `requires_independent_reverification`

## Boundary

- Training executed: `False`.
- Sealed-test scenarios accessed: `False`.
- OSM inputs remain simulation inputs, not field-deployment evidence.
- Candidate M2/M3/M4 code and claims remain unaccepted.

Candidate-branch assets are design or candidate implementation inputs only; no M2/M3/M4 claim is accepted in the current G1 branch without fresh, branch-local verification.

## Commands

- `["git", "rev-parse", "origin/main"]` -> return `0` (`ok`)
- `["git", "rev-parse", "origin/feature/problem2-code-framework"]` -> return `0` (`ok`)
- `["git", "rev-parse", "HEAD"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "diff", "--name-status", "-z", "origin/main...origin/feature/problem2-code-framework"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-r", "-z", "--name-only", "origin/feature/problem2-code-framework"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "\\bM[234]\\b", "origin/feature/problem2-code-framework", "--", "."]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "formal experiments show", "origin/feature/problem2-code-framework", "--", "."]` -> return `1` (`no_match`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "significantly outperforms", "origin/feature/problem2-code-framework", "--", "."]` -> return `1` (`no_match`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "\\bproves?\\b", "origin/feature/problem2-code-framework", "--", "."]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "real deployment verified", "origin/feature/problem2-code-framework", "--", "."]` -> return `1` (`no_match`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "universally optimal", "origin/feature/problem2-code-framework", "--", "."]` -> return `1` (`no_match`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "HAPPO", "origin/feature/problem2-code-framework", "--", "."]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "happpo", "origin/feature/problem2-code-framework", "--", "."]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "grep", "-n", "-I", "-E", "AG\\-SR\\-MAPPO", "origin/feature/problem2-code-framework", "--", "."]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-z", "origin/feature/problem2-code-framework", "--", "configs/parameter_registry.yaml"]` -> return `0` (`ok`)
- `["git", "show", "origin/feature/problem2-code-framework:configs/parameter_registry.yaml"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-z", "origin/feature/problem2-code-framework", "--", "configs/scenarios.yaml"]` -> return `0` (`ok`)
- `["git", "show", "origin/feature/problem2-code-framework:configs/scenarios.yaml"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-z", "origin/feature/problem2-code-framework", "--", "configs/experiments/formal_matrix.yaml"]` -> return `0` (`ok`)
- `["git", "show", "origin/feature/problem2-code-framework:configs/experiments/formal_matrix.yaml"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-z", "origin/feature/problem2-code-framework", "--", "src/problem2/artifacts/evidence_manifest.py"]` -> return `0` (`ok`)
- `["git", "show", "origin/feature/problem2-code-framework:src/problem2/artifacts/evidence_manifest.py"]` -> return `0` (`ok`)
- `["git", "-c", "core.quotepath=false", "ls-tree", "-z", "origin/feature/problem2-code-framework", "--", "src/problem2/experiments/freeze.py"]` -> return `0` (`ok`)
- `["git", "show", "origin/feature/problem2-code-framework:src/problem2/experiments/freeze.py"]` -> return `0` (`ok`)
