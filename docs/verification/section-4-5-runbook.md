# Section 4.5 Experiment Runbook

## Scope and maturity

This runbook covers the complete Chapter 4.5 software path: the five fair main
methods, mechanism interventions, parameter sensitivity, adaptation conditions,
component ablations, recoverable jobs, shared-scenario evaluation, paired
statistics, and traceable figures/tables.

The checked-in protocol is executed as a controlled simulation. Smoke outputs
verify interfaces only. Full `--simulation` outputs become pilot evidence only
after multi-seed shared-scenario evaluation and identity checks; they are not
field deployment evidence.

## 1. Protocol dry-run

Dry-run does not create jobs, checkpoints, logs, or figures. Run it for every
family before launching workers:

```powershell
$families = @("main_comparison", "mechanism", "sensitivity", "adaptation", "ablation")
foreach ($family in $families) {
  python scripts/run_matrix.py `
    --config-dir configs `
    --protocol configs/experiments/chapter4_5.yaml `
    --family $family `
    --output-root runs/planning `
    --simulation --dry-run
}
```

Expected checked-in job counts are 150 for `main_comparison`, 90 for
`mechanism`, 120 for `sensitivity`, 120 for `adaptation`, and 60 for
`ablation`. The command reports the protocol hash, provisional status, and
immutable job identities. A changed configuration, condition, seed, split,
protocol, or Git commit must create a different job identity.

## 2. Five-method CPU smoke

Run one real worker for each canonical method on the same smoke configuration:

```powershell
$out = "runs\chapter45-smoke"
python scripts/run_matrix.py `
  --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --family main_comparison `
  --output-root $out `
  --smoke --max-jobs 5
```

The five completed child jobs must be `sr_mappo_mobile`, `sr_mappo_fixed`,
`sr_mappo_astar`, `mappo_mobile`, and `sr_mappo_two_stage`. Every raw row must
retain the method, scale, training seed, family, condition ID, configuration
hash, protocol hash, Git commit, split, and parameter status.

Repeat the same command to verify recovery. Completed identities are reused;
they must not receive a new attempt or a second training trajectory. For a
failed identity, inspect `runs/.../jobs/<job-id>.json`, preserve its traceback,
and retry only that identity after correcting the root cause.

A local live PID keeps its lease regardless of age. A lease owned by another
host is treated as stale after the configured 24-hour timeout, allowing a
crashed remote worker to be recovered without immediate cross-host job
stealing.

## 3. Controlled-simulation pilot sequence

Run the technical preflight and regenerate the resource pilot after any model,
parameter, profile, or source-code change:

```powershell
python scripts/audit_simulation_preflight.py --config-dir configs `
  --report runs/simulation-preflight.json --strict
python scripts/run_resource_pilot.py --config-dir configs `
  --output runs/resource-pilot/raw.jsonl `
  --report runs/resource-pilot/activation.json `
  --scale s1 --episodes 5 --max-steps 600
python scripts/audit_simulation_preflight.py --config-dir configs `
  --resource-report runs/resource-pilot/activation.json `
  --report runs/simulation-preflight-with-resource.json --strict
```

Commit the tested source, verify a clean worktree, then run one smallest-scale
and one largest-scale job before expanding the matrix. Never launch the full
540-job set (150 main + 90 mechanism + 120 sensitivity + 120 adaptation + 60
ablation) before these pilots complete without non-finite losses or corrupted
artifacts.

```powershell
python scripts/run_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --family main_comparison --output-root runs/simulation `
  --simulation --max-jobs 1
```

## 4. Shared validation and sealed-test rules

Each checkpoint is evaluated on identical scenario IDs for paired comparisons:

```powershell
python scripts/evaluate.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --checkpoint $out\checkpoints\<job-id>.pt `
  --split validation --scenario val_001 --simulation
```

For matrix execution, use the batch entry point so every selected checkpoint is
evaluated on every registered scenario of its physical scale:

```powershell
python scripts/evaluate_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --family main_comparison --output-root $out `
  --split validation --simulation --max-jobs 5
```

The batch evaluator rejects missing/incomplete training jobs, validates any
existing evaluation row before reusing it, and fails on identity mismatches.
The current frozen implementation selects the final-update checkpoint for every
method. This rule is fair and test-independent but remains provisional; changing
to a validation-selected checkpoint requires a new frozen protocol and code
revision before sealed-test access.

Deterministic evaluation freezes actor normalization, return normalization,
optimizer state, and RNG state. Evaluation does not update learning state. A
`sealed_test` call is rejected until the parameter status and policy freeze
gate are verified; it must never fall back to a smoke or validation scenario.

After every controlled-simulation validation row exists, freeze the exact final-update
checkpoints, validation inputs, protocol, source tree, and pre-registered
statistics. The practical-equivalence margin and its agronomic basis must be
non-empty before this command can succeed:

```powershell
$jobFiles = (Get-ChildItem -LiteralPath $out\jobs -Filter "*.json").FullName
$validationLogs = (Get-ChildItem -LiteralPath $out\raw -Filter "evaluation-*-val_*.jsonl").FullName
python scripts/freeze_sealed_test.py freeze --simulation `
  --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --job-file $jobFiles `
  --validation $validationLogs `
  --output $out\validation-freeze.json
```

Issue the sealed-test ledger only after reviewing that immutable freeze. Pass
every registered sealed scenario explicitly; the example shows one scenario:

