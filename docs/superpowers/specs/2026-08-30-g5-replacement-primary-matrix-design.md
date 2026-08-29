# G5 Replacement Primary Matrix Design

## Goal

Replace the incomplete 120-job development pilot scope with a pre-registered
48-job replacement matrix that can support a new dynamic G5 freeze while
keeping reacceptance checks minimal and risk-based.

## Scope Boundary

This replacement applies only to the development pilot used for G5 method and
budget selection. It does not change formal G6 scales, formal training seeds,
validation scenarios, sealed scenarios, evaluation horizons, or statistical
contracts. The project remains at maturity `M2` until later gates are passed.

The existing 120-job matrix expands 20 executable conditions over two
representative scales and three development training seeds. The replacement
matrix expands the five required comparison conditions plus the three
learning-method coverage conditions over the same two scales and three seeds:

| condition | learning method | vehicle/controller path |
|---|---|---|
| `sr_mappo_mobile` | `sr_mappo_mobile` | learned, joint |
| `sr_mappo_fixed` | `sr_mappo_mobile` | fixed support, UAV-only |
| `sr_mappo_astar` | `sr_mappo_mobile` | rolling A*, UAV-only |
| `mappo_mobile` | `mappo_mobile` | learned, joint |
| `sr_mappo_two_stage` | `sr_mappo_mobile` | learned two-stage |
| `ippo_mobile` | `ippo_mobile` | IPPO mobile |
| `maddpg_mobile` | `maddpg_mobile` | MADDPG mobile |
| `iql_mobile` | `iql_mobile` | IQL mobile |

The resulting coverage is exactly `8 conditions x 2 scales x 3 seeds = 48`
jobs. Each job keeps the frozen development panel `10000-10019`, starts at
scenario `10000`, and uses the existing 128-interaction development budget
unless a separately committed replacement freeze records another value.

## Excluded Diagnostics

The following conditions are excluded from primary G5 candidate selection and
formal comparison: `sr_mappo_nearest`, `sr_mappo_urgency`,
`no_observation_normalization`,
`no_return_normalization`, `no_network_stabilization`,
`no_robust_value_update`, `no_learning_rate_decay`, `learning_rate`,
`clip_range`, `entropy_coef`, `gamma`, and `gae_lambda`.

Existing Phase 3 controller checks and the seven completed dynamic pilots are
retained as descriptive M2 diagnostics. They are not silently reclassified as
rows in the replacement primary matrix and are not used as formal efficacy,
ranking, significance, or superiority evidence.

## Identity And Audit Contract

`build_pilot_matrix` remains the single source of truth for the replacement
matrix. Its deterministic order remains scale, seed, condition, then the
single start scenario. The matrix builder must emit 48 unique `PilotJob`
identities, and the runner must reject any subset, duplicate, excluded
condition, non-development partition, scenario-panel drift, or identity drift.

Every completed job must preserve the existing evidence chain: source commit,
frozen candidate/config hashes, raw training artifacts, validated artifact
manifest, finite metrics, dynamic ecology, pesticide-only replenishment,
resource conservation, and false validation/sealed access flags. The machine
audit must record the replacement scope and `matrix_complete=true` only after
all 48 identities pass.

## Gate Consequences

A complete, audited 48-job matrix may be used to generate a replacement G5
freeze and run the read-only Phase 4 preflight. The first formal G6 job remains
blocked until that freeze and preflight pass. Formal G6 still uses the project
default six physical scales, five formal training seeds, fixed validation/test
partitions, and locked statistics. No validation or sealed payload is accessed
while generating or executing this replacement pilot.

## Non-Goals

- No parallel or batch execution is introduced by this design; the current
  one-job-at-a-time boundary remains in force.
- No candidate is selected from the seven historical Phase 3 physical pilots.
- No budget, seed, scenario, or statistical rule is changed after validation
  access; any later change requires another replacement freeze.
- No claim about treatment efficacy, superiority, deployment, or optimality is
  made from development evidence.
