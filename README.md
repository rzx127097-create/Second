# Problem 2: Road-Constrained Air-Ground SR-MAPPO

This repository contains the runnable code framework for Chapter 4, Problem 2:
heterogeneous UAV and road-constrained pesticide-supply-vehicle cooperation.
The ground vehicle supplies pesticide liquid only. Battery charging and battery
exchange are outside this problem.

The current checked-in configuration is **provisional**. The implementation and
its deterministic invariants are at maturity M2. Smoke runs verify the software
path; they are not formal thesis results, deployment evidence, or superiority
claims. See `docs/verification/section-4-5-runbook.md` for the complete workflow.
The latest parameter, road-source, scenario, and resource-activation decision
is recorded in `docs/verification/formal-readiness-report.md`.

The repository includes a frozen representative road derivative at
`data/roads/jodhpur_cropped_metric.graphml` with provenance in
`docs/verification/frozen-road-jodhpur.json`. It is derived from the local
Jodhpur OSM GraphML and is a simulation constraint, not a surveyed farm road.
Parameter provenance and applicability limits are recorded in
`docs/evidence/parameter-source-ledger.yaml`. The runtime field is a
reaction-diffusion-advection exposure model configured in
`configs/field_dynamics.yaml`; its coefficients remain provisional until
crop-, wind- and compound-specific calibration is supplied.

## Environment

Use Windows PowerShell and Python 3.11:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev,rl]"
```

The `rl` extra installs PyTorch for the SR-MAPPO CPU smoke path. Domain-only
tests may use `pip install -e ".[dev]"`.

## Verification

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
```

The e2e suite intentionally exercises real CPU training and recovery and can
take several minutes. Do not reduce its assertions to make it finish faster.

## Canonical methods

The five registered comparison methods are:

```text
sr_mappo_mobile
sr_mappo_fixed
sr_mappo_astar
mappo_mobile
sr_mappo_two_stage
```

`SR-MAPPO` is the flagship algorithm name. HAPPO and `AG-SR-MAPPO` are not
implemented or registered in this project.

## Smallest end-to-end smoke

```powershell
$out = "runs\smoke"
python scripts/run_matrix.py --config-dir configs --output-root $out --smoke --max-jobs 1
```

The command writes an immutable job record, a format-2 checkpoint, and a raw
UTF-8 JSONL episode log below `$out`. Repeating the same command resumes the
same identity and does not retrain a completed job.

Evaluate one shared validation scenario:

```powershell
python scripts/evaluate.py --config-dir configs `
  --checkpoint $out\checkpoints\<job-id>.pt `
  --split validation --scenario val_001 --smoke
```

Evaluate every registered validation scenario for selected completed jobs:

```powershell
python scripts/evaluate_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --family main_comparison --output-root $out `
  --split validation --smoke --max-jobs 1
```

After all formal validation jobs are complete and the configuration status is
verified, freeze the selected final-update checkpoints and validation evidence,
then issue the one-time sealed-test ledger:

```powershell
$jobFiles = (Get-ChildItem -LiteralPath $out\jobs -Filter "*.json").FullName
$validationLogs = (Get-ChildItem -LiteralPath $out\raw -Filter "evaluation-*-val_*.jsonl").FullName
python scripts/freeze_sealed_test.py freeze `
  --config-dir configs --job-file $jobFiles --validation $validationLogs `
  --output $out\validation-freeze.json
python scripts/freeze_sealed_test.py unlock `
  --freeze $out\validation-freeze.json `
  --scenario test_001 --output $out\sealed-unlock.json
```

The checked-in configuration is provisional, so these formal commands fail
closed until the parameter, scenario, and protocol registries are verified.

Build the basic traceable artifact package:

```powershell
python scripts/build_artifacts.py `
  $out\raw\evaluation-<job-id>-val_001.jsonl `
  --output $out\artifacts `
  --manifest $out\artifacts\evidence_manifest.json
```

## Formal boundary

While the parameter registry, scenario registry, and protocol are provisional,
commands without `--smoke` are rejected. Formal work requires the remaining
engineering parameter sources, independent validation scenarios, a frozen
configuration, calibrated reaction-diffusion-advection coefficients, and a
sealed-test unlock. The evidence path is always:

```text
source/config -> raw JSONL -> validated table -> statistics -> figure/table -> prose
```

The OSM/synthetic road graph is a simulation constraint, not a surveyed road
network or a real deployment claim. See `docs/verification/complete-project-runbook.md`
and `docs/verification/section-4-5-runbook.md` for maturity gates and recovery.
