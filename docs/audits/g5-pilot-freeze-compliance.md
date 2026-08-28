# G5 Pilot Freeze Compliance Audit

Date: 2026-08-28
Branch: `codex/problem2-g5-pilot-freeze`
Generation source commit: `7a079fa16afae7ebd1d69f4d63d83cc09437a816`
Generation source scope SHA-256:
`9a6a9baf960d86f94ba391cef60116d0ab33fb8b8c965c30a2e7f38e9308def4`

## Disposition

Task12 completed the G5 validation-only tuning, selected development refit,
and freeze-manifest generation. The generated freeze has `status=pass`, but
the project remains at maturity `M2`. G6 is formal training and remains
unexecuted until the required content and persistence commits are pushed.

No sealed scenario content or sealed evaluation result was read. The sealed
lock remains `maximum_unlock_count=1`, `actual_unlock_count=0`.

## Immutable Inputs

| Artifact | SHA-256 |
|---|---|
| `manifests/validation-candidates.json` | `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A` |
| `manifests/pilot-budget.json` | `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB` |
| `docs/evidence/g1/sealed_test_lock.yaml` | `78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226` |

The candidate grid remained at 20 entries, four per learning method. Every
candidate used the same frozen `200000` environment-interaction budget.

## Validation Tuning

Canonical candidate training used the physical G2-to-G3 environment adapter at
scale `g30x50_d4` for `60` unique identities: five methods, four candidates,
and three seeds (`51001`, `51002`, `51003`). All terminal manifests were
`pass`, all were generated from the source commit above, and all recorded
`validation_accessed=false`, `sealed_accessed=false`, and
`battery_replenishment_enabled=false`.

Validation evaluation consumed exactly the frozen scenario IDs `20000-20049`
and produced:

```text
20 candidates x 3 training seeds x 50 scenarios = 3000 rows
```

The action-driven environment supplied pest metrics. The access ledger used an
exact row prefix and hash chain and ended with `row_count=3000` and
`actual_unlock_count=0`. No technical failure was recorded. Every candidate
summary has 150 rows and `interaction_count=200000`.

The mechanical rule was mean validation reduction rate, then success
probability, then interaction count, then lexicographically smaller config
hash. The selected configurations were:

| Method | Candidate | Config hash | Mean reduction | Success probability |
|---|---|---|---:|---:|
| `sr_mappo_mobile` | `c02` | `06deec69c111adb01062b951e98bf6642bdb9bd064a63ebade903fe87786e6d0` | 0.00743609 | 0.0 |
| `mappo_mobile` | `c01` | `9b47674560692e920dc28361bc8bf0dc1210923fbec424ad442cefede0695de9` | 0.00269588 | 0.0 |
| `ippo_mobile` | `c01` | `ab9e8807b886a059b54e34053a891d8dd046fcfbfec52fa1d180eed247df3461` | 0.00261758 | 0.0 |
| `maddpg_mobile` | `c04` | `22dc69688615b405acd2e6cc64e6700400b60d7904826883874dcb3496d0434f` | 0.00000000 | 0.0 |
| `iql_mobile` | `c03` | `41871a4071d3b04e2585d06d3476976bbda0ac305c563d40b2a421d6b5cdde48` | 0.00259980 | 0.0 |

These are weak/negative validation outcomes. They are retained in
`audits/negative-result-diagnosis.json` and do not support an efficacy,
superiority, or statistical-significance claim.

## Development Refit

The selected configurations were rerun through the physical development
refit on the complete Task11 pilot matrix:

```text
2 scales x 5 methods x 17 conditions x 3 seeds = 510 jobs
510 jobs x 20 development scenario references = 10200 records
```

The refit returned `status=pass`, retained its raw checkpoint, manifest,
summary, and physical episode artifacts, and recorded no validation or sealed
scenario access in the training results. It is descriptive development
evidence, not independent formal evaluation.

## Frozen G6/G7 Plans

- `g6-training-jobs.json`: `150` base jobs and `375` unique jobs, with selected
  candidate hashes, source scope, checkpoint rule, and dependency graph.
- `g6-validation-evaluations.json`: `375000` expected evaluation identities,
  content-free and `frozen_unexecuted`.
- `g7-sealed-evaluations.json`: `42500` expected evaluation identities,
  scenario identities/hashes only, no scenario content, and no results.
- `g7-analysis.json`: `locked_unexecuted`, empty inputs/results, and frozen
  statistics/exclusion contract hashes.

## Acceptance Checks

The following checks were run during Task12 generation:

- focused Task12 and physical-training tests: `70 passed`;
- canonical training identity audit: `60/60`, all `pass`, no duplicate
  `(method,candidate,seed)` identity;
- pre-validation candidate/budget/sealed-lock hash audit: pass;
- validation tuning: `3000/3000` rows, `20/20` summaries, zero technical
  failures;
- selected refit: `510/510` jobs, `10200` records, `status=pass`;
- `scripts/freeze_g5.py --write`: `status=pass`, exact counts and protected
  asset audit pass;
- `scripts/audit_g5_contracts.py`: `status=pass`, validation and sealed
  boundary flags safe before validation access;
- the first invocation of the refit helper failed only because a one-off
  `python -c` call omitted the repository `src` path; it wrote no evidence and
  was immediately corrected. This is not part of the evidence set.

The final fresh full-suite, compile, artifact dry-run, freeze check-only,
diff, content push, and persistence checks must be recorded in
`docs/PROJECT_STATE.md` after the content commit. G5 must not be marked
persisted until all of them pass on clean source history.

## Protected Assets And Claims

The protected first-problem repository, base project and OSM inputs, planning
evidence, and external Word files were only hash-checked and were not modified.
Temporary directories and quarantined failed attempts were not staged.

Permitted statements at the current maturity are limited to implementation,
invariant, validation-process, and descriptive development/validation
observations. Formal experiments, treatment improvement, SR-MAPPO superiority,
statistical significance, deployment verification, and sealed-test conclusions
remain unauthorized.
