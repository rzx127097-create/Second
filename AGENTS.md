# Project Agents Guide

This repository is the authoritative working record for the thesis second problem:

> Road-constrained air-ground heterogeneous cooperative pesticide spraying with
> a mobile pesticide replenishment vehicle, using SR-MAPPO as the flagship
> algorithmic framework.

All future code, Markdown documents, experiment manifests, audit reports,
figures, tables, and thesis-generation scripts for the second problem must be
recorded here unless a later project-state update explicitly changes that
decision.

Every important phase must be persisted to GitHub before the next gate begins:

1. update code, Markdown, configuration, manifests, and audit records in this
   repository;
2. run the phase-specific verification;
3. commit the phase with a descriptive message;
4. push the branch to `origin`;
5. record the pushed commit hash and verification result in
   `docs/PROJECT_STATE.md`.

Do not claim a phase is complete while its commit and push record is missing.
Never use force-push to rewrite the evidence history.

## Non-Negotiable Research Identity

- Use the public algorithm name `SR-MAPPO`.
- Describe the second problem as an air-ground heterogeneous extension of
  SR-MAPPO.
- Do not introduce HAPPO as an implementation or baseline.
- Do not rename the method to `AG-SR-MAPPO` or any other public algorithm name.
- The main replenished resource is pesticide only. Battery replenishment is
  inactive unless a separate activation audit is passed and recorded.
- Treat OSM road data as simulation input for road-constrained modeling, not as
  evidence of real field deployment.

## Maturity Boundary

- `docs/PROJECT_STATE.md` is authoritative for the dynamic current gate,
  highest maturity level, verification state, and next authorized work.
- Until that record documents a later persisted maturity gate, the highest
  maturity remains `M1` design/specification evidence.
- Permitted wording at M1: proposes, designs, defines, establishes, plans to
  test, provides a specification for later verification.
- Disallowed wording at M1: proves, significantly outperforms, formal
  experiments show, real deployment verified, universally optimal.

No formal claim that mobile support improves treatment or that SR-MAPPO is best
is allowed until the required evidence chain has reached the matching maturity
gate.

## Evidence Chain

Every formal result must remain traceable through this chain:

```text
source parameter/literature
-> frozen configuration and Git commit
-> run ID and raw episode log
-> validated long-format table
-> paired statistical summary
-> figure/table artifact manifest
-> thesis statement
```

Reject a result if any link is missing, duplicated, stale, manually overwritten,
or derived from an unlocked sealed test set.

## Gate Order

Work must advance in this order and stop at the first failed gate:

1. `G0`: isolate development state, inventory protected assets, and register
   project state.
2. `G1`: create evidence registries for parameters, literature, experiments,
   and artifacts.
3. `G2`: validate deterministic models: offline road topology, physical scale,
   service state machine, and resource conservation.
4. `G3`: validate heterogeneous MARL: role actors, critic, GAE, masks,
   normalization, and checkpoint round trip.
5. `G4`: activate resource scarcity and spatial-temporal mismatch mechanisms.
6. `G5`: run fair pilots and freeze methods/statistics before formal runs.
7. `G6`: run immutable formal jobs with recovery and validation.
8. `G7`: unlock sealed tests once, run paired statistics and mechanism audit.
9. `G8`: generate figures, tables, thesis prose, and blind-review audit from
   locked summaries.

## Required Comparisons

The default primary method family is:

- `sr_mappo_mobile`: SR-MAPPO with road-constrained mobile replenishment.
- `sr_mappo_fixed`: SR-MAPPO with resource-matched stationary support.
- `sr_mappo_astar`: SR-MAPPO UAV policy plus a rolling A* vehicle policy.
- `mappo_mobile`: same-source heterogeneous MAPPO with mobile replenishment.
- `sr_mappo_two_stage`: SR-MAPPO two-stage training.

All formal comparisons must use the same environment, resource budget, horizon,
scenario IDs, seed protocol, and information conditions unless a documented
exception is explicitly frozen before evaluation.

## Seed And Scale Protocol

Default formal protocol:

- Scales and maximum physical decision steps:
  - `g20x20_d2`: `150`
  - `g20x30_d3`: `180`
  - `g20x40_d3`: `220`
  - `g30x30_d3`: `220`
  - `g30x40_d4`: `280`
  - `g30x50_d4`: `350`
- Training seeds: `42`, `123`, `2024`, `3407`, `7919`.
- Validation scenario seeds: `20000-20049`.
- Sealed-test scenario seeds: `30000-30099`.
- Primary success threshold: `reduction_rate >= 0.85`.

Training reward is a diagnostic only. Thesis conclusions must use fixed-scenario
evaluation metrics and the locked statistical summary.

## Protected External Assets

Do not modify these assets unless a later user request explicitly authorizes it:

- First-problem repository:
  `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`.
- Base project and OSM inputs:
  `D:/Pycharm/Locust_rl`.
- Second-problem planning evidence:
  `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析`.
- Existing Word thesis files outside this repository.

The first-problem repository currently contains user changes related to
SR-MAPPO reward sensitivity. Treat them as protected user work and do not
revert, overwrite, or mix them into second-problem code.

## Repository Branches

- `origin/main` contains the currently tracked chapter 4.1/4.2 design and
  document-delivery assets.
- `origin/feature/problem2-code-framework` contains substantial problem-2 code,
  configs, tests, and verification assets. Treat it as existing project work
  that must be audited before integration; do not assume its maturity claims are
  valid without fresh verification.
- Use `codex/` branch names for new orchestration or implementation work unless
  the user requests a different branch.

## Output Roots

- The frozen problem-2 output root is
  `outputs/problem2_sr_mappo_v1`.
- Keep all second-problem raw logs, validated tables, statistics, figures,
  tables, manifests, and generated thesis evidence under that root or a
  documented repository subpath below it.
- Do not write problem-2 outputs into first-problem roots such as
  `outputs/sr_mappo_paper_v1`.
- OSM source files are read-only; derived road caches must carry source hash,
  CRS/bbox, grid shape, topology checksum, and code version.

## Agent Working Rules

- Read `docs/PROJECT_STATE.md` before starting any work.
- Update `docs/PROJECT_STATE.md` after each important phase.
- Keep subagent tasks bounded, independent, and explicit about inputs,
  acceptance criteria, output format, changed files, tests, unresolved issues,
  and maturity gate.
- Do not copy full subagent logs into the project state; summarize decisions,
  outputs, tests, and blockers.
- Use fresh verification before claiming that a gate, test, build, experiment,
  or artifact is complete.
- Preserve existing repository assets unless the task explicitly requires an
  update.
