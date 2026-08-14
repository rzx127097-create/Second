# Complete Project Runbook

## Scope and claim boundary

This runbook verifies the M2 implementation path end to end: a real
`ScenarioBundle` CPU smoke update, checkpoint recovery, one validation scene,
and the traceable artifact pipeline. It is an engineering check, not a paper
result. The checked-in parameter registry and formal matrix are `provisional`.
Do not report smoke metrics as formal performance, deployment evidence, or a
superiority claim.

M3 is blocked until engineering parameter sources and independent validation
scenarios with multiple training seeds are documented and frozen. M4 is blocked
until the complete five-method matrix, frozen configuration, sealed-test split,
deterministic policy evaluation, and evidence manifests are produced. A sealed
test must be frozen and deterministic; it must never silently fall back to the
smoke split.

The road graph and travel times are simulation constraints used to test the
decision model. They are not a claim about a surveyed road network or real
deployment. The vehicle supplies pesticide liquid only; charging and battery
exchange are outside this problem. M2 code evidence is limited to the scenario,
event ordering, resource conservation, demand/rendezvous interfaces, and
SR-MAPPO training/evaluation contracts.

## Environment

Use Windows PowerShell and Python 3.11:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev,rl]"  # pytest + torch; required by end-to-end smoke
# Non-RL domain-only checks may omit torch:
# pip install -e ".[dev]"
```

The smoke path uses CPU and a small hidden layer/horizon. It is the only
execution path permitted while configuration status is provisional.

## End-to-end smoke

Run the smallest matrix entry (one job) first:

```powershell
$out = "runs\smoke"
python scripts\run_matrix.py --config-dir configs --output-root $out --smoke --max-jobs 1
```

The command emits one JSON object. `status` is normally `partial` because one
job is selected from the full matrix; a child job must be `completed`. The
selected job uses canonical key `sr_mappo_mobile` and writes:

- `runs\smoke\jobs\<job-id>.json`: immutable method/scale/training seed,
  config hash, Git commit, attempts, status, and checkpoint path.
- `runs\smoke\checkpoints\<job-id>.pt`: canonical format-2 checkpoint with an
  integer `step` and algorithm/optimizer state.
- `runs\smoke\raw\<job-id>.jsonl`: event-complete training episode rows.

Resume the same identity after an interruption by rerunning the training
command with the same config, scale, seed, and output root. The runner loads the
existing checkpoint and continues from its recorded step; it never changes the
job identity. Failed jobs may be retried up to `--max-attempts`. The e2e test
uses a deterministic failure injection in the worker to exercise this persisted
retry path; that injected failure is a recovery check, not a scientific result.
Matrix output
`partial` means accepted selected jobs completed while unselected jobs remain;
`failed` means at least one selected job did not complete. Inspect the persisted
job JSON before retrying.

## Validation and artifacts

Use the checkpoint produced above for one explicitly isolated validation scene:

```powershell
python scripts\evaluate.py --config-dir configs `
  --checkpoint runs\smoke\checkpoints\<job-id>.pt `
  --split validation --scenario val_001 --smoke
```

The output JSON includes `status`, `split`, `scenario`, and `raw_path`. The
validation raw JSONL row preserves `run_id`, `method`, `scale`,
`training_seed`, `scenario_id`, `config_hash`, `git_commit`, `split`,
`parameter_status`, `reduction_rate`, `success`, and `transferred_l`.
The strict artifact parser derives the normalized boolean `provisional` field;
summary rows and the evidence manifest carry that normalized status.

Build validated tables, summaries, figures, and an input/output hash manifest
from that generated JSONL:

```powershell
python scripts\build_artifacts.py `
  runs\smoke\raw\evaluation-<job-id>-val_001.jsonl `
  --output runs\smoke\artifacts `
  --manifest runs\smoke\artifacts\evidence_manifest.json
```

The artifact command emits a `paths` object. Check that `validated_csv`,
`summary_json`, `three_line_table.tsv`, `three_line_table.md`, `figure_svg`,
`figure_png`, and `manifest_json` exist. The manifest records the input path and
SHA-256 of the exact input bytes, output paths and hashes of the exact output
bytes, and identity sets, preserving the chain
`config/source -> raw JSONL -> validated CSV -> summary/table/figure -> prose`.

## Formal matrix gates

`run_matrix.py --dry-run` is read-only and may enumerate all 150 immutable jobs.
Actual matrix execution requires explicit `--smoke` while status is provisional.
Formal execution without smoke is rejected. Before M3/M4, do not claim a
verified parameter set, multi-seed validation, sealed-test performance, or
method superiority. Keep the five canonical keys exactly as configured:

`sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`,
`sr_mappo_two_stage`.

`HAPPO` and `AG-SR-MAPPO` are forbidden names for this project and must not
appear as matrix methods or result labels.

## Verification checklist

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
```

Do not modify Word artifacts as part of this runbook. Any thesis prose must be
written only after the corresponding manifest and validated artifacts are
available, with provisional wording retained until the M3/M4 gates pass.
