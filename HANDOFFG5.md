# HANDOFF G5: TASK12 COMPLETE

Date: 2026-08-28
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g5-pilot-freeze`
Task12 training and validation source commit: `7a079fa16afae7ebd1d69f4d63d83cc09437a816`

## Current Position

G5 Task12 has completed the validation-only tuning and final G5 freeze
generation. The implementation and evidence remain at maturity `M2`. The
freeze is not formal efficacy evidence. G6 is the next authorized gate only
after the content commit and the separate state-record persistence commit have
both been pushed and verified.

The public method name remains `SR-MAPPO`. Problem 2 remains its air-ground
heterogeneous extension. The only replenished resource is pesticide; battery
replenishment remains disabled. OSM data remains a road-constrained simulation
input, not field-deployment evidence.

## Task12 Evidence

- Canonical physical candidate training: `60` identities, exactly five methods
  x four candidates x three seeds, scale `g30x50_d4`, and `200000`
  interactions per identity. All `60` terminal manifests passed. Five older
  source attempts remain preserved and were not counted.
- Validation tuning: `20` frozen candidates x `3` training seeds x `50`
  validation scenarios = `3000` action-driven rows. Candidate and budget
  hashes were checked before the first row and the access ledger locked the
  candidate bytes thereafter.
- Validation candidate results, including every weak result, are retained in
  `validation/selected-configurations.json`. All candidates have
  `success_probability=0.0`; this is a negative/weak validation diagnosis, not
  a formal ranking or efficacy claim.
- Mechanical selections: `sr_mappo_mobile=c02`, `mappo_mobile=c01`,
  `ippo_mobile=c01`, `maddpg_mobile=c04`, and `iql_mobile=c03`.
- Selected development refit: `510` physical development jobs and `10200`
  scenario-reference rows. The refit did not access validation or sealed
  scenarios.
- G6 plan: `150` base jobs and `375` unique jobs, all frozen and unexecuted.
- G6 validation plan: `375000` expected identities, content-free until G6.
- G7 plan: `42500` expected sealed evaluation identities. The sealed manifest
  contains identities and hashes only; scenario content and results are empty.

Frozen hashes:

- validation candidates:
  `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`;
- pilot budget:
  `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`;
- sealed lock:
  `78C9CAA7D432F56F91B67195EB413EDDAB4E9F84C9FD214EB7A9373F48A73226`;
- freeze source scope:
  `9a6a9baf960d86f94ba391cef60116d0ab33fb8b8c965c30a2e7f38e9308def4`.

## Required Verification Before G6

Run from the repository root:

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5 -q
.venv-g5/Scripts/python.exe -m pytest -q
.venv-g5/Scripts/python.exe -m compileall -q src scripts
.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py
.venv-g5/Scripts/python.exe scripts/validate_g5_artifacts.py --root outputs/problem2_sr_mappo_v1/g5 --dry-run
.venv-g5/Scripts/python.exe scripts/freeze_g5.py --check-only
git diff --check
```

The expected artifact status is `freeze-manifest.status=pass`,
`validation_rows=3000`, `refit_jobs=510`, `refit_episodes=10200`, G6
`150/375`, G7 `42500`, `sealed_accessed=false`, and
`actual_unlock_count=0`. Do not run G6 formal training in this handoff.

## Evidence Paths

The primary artifacts are below
`outputs/problem2_sr_mappo_v1/g5/validation/`:

- `validation-access.json`;
- `validation-episodes.jsonl` and `rows/`;
- `summaries/`;
- `selected-configurations.json`;
- `refit/`;
- `technical-failures.jsonl`.

The final freeze artifacts are:

- `outputs/problem2_sr_mappo_v1/g5/validated/validation-episodes.jsonl`;
- `outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json`;
- `outputs/problem2_sr_mappo_v1/g5/manifests/g6-validation-evaluations.json`;
- `outputs/problem2_sr_mappo_v1/g5/manifests/g7-sealed-evaluations.json`;
- `outputs/problem2_sr_mappo_v1/g5/manifests/g7-analysis.json`;
- `outputs/problem2_sr_mappo_v1/g5/freeze-manifest.json`;
- `outputs/problem2_sr_mappo_v1/g5/audits/negative-result-diagnosis.json`;
- `docs/audits/g5-pilot-freeze-compliance.md`.

## Boundaries

- Do not edit or regenerate the candidate manifest, budget manifest, or any
  validation row after the first validation access.
- Do not read sealed scenario content. Keep the sealed lock at maximum `1` and
  actual unlock `0`.
- Do not modify `_tmp_docx_assets/`, `g5/_debug/`, `g5/quarantine/`, or any
  existing `tmp-*` directory.
- Do not modify the first-problem repository, `D:/Pycharm/Locust_rl`, OSM
  inputs, planning evidence, or external Word files.
- Do not claim that mobile support improves treatment, that SR-MAPPO is best,
  that results are statistically significant, or that simulation verifies a
  real deployment. At `M2`, only implementation, invariant, and
  development/validation-process statements are permitted.

## Persistence Requirement

The Task12 content commit must use subject:
`feat: freeze g5 fair-pilot experiment system`.

After the content push, update `docs/PROJECT_STATE.md` with the exact content
hash and fresh verification, then create and push:
`docs: record g5 freeze persistence`. Verify local HEAD, upstream HEAD, and
`git ls-remote` are identical. Only then may `docs/PROJECT_STATE.md` authorize
G6.