```powershell
python scripts/freeze_sealed_test.py unlock `
  --freeze $out\validation-freeze.json `
  --scenario test_001 `
  --output $out\sealed-unlock.json
```

Run the sealed matrix using both records:

```powershell
python scripts/evaluate_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --family main_comparison --output-root $out `
  --split sealed_test `
  --simulation `
  --max-jobs 150 `
  --freeze-manifest $out\validation-freeze.json `
  --sealed-unlock $out\sealed-unlock.json
```

Each `job_id x scenario_id` access first receives an exclusive reservation. It
is consumed only after the evaluation JSONL is atomically written, at which
point the ledger records its path, run ID, and SHA-256. Failed evaluations
release their reservation. The final Chapter 4.5 artifact build recomputes raw
hashes and verifies them against the frozen checkpoint identities.

## 5. Resource activation audit

Before interpreting a mobility result, audit the event-derived resource
metrics:

```powershell
python scripts/audit_resource_activation.py `
  $out\raw\evaluation-<job-id>-val_001.jsonl `
  --report $out\resource_activation.json
```

The report distinguishes total pesticide shortage from a spatial-temporal
mismatch. It requires request creation, transferred volume, waiting or
pesticide-disabled time, rendezvous distance, effective spraying time, and
conservation-compatible inventory fields. If requests are absent, the report
must not call the resource mechanism activated.

## 6. Chapter 4.5 artifact package

For the five-job CPU smoke, use the basic artifact command on one named
validation row. This checks the CSV/summary/figure/table path without treating
one scale and seed as a complete Chapter 4.5 family:

```powershell
python scripts/build_artifacts.py `
  $out\raw\evaluation-<job-id>-val_001.jsonl `
  --output $out\smoke-artifacts `
  --manifest $out\smoke-artifacts\evidence_manifest.json
```

Use the Chapter 4.5 package builder only after every registered job and shared
scenario for each included family exists:

```powershell
$evaluationLogs = (Get-ChildItem -LiteralPath $out\raw -Filter "evaluation-*.jsonl").FullName
python scripts/build_chapter45_artifacts.py `
  $evaluationLogs `
  --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --output $out\chapter45-artifacts `
  --allow-partial
```

`--allow-partial` is for pilot assembly only. It does not unlock a formal
claim. It permits entire experiment families to be absent, but rejects missing
conditions, training seeds, or scenarios inside any family that is present.
The package contains a validated long table, one locked summary, four
figure groups (`main_comparison`, `mechanism`, `sensitivity_adaptation`, and
`ablation`) in SVG/PDF/600-dpi PNG, five three-line-table TSV/Markdown pairs,
and `artifact_manifest.json`. The manifest records source hashes, protocol and
configuration identities, output hashes, uncertainty semantics, pairing unit,
condition labels, and maturity.

For a formal build, omit `--allow-partial` only after the complete matrix gate
passes. Any missing identity, stale hash, mixed provenance, duplicate run ID,
or provisional protocol must fail closed.

## 7. Statistics and evidence chain

Use training seeds as independent replications and scenarios as paired
observations within a trained policy. The hierarchical analysis resamples
paired seeds first and shared scenarios second, reports the estimate and
percentile interval, treats success probability as a paired risk difference,
and applies Holm correction to confirmatory comparisons. It does not treat 100
scenarios from one trained policy as 100 training seeds.

The required evidence chain is:

```text
engineering source/config -> immutable job -> raw JSONL -> validated table
-> paired statistics -> figure/table -> thesis prose
```

The checked-in OSM-derived road cache is a representative simulation
constraint, not a surveyed farm network. Synthetic roads remain available only
for isolated interface fixtures. The mobile-support hypothesis is interpreted
through the logged chain

```text
mobility -> rendezvous distance -> waiting/disabled time
-> effective spraying time -> reduction and 85% success
```

If an intermediate metric does not support the endpoint change, report the
mechanism as unresolved rather than selecting a favorable endpoint.

## 8. Verification commands

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
python scripts/run_matrix.py --config-dir configs --family main_comparison --output-root runs/planning --simulation --dry-run
```

The complete e2e suite performs real CPU updates and normally takes several
minutes. A timeout is not a pass; rerun with a sufficient process timeout and
inspect the per-directory test results.

## 9. Maturity gates and permitted claims

- **M0/M1:** concept or frozen design only; use proposed/planned wording.
- **M2 (current):** implementation tests verify interfaces, masks, event order,
  conservation, recovery, and artifact traceability. Do not claim efficacy.
- **M3:** multi-seed pilot on independent validation scenarios; use pilot
  results indicate wording.
- **M4:** frozen formal matrix plus one deterministic sealed-test evaluation and
  complete manifests; only then use formal paired-test wording.

Never weaken a rolling A* baseline, tune on sealed-test outcomes, fabricate
missing logs, or rename the flagship algorithm. The public algorithm name is
`SR-MAPPO` throughout.

The scenario factory uses the audited offline road derivative and a mechanistic
reaction-diffusion-advection-exposure model. M3 requires current resource
activation evidence and multi-seed validation pilots. M4 requires a frozen
simulation matrix, one-time sealed-test evaluation, paired statistics, and a
complete artifact manifest. These levels support controlled-simulation claims,
not field deployment claims.
