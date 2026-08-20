# G3 Heterogeneous SR-MAPPO Compliance Audit

Date: 2026-08-20

## Result

The G3 heterogeneous-MARL acceptance boundary passed at maturity `M2`.
The public algorithm identity remains `SR-MAPPO`; this is an air-ground
heterogeneous implementation with one shared UAV actor, one vehicle actor,
and one structured centralized team critic.

- Gate: `G3`
- Audit status: `pass`
- Acceptance tests: `17/17`
- Configuration hash:
  `421eff64d1161f78c9029dfc6d133b9b66247f3cf905b9577e55965584195f93`
- Training partition: `development`
- Smoke source-tree commit:
  `092b7f3e965a24979bac65c8304cd9d7dc142f73`
- Implementation source-tree hash:
  `a3b5f20c6935cf29c0c0edb627cf64a0b4b5c7b96a3ca94449c205da1b5f2a95`
- Scenario seed manifest:
  `g1.v1`,
  `ab993f19e1ae4cb9d7ba4f4f862639901581be057e0a251e5c113d957f6059ce`

## Acceptance Coverage

| Contract | Verified node |
|---|---|
| Actor gradient and optimizer isolation | `test_actor_optimizer_parameter_sets_are_gradient_isolated` |
| Saved-mask log-probability replay | `test_algorithm_act_replays_from_exact_masks_and_policy_inputs` |
| Zero probability for invalid actions | `test_masked_categorical_has_exact_zero_probability_for_invalid_actions` |
| Team GAE termination/truncation semantics | `test_compute_gae_bootstraps_truncation_but_cuts_termination_and_trace` |
| Valid-population advantage normalization | `test_rollout_advantage_normalization_uses_only_valid_team_samples` |
| Configured actor/critic update counts | `test_trainer_updates_roles_with_isolated_optimizers_and_counts` |
| Team-valid sample filtering | `test_trainer_excludes_team_invalid_samples_from_all_updates` |
| Evaluation normalizer freeze | `test_deterministic_evaluation_freezes_normalizers_byte_identically` |
| Checkpoint policy/value/optimizer/scheduler/normalizer/RNG round trip | `test_checkpoint_roundtrip_restores_policy_trainer_normalizers_and_rng` |
| Expected checkpoint provenance binding | `test_checkpoint_rejects_expected_provenance_drift` |
| Actor information boundary | `test_actor_interfaces_accept_only_role_observation` |
| SR-MAPPO/MAPPO stability-only diff | `test_configuration_diff_only_allows_declared_stability_flags` |
| G2 mask conversion without action replacement | `test_g2_masks_convert_to_role_masks_without_action_replacement` |
| Hold-only vehicle mask | `test_g2_vehicle_mask_allows_hold_only_without_candidate_slots` |
| Candidate-slot identity validation | `test_g2_vehicle_mask_validates_candidate_slot_identity` |
| Rollout candidate mapping validation | `test_rollout_rejects_g3_candidate_mapping_mask_mismatch` |
| Non-sealed finite training smoke | `test_training_smoke_writes_finite_provenance_bound_artifacts` |

The auditor executes all 17 nodeids directly and requires exactly `17 passed`.
Skipped, xfailed, xpassed, failed, or error outcomes are rejected.

## Smoke Artifacts

The canonical smoke used development seed `9017` and `2` updates. It used the
frozen output root and did not read validation scenario seeds `20000-20049` or
sealed-test seeds `30000-30099`.

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| `outputs/problem2_sr_mappo_v1/g3/training-smoke.jsonl` | `9885e24a0e58191fdd7975b55d72487d3f817985c8a0ec585d737af5228e2972` | 2204 |
| `outputs/problem2_sr_mappo_v1/g3/provenance.json` | `10da75b9c01d485ece3e6214de10367ba5356d80e4be97e38a1e399afb9ed69d` | 756 |
| `outputs/problem2_sr_mappo_v1/g3/checkpoints/g3-smoke.pt` | `832ddd1350ff82a0642b144c4d962e762f47b294dcc00873354e2df99159d0b3` | 1293261 |
| `outputs/problem2_sr_mappo_v1/g3/g3-marl-audit.json` | `b9e2829f02372235bba856317767b8d0703d83e5841c75befab68d092ddc6b2c` | 4874 |

The checkpoint, provenance, and raw log bind the same configuration hash,
source commit, implementation-tree hash, source-clean flag, seed-manifest
hash, development partition, update count, finite-loss result, pesticide-only
resource declaration, and false validation/sealed access flags.

## Fail-Closed Boundaries

- The canonical smoke output root is fixed to
  `outputs/problem2_sr_mappo_v1/g3`.
- The auditor rejects output-root escapes, provenance drift, raw-log identity
  drift, unresolved source commits, implementation-tree hash drift, incomplete
  checkpoint state, skipped acceptance nodes, validation/sealed access, and
  battery replenishment.
- Candidate slot identities must agree with the behavior-time action mask.
- Team-invalid padding is excluded from critic and actor updates; forced
  single-action samples remain in team GAE/critic data and are excluded only
  from the corresponding actor loss.

## Boundaries

G3 does not establish resource-scarcity activation, mobile-support efficacy,
algorithmic superiority, formal experiment results, or deployment evidence.
The development environment is resource-neutral and the smoke is engineering
evidence only. Battery replenishment remains inactive.

The next authorized gate is G4. G4 must begin with resource activation and
counterfactual mechanism probes; it must not treat the G3 smoke as endpoint
evidence.
