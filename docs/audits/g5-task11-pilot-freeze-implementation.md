# G5 Task11 Pilot Freeze Implementation Handoff

Date: 2026-08-25
Status: implementation-ready; full development pilot execution pending
Maturity: M2

## Scope

Task11 now provides a development-only pilot matrix, conservative runtime
aggregation, frozen-budget selection, and validation-candidate manifest
generation. The matrix is exactly:

- scales: `g20x20_d2`, `g30x50_d4`;
- methods: the five registered learning methods;
- conditions: all 17 registered condition types;
- training seeds: `51001`, `51002`, `51003`;
- scenarios: `10000-10019`;
- total identities: `10,200`.

`run_pilot_matrix` uses the same `run_training_job` collection/update/checkpoint
path, preserves `scale` and `scenario_id` in the training log, and writes only
descriptive `development_pilot_descriptive` records. It fails closed on any
validation/sealed/battery flag, duplicate identity, non-development partition,
or runner failure.

`select_pilot_budget` retains the maximum observed seconds-per-interaction for
each method/scale pair and passes representative `g30x50_d4` evidence to the
already frozen largest-feasible budget rule. `freeze_validation_candidates`
writes four content-hashed candidates per learning method, equal interactions,
the 50-ID validation panel hash, and the exact tie-break chain. It rejects any
attempt to mutate a manifest after validation or sealed access.

## Verification

- `python -m pytest tests/g5/test_pilot_freeze.py -q`: `5 passed`.
- `python -m pytest tests/g5/test_end_to_end_smoke.py -q`: `15 passed`.
- `python -m pytest tests/g3 tests/g5 -q`: `390 passed` from the isolated G5
  environment after the final runner wiring.
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed` from the host
  environment, which is required for the G2 cross-process replay subprocess.
- `python scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed
  access false, `actual_unlock_count=0`.
- `python -m compileall -q src scripts` and `git diff --check`: passed.
- Task10 smoke was rerun after Task11 runner wiring: CPU/main `pass/85`, CUDA
  `pass/5`; every smoke manifest now binds source commit
  `991af5759ee77e9c2b93d9d564768a8e67cd518d` and keeps validation/sealed/battery
  access false.

## Pending Execution Gate

The full neural pilot matrix has not been run in this handoff. A one-job real
runner benchmark was approximately four seconds on the current CPU, implying
hours for 10,200 independent jobs. No synthetic rows, smoke rows, or copied
scenario records were promoted to pilot evidence. The authorized execution
command is:

```powershell
.venv-g5/Scripts/python.exe scripts/run_g5_pilots.py --device cpu --interactions 128
```

The command must finish with `status=pass` and complete coverage before it can
freeze `outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json`.
Until then, validation tuning, G6 formal jobs, and G7 sealed evaluation remain
unauthorized and no Task11 pilot result supports efficacy, superiority, or real
deployment claims.
