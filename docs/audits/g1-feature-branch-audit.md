# G1 Candidate Branch Audit

> Read-only Git-object audit. This report classifies candidate assets;
> it does not accept candidate maturity claims as current evidence.

## Identity

- Base ref: `origin/main`
- Base commit: `2643753855c385253951dfad2c225be0b09b7e00`
- Candidate ref: `origin/feature/problem2-code-framework`
- Candidate commit: `52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`
- Read-only: `True`
- Current maturity: `M1`
- Current gate: `G1`

## Inventory

- Changed paths: `210`
- Candidate tree paths: `239`
- Changed class counts: `{"configuration": 9, "documentation": 43, "report": 20, "source": 90, "test": 48}`

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

## Changed-Path Classification

- `A` `.gitignore` -> `documentation`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-1-report.md` -> `documentation`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-3-report.md` -> `documentation`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-4-report.md` -> `documentation`
- `A` `.superpowers/sdd/2026-08-14-complete-problem2-project/task-5-report.md` -> `documentation`
- `M` `README.md` -> `documentation`
- `A` `configs/algorithms/sr_mappo.yaml` -> `configuration`
- `A` `configs/environment.yaml` -> `configuration`
- `A` `configs/experiments/chapter4_5.yaml` -> `configuration`
- `A` `configs/experiments/formal_matrix.yaml` -> `configuration`
- `A` `configs/field_dynamics.yaml` -> `configuration`
- `A` `configs/parameter_registry.yaml` -> `configuration`
- `A` `configs/scales.yaml` -> `configuration`
- `A` `configs/scenarios.yaml` -> `configuration`
- `A` `configs/simulation_profile.yaml` -> `configuration`
- `A` `data/roads/jodhpur_cropped_metric.graphml` -> `documentation`
- `A` `docs/evidence/field-dynamics-calibration-plan.md` -> `documentation`
- `A` `docs/evidence/parameter-source-ledger.yaml` -> `documentation`
- `A` `docs/evidence/search-log-2026-08-15.md` -> `documentation`
- `A` `docs/plans/2026-08-14-problem2-code-framework.md` -> `documentation`
- `A` `docs/plans/2026-08-14-section-4-2-integration.md` -> `documentation`
- `A` `docs/plans/2026-08-14-section-4-3-demand-rendezvous.md` -> `documentation`
- `A` `docs/plans/2026-08-14-section-4-4-sr-mappo.md` -> `documentation`
- `A` `docs/plans/2026-08-14-section-4-5-experiment-system.md` -> `documentation`
- `A` `docs/superpowers/plans/2026-08-14-complete-problem2-project.md` -> `documentation`
- `A` `docs/superpowers/plans/2026-08-14-section-4-4-integration.md` -> `documentation`
- `A` `docs/superpowers/plans/2026-08-15-formal-readiness.md` -> `documentation`
- `A` `docs/superpowers/plans/2026-08-17-simulation-preflight-implementation.md` -> `documentation`
- `A` `docs/superpowers/plans/2026-08-18-m3-pilot-pipeline.md` -> `documentation`
- `A` `docs/superpowers/specs/2026-08-17-simulation-preflight-design.md` -> `documentation`
- `A` `docs/superpowers/specs/2026-08-18-m3-pilot-pipeline-design.md` -> `documentation`
- `A` `docs/verification/complete-project-runbook.md` -> `report`
- `A` `docs/verification/field-dynamics-hash.json` -> `report`
- `A` `docs/verification/formal-readiness-after-fixes.json` -> `report`
- `A` `docs/verification/formal-readiness-final.json` -> `report`
- `A` `docs/verification/formal-readiness-report.md` -> `report`
- `A` `docs/verification/formal-readiness-web-evidence.json` -> `report`
- `A` `docs/verification/formal-readiness-with-pilot.json` -> `report`
- `A` `docs/verification/frozen-road-jodhpur.json` -> `report`
- `A` `docs/verification/parameter-audit-after-fixes.json` -> `report`
- `A` `docs/verification/parameter-audit-web-evidence.json` -> `report`
- `A` `docs/verification/parameter-audit.json` -> `report`
- `A` `docs/verification/readiness-with-resource.json` -> `report`
- `A` `docs/verification/readiness-without-resource.json` -> `report`
- `A` `docs/verification/resource-pilot-frozen.json` -> `report`
- `A` `docs/verification/road-audit-frozen.json` -> `report`
- `A` `docs/verification/road-audit-jodhpur.json` -> `report`
- `A` `docs/verification/scenario-audit-after-fixes.json` -> `report`
- `A` `docs/verification/scenario-audit.json` -> `report`
- `A` `docs/verification/section-4-5-runbook.md` -> `report`
- `A` `docs/verification/step4-shared-validation-report.md` -> `report`
- `A` `pyproject.toml` -> `documentation`
- `A` `scripts/__init__.py` -> `documentation`
- `A` `scripts/analyze_paired_results.py` -> `documentation`
- `A` `scripts/audit_m3_pilot.py` -> `documentation`
- `A` `scripts/audit_parameters.py` -> `documentation`
- `A` `scripts/audit_readiness.py` -> `documentation`
- `A` `scripts/audit_resource_activation.py` -> `documentation`
- `A` `scripts/audit_road_source.py` -> `documentation`
- `A` `scripts/audit_scenarios.py` -> `documentation`
- `A` `scripts/audit_simulation_preflight.py` -> `documentation`
- `A` `scripts/build_artifacts.py` -> `documentation`
- `A` `scripts/build_chapter45_artifacts.py` -> `documentation`
- `A` `scripts/build_frozen_road.py` -> `documentation`
- `A` `scripts/build_m3_pilot_artifacts.py` -> `documentation`
- `A` `scripts/evaluate.py` -> `documentation`
- `A` `scripts/evaluate_matrix.py` -> `documentation`
- `A` `scripts/freeze_sealed_test.py` -> `documentation`
- `A` `scripts/prepare_m3_pilot.py` -> `documentation`
- `A` `scripts/run_matrix.py` -> `documentation`
- `A` `scripts/run_resource_pilot.py` -> `documentation`
- `A` `scripts/train.py` -> `documentation`
- `A` `src/problem2/__init__.py` -> `source`
- `A` `src/problem2/algorithms/__init__.py` -> `source`
- `A` `src/problem2/algorithms/common/__init__.py` -> `source`
- `A` `src/problem2/algorithms/common/checkpoint.py` -> `source`
- `A` `src/problem2/algorithms/common/gae.py` -> `source`
- `A` `src/problem2/algorithms/common/masked_distribution.py` -> `source`
- `A` `src/problem2/algorithms/common/normalization.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/__init__.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/actors.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/algorithm.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/critic.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/losses.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/rollout.py` -> `source`
- `A` `src/problem2/algorithms/sr_mappo/trainer.py` -> `source`
- `A` `src/problem2/artifacts/__init__.py` -> `source`
- `A` `src/problem2/artifacts/chapter45.py` -> `source`
- `A` `src/problem2/artifacts/evidence_manifest.py` -> `source`
- `A` `src/problem2/artifacts/figures.py` -> `source`
- `A` `src/problem2/artifacts/m3_pilot.py` -> `source`
- `A` `src/problem2/artifacts/statistics.py` -> `source`
- `A` `src/problem2/artifacts/summarize.py` -> `source`
- `A` `src/problem2/artifacts/tables.py` -> `source`
- `A` `src/problem2/artifacts/validate_logs.py` -> `source`
- `A` `src/problem2/baselines/__init__.py` -> `source`
- `A` `src/problem2/baselines/fixed_support.py` -> `source`
- `A` `src/problem2/baselines/policies.py` -> `source`
- `A` `src/problem2/baselines/priority_dispatch.py` -> `source`
- `A` `src/problem2/baselines/rolling_astar.py` -> `source`
- `A` `src/problem2/baselines/teleport_service.py` -> `source`
- `A` `src/problem2/baselines/unlimited_supply.py` -> `source`
- `A` `src/problem2/config.py` -> `source`
- `A` `src/problem2/demand/__init__.py` -> `source`
- `A` `src/problem2/demand/candidate_slots.py` -> `source`
- `A` `src/problem2/demand/endurance.py` -> `source`
- `A` `src/problem2/demand/eta.py` -> `source`
- `A` `src/problem2/demand/feasibility.py` -> `source`
- `A` `src/problem2/demand/planning.py` -> `source`
- `A` `src/problem2/demand/rendezvous.py` -> `source`
- `A` `src/problem2/demand/urgency.py` -> `source`
- `A` `src/problem2/domain/__init__.py` -> `source`
- `A` `src/problem2/domain/events.py` -> `source`
- `A` `src/problem2/domain/requests.py` -> `source`
- `A` `src/problem2/domain/resources.py` -> `source`
- `A` `src/problem2/domain/state.py` -> `source`
- `A` `src/problem2/domain/types.py` -> `source`
- `A` `src/problem2/domain/units.py` -> `source`
- `A` `src/problem2/environment/__init__.py` -> `source`
- `A` `src/problem2/environment/action_masks.py` -> `source`
- `A` `src/problem2/environment/air_ground_env.py` -> `source`
- `A` `src/problem2/environment/movement.py` -> `source`
- `A` `src/problem2/environment/observations.py` -> `source`
- `A` `src/problem2/environment/rewards.py` -> `source`
- `A` `src/problem2/environment/service_state_machine.py` -> `source`
- `A` `src/problem2/environment/transition.py` -> `source`
- `A` `src/problem2/experiments/__init__.py` -> `source`
- `A` `src/problem2/experiments/evaluation.py` -> `source`
- `A` `src/problem2/experiments/freeze.py` -> `source`
- `A` `src/problem2/experiments/job_identity.py` -> `source`
- `A` `src/problem2/experiments/m3_audit.py` -> `source`
- `A` `src/problem2/experiments/m3_pilot.py` -> `source`
- `A` `src/problem2/experiments/methods.py` -> `source`
- `A` `src/problem2/experiments/metrics.py` -> `source`
- `A` `src/problem2/experiments/orchestrator.py` -> `source`
- `A` `src/problem2/experiments/policy_protocol.py` -> `source`
- `A` `src/problem2/experiments/process.py` -> `source`
- `A` `src/problem2/experiments/process_liveness.py` -> `source`
- `A` `src/problem2/experiments/readiness.py` -> `source`
- `A` `src/problem2/experiments/recovery.py` -> `source`
- `A` `src/problem2/experiments/resource_activation.py` -> `source`
- `A` `src/problem2/experiments/rollout_runner.py` -> `source`
- `A` `src/problem2/experiments/runner.py` -> `source`
- `A` `src/problem2/experiments/simulation_preflight.py` -> `source`
- `A` `src/problem2/experiments/specification.py` -> `source`
- `A` `src/problem2/field/__init__.py` -> `source`
- `A` `src/problem2/field/pest_dynamics.py` -> `source`
- `A` `src/problem2/field/pesticide_field.py` -> `source`
- `A` `src/problem2/field/wind_field.py` -> `source`
- `A` `src/problem2/road/__init__.py` -> `source`
- `A` `src/problem2/road/graph.py` -> `source`
- `A` `src/problem2/road/graphml.py` -> `source`
- `A` `src/problem2/road/projection.py` -> `source`
- `A` `src/problem2/road/shortest_path.py` -> `source`
- `A` `src/problem2/road/topology.py` -> `source`
- `A` `src/problem2/scenarios/__init__.py` -> `source`
- `A` `src/problem2/scenarios/factory.py` -> `source`
- `A` `src/problem2/scenarios/interventions.py` -> `source`
- `A` `src/problem2/section4_2/__init__.py` -> `source`
- `A` `src/problem2/section4_2/adapter.py` -> `source`
- `A` `src/problem2/section4_2/audit.py` -> `source`
- `A` `src/problem2/section4_2/road_executor.py` -> `source`
- `A` `tests/artifacts/test_traceability.py` -> `test`
- `A` `tests/baselines/test_baselines.py` -> `test`
- `A` `tests/e2e/test_artifact_pipeline.py` -> `test`
- `A` `tests/e2e/test_baseline_protocol.py` -> `test`
- `A` `tests/e2e/test_chapter45_smoke.py` -> `test`
- `A` `tests/e2e/test_cli_and_recovery.py` -> `test`
- `A` `tests/e2e/test_complete_project.py` -> `test`
- `A` `tests/e2e/test_evaluation_smoke.py` -> `test`
- `A` `tests/e2e/test_frozen_gis_factory.py` -> `test`
- `A` `tests/e2e/test_review_fixes.py` -> `test`
- `A` `tests/e2e/test_scenario_factory.py` -> `test`
- `A` `tests/e2e/test_training_methods.py` -> `test`
- `A` `tests/e2e/test_training_smoke.py` -> `test`
- `A` `tests/experiments/test_chapter45_artifacts.py` -> `test`
- `A` `tests/experiments/test_experiment_specification.py` -> `test`
- `A` `tests/experiments/test_m3_artifacts.py` -> `test`
- `A` `tests/experiments/test_m3_pilot.py` -> `test`
- `A` `tests/experiments/test_method_profiles.py` -> `test`
- `A` `tests/experiments/test_metrics_and_activation.py` -> `test`
- `A` `tests/experiments/test_orchestrator.py` -> `test`
- `A` `tests/experiments/test_parameter_audit.py` -> `test`
- `A` `tests/experiments/test_readiness_gate.py` -> `test`
- `A` `tests/experiments/test_resource_pilot.py` -> `test`
- `A` `tests/experiments/test_scenario_audit.py` -> `test`
- `A` `tests/experiments/test_scenario_interventions.py` -> `test`
- `A` `tests/experiments/test_sealed_freeze.py` -> `test`
- `A` `tests/experiments/test_simulation_preflight.py` -> `test`
- `A` `tests/experiments/test_statistics.py` -> `test`
- `A` `tests/integration/test_environment_step.py` -> `test`
- `A` `tests/integration/test_job_recovery.py` -> `test`
- `A` `tests/integration/test_section_4_2_integration.py` -> `test`
- `A` `tests/m3_fixtures.py` -> `test`
- `A` `tests/marl/test_checkpoint_roundtrip.py` -> `test`
- `A` `tests/marl/test_masks_and_gae.py` -> `test`
- `A` `tests/marl/test_role_gradient_isolation.py` -> `test`
- `A` `tests/marl/test_sr_mappo_contract.py` -> `test`
- `A` `tests/unit/test_config.py` -> `test`
- `A` `tests/unit/test_conservation.py` -> `test`

## Boundary

- Training executed: `False`.
- Sealed-test scenarios accessed: `False`.
- OSM inputs remain simulation inputs, not field-deployment evidence.
- Candidate source, configurations, tests, reports, and outputs require independent branch-local verification.

Candidate-branch assets are design or candidate implementation inputs only; no M2/M3/M4 claim is accepted in the current G1 branch without fresh, branch-local verification.

## Commands

- `git rev-parse <ref>`
- `git diff --name-status <base>...<candidate>`
- `git ls-tree -r --name-only <candidate>`
- `git grep -n -I -E <pattern> <candidate>`
