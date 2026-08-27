# G5 Task11 Pilot Freeze Implementation Handoff

Date: 2026-08-27
Status: accepted; complete development pilot and candidate freeze persisted
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
- training identities: `510` (`5 x 17 x 2 x 3`);
- descriptive episode records: `10,200` (`510 x 20`).

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

## Acceptance Evidence

The full command completed with `status=pass`:

```powershell
.venv-g5/Scripts/python.exe scripts/run_g5_pilots.py --device cpu --interactions 128
```

- training jobs: `510`; episode records: `10,200`; failures: `0`;
- scales: `g20x20_d2`, `g30x50_d4`;
- methods: `sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`,
  `maddpg_mobile`, `iql_mobile`;
- conditions: all `17` registered condition IDs;
- training seeds: `51001`, `51002`, `51003`; development scenarios:
  `10000-10019`;
- every pilot directory has a checkpoint, manifest, summary, and training log;
- runtime budget: `200000` interactions, checkpoint interval `10000`,
  checkpoint count `20`, projected slowest runtime `0.7708476562500424` hours;
- candidate freeze: `20` candidates, exactly four per learning method,
  content-hashed and bound to the 50-ID validation panel hash;
- all pilot records are `development_pilot_descriptive` with
  `validation_accessed=false`, `sealed_accessed=false`, and
  `battery_replenishment_enabled=false`.

Core artifact SHA-256 hashes:

- `validated/pilot-episodes.jsonl`: `7609183B3B8945BC019F63F361C5FEBE7D00E9E7E4E8042BB07530A9C013DE72`;
- `audits/pilot-audit.json`: `4A14FE3B3518ECD0E864DDD79FADFCE7311E829BB1E505E76925AE162EF58CF2`;
- `audits/pilot-artifact-manifest.json`: `1B757397A28240C567CBADC5AD56B64C533E316558CE2924935C4D33B1ACC61E`;
- `manifests/pilot-budget.json`: `048138954F336C95E3D339AED594C71E23167EF30CC1F4A373D5C2B10BB049CB`;
- `manifests/validation-candidates.json`: `67E6784B3D00D0385310D467C351F5B3374F02C7A7D7C22C571D4DE29190419A`.

The candidate manifest, pilot summaries, artifact manifest, and refreshed
smoke manifests bind the executed source commit
`33ba716aacedeff4e90a6d6f604f103732a970fd`.

## Verification

- `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_pilot_freeze.py
  tests/g5/test_end_to_end_smoke.py -q`: `32 passed`.
- `python -m pytest tests/g5/test_end_to_end_smoke.py -q`: `15 passed`.
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`: `402 passed`
  from the isolated G5 environment after the final persistence commit.
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed` from the host
  environment, which is required for the G2 cross-process replay subprocess.
- `python scripts/audit_g5_contracts.py`: `status=pass`, validation/sealed
  access false, `actual_unlock_count=0`.
- `python -m compileall -q src scripts` and `git diff --check`: passed.
- `.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q`: `402 passed`;
- `python -m pytest tests/g2 tests/g4 -q`: `178 passed`;
- `python -m compileall -q src scripts`: exit `0`; `git diff --check`: exit `0`;
- `python scripts/audit_g5_contracts.py`: `status=pass`,
  `actual_unlock_count=0`;
- `python scripts/validate_g5_artifacts.py --root outputs/problem2_sr_mappo_v1/g5 --dry-run`:
  dry-run only, no jobs executed;
- refreshed Task10 smoke audits: CPU/main `pass/85`, CPU `pass/85`, CUDA
  `pass/5`; all 85 manifests bind source commit
  `33ba716aacedeff4e90a6d6f604f103732a970fd` and retain false boundary flags.

## Boundary And Next Gate

Task11 is accepted at `M2`. These descriptive pilot artifacts do not support
efficacy, superiority, or real-deployment claims. Validation tuning is the next
authorized G5 activity and must consume the frozen candidate manifest without
editing it. G6 formal jobs and G7 sealed evaluation remain unauthorized until
the subsequent acceptance gates.
