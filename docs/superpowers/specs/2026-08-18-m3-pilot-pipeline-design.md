# M3 Pilot Pipeline Design

Date: 2026-08-18

## 1. Purpose

This design moves the problem-2 project from M2 (implemented and tested) to
M3 (multi-seed pilot evidence on independent validation scenarios). It adds a
reusable pilot-selection, execution, evaluation, audit, and evidence pipeline
without weakening the complete Chapter 4.5 matrix rules.

M3 is reached only after the code is implemented and the registered pilot has
finished successfully. Passing tests alone leaves the project at M2.

The pilot remains a controlled road-constrained simulation. It does not use
the sealed-test split and does not support field-deployment claims.

## 2. Fixed Pilot Scope

The M3 pilot is a canonical subset of the existing
`configs/experiments/chapter4_5.yaml` main-comparison matrix:

| Dimension | Registered values |
| --- | --- |
| Family | `main_comparison` |
| Scales | `s1`, `s6` |
| Methods | `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`, `sr_mappo_two_stage` |
| Training seeds | `0`, `1`, `2`, `3`, `4` |
| Execution profile | `simulation` |
| Training budget | Full `total_updates` from the algorithm configuration |
| Evaluation split | `validation` only |
| Validation scenarios | Every registered validation scenario for `s1` and `s6` |

With the current protocol, this produces 50 canonical training jobs. The
current scenario registry contains two validation scenarios for each selected
scale, producing 100 evaluation rows.

The selector must derive methods, seeds, update budget, and scenario IDs from
the registered protocol/configuration and then assert the fixed M3 shape. It
must not create a second experiment protocol or use `condition_id=direct`.

## 3. Alternatives Considered

### 3.1 Canonical selection from the Chapter 4.5 matrix (selected)

Add deterministic filters to the existing orchestrator flow and audit the
selected canonical identities. The same completed identities can be reused by
the later controlled-simulation Chapter 4.5 matrix when source, configuration,
protocol, and execution-profile identities remain unchanged.

### 3.2 Separate M3 protocol (rejected)

A separate YAML file would be easy to execute, but it would create a second
protocol identity and weaken reuse and traceability when the project advances
to M4.

### 3.3 Direct training wrapper (rejected)

Calling `train.py` manually would bypass canonical matrix selection and risks
reintroducing diagnostic `direct` identities. Such output is useful for smoke
tests but is not sufficient M3 evidence.

## 4. Architecture

```text
Chapter45Orchestrator.plan("main_comparison", profile="simulation")
        |
        v
select_jobs(scales, methods, seeds)
        |
        +--> run_matrix.py ------> 50 recoverable training jobs
        |
        +--> evaluate_matrix.py -> 100 shared validation rows
        |
        v
M3 pilot manifest + resource-activation report
        |
        v
audit_m3_pilot.py
        |
        +--> m3-pilot-readiness.json
        |
        v
build_m3_pilot_artifacts.py
        |
        +--> validated rows, summaries, paired statistics, figures, tables,
             and evidence manifest
```

The existing job identity remains authoritative:

```text
method + scale + training_seed + config_hash + git_commit
+ execution_profile + protocol_hash + source_tree_hash
```

The M3 layer selects and validates canonical jobs; it does not define an
alternative identity.

## 5. Components

### 5.1 Shared canonical job selector

Add a pure selector in `src/problem2/experiments/orchestrator.py`, or a focused
module imported by it, with this conceptual interface:

```python
select_jobs(
    jobs,
    *,
    scales: Collection[str] = (),
    methods: Collection[str] = (),
    seeds: Collection[int] = (),
) -> tuple[PlannedJob, ...]
```

Rules:

- Empty filter collections mean no restriction for that dimension.
- Output order is the original canonical plan order.
- Every requested filter value must exist in the unfiltered plan.
- Unknown scales, methods, or seeds fail before any output directory is
  modified.
- Duplicate command-line values are normalized without duplicating jobs.
- The selector never rewrites job identities or interventions.

### 5.2 Matrix command-line filters

Extend `scripts/run_matrix.py` and `scripts/evaluate_matrix.py` with repeatable
arguments:

```text
--scale SCALE
--method METHOD
--seed INTEGER
```

Filtering occurs after canonical planning and before `--max-jobs`. The emitted
JSON records both the unfiltered family count and filtered selection count.
`--max-jobs` remains a bounded execution/recovery control and is not treated as
an experiment definition.

Dry-run output must expose the exact selected identities without writing run
artifacts. Training and evaluation reuse the existing atomic checkpoint,
recovery, and evaluation-identity checks.

### 5.3 Frozen M3 pilot manifest

Add `src/problem2/experiments/m3_pilot.py` and
`scripts/prepare_m3_pilot.py`. Preparation performs a side-effect-free
canonical plan and writes one immutable manifest containing:

- M3 profile version;
- creation time;
- repository commit and clean-tree status;
- source-tree, configuration, and protocol hashes;
- fixed family, execution profile, scales, methods, seeds, and scenario IDs;
- all 50 expected job IDs and their identity fields;
- all 100 expected evaluation keys;
- resource-activation report path and hash;
- expected update budget and checkpoint-selection rule.

Preparation fails on a dirty worktree, an unexpected protocol shape, missing
validation scenarios, or a resource report that does not show the active
pesticide-service chain. An existing manifest is reused only when its semantic
identity and referenced hashes match. The original creation time and bytes are
preserved; a conflicting manifest is never silently overwritten.

### 5.4 M3 readiness audit

Add `scripts/audit_m3_pilot.py`. It reads the frozen manifest and output root,
performs every check, writes `m3-pilot-readiness.json`, and returns a non-zero
exit status when `m3_ready` is false.

Required checks:

1. Manifest shape is exactly 2 scales x 5 methods x 5 seeds.
2. Every expected job record exists exactly once and has status `completed`.
3. Job identities, config/protocol/source hashes, and execution profile match
   the manifest.
4. Each checkpoint exists, its SHA-256 matches the job record, and its step is
   the registered final update.
5. Every expected validation row exists exactly once, with the registered
   shared scenario, split, job identity, checkpoint hash, and run ID.
6. There are exactly 100 finite validation rows and no failed expected job.
7. Primary and mechanism fields required by the Chapter 4.5 contract are
   present and finite.
8. The resource-activation report is current, hash-matched, and reports
   `resource_service_chain_activated`.
9. No sealed-test row is consumed or included.
10. All provenance paths and hashes used by the report are recorded.

The report contains per-check status and diagnostics even when the overall
audit fails. Existing raw evidence is preserved.

### 5.5 M3 pilot artifact builder

Add `src/problem2/artifacts/m3_pilot.py` and
`scripts/build_m3_pilot_artifacts.py`. This builder validates against the M3
manifest instead of weakening `build_chapter45_artifacts.py` completeness
rules.

It produces, from the same validated rows:

- `m3-validation-long.csv`;
- seed/scenario-level descriptive summaries;
- paired differences between `sr_mappo_mobile` and each registered comparator;
- hierarchical paired-bootstrap intervals using the protocol settings;
- reduction-rate and 85%-success summaries;
- mechanism summaries for rendezvous distance, wait/disabled time, effective
  spraying time, transfers, vehicle movement, and decision runtime;
- pilot diagnostic figures and CSV-backed three-line-table source files;
- an artifact manifest with input and output hashes.

All outputs are labelled `pilot`, `validation`, and `controlled_simulation`.
The builder does not write Word files and does not state that SR-MAPPO wins.

## 6. Data Flow and Recovery

1. Commit and push the tested M3 pipeline so the worktree is clean.
2. Run technical dry-run selection and prepare the immutable M3 manifest.
3. Execute the 50 training identities. Existing completed identities are
   reused; failed identities can be rerun individually with the same filters.
4. Evaluate every completed identity on its two registered validation
   scenarios. Existing valid rows are reused byte-for-byte.
5. Run the M3 audit. Failure preserves all raw jobs and rows and identifies the
   first broken evidence link.
6. Build artifacts only after the readiness audit passes.

The pipeline must not retry by changing hyperparameters, lowering update
budgets, selecting favourable seeds, or removing a comparator. A bug fix that
changes tracked source produces a new source identity and therefore a new
pilot manifest and affected job identities.

## 7. Error Handling

- CLI boundaries emit one machine-readable JSON object on success or failure.
- Invalid selectors fail before filesystem mutation.
- Missing, duplicate, malformed, stale, or non-finite artifacts fail closed.
- Checkpoint mismatches identify the path, expected identity, and observed
  value.
- Training failures keep their job records and can be rerun without deleting
  successful jobs.
- Audit failures never delete or rewrite raw logs.
- Sealed-test input is explicitly rejected by the M3 auditor and builder.

## 8. Testing Strategy

Implementation follows test-driven development.

Unit tests cover:

- selector ordering, empty filters, combined filters, duplicates, and unknown
  values;
- exact M3 manifest counts and hash stability;
- dirty-tree, missing-scenario, and inactive-resource rejection;
- readiness checks for missing, duplicate, stale, non-finite, wrong-step, and
  wrong-checkpoint artifacts;
- artifact-builder completeness and provenance.

CLI/integration tests cover:

- dry-run selection of exactly 50 canonical jobs;
- a reduced smoke fixture using the same selection path;
- filtered training recovery without retraining completed jobs;
- filtered evaluation of all shared scale scenarios and output reuse;
- successful and failing readiness reports;
- explicit rejection of sealed-test rows.

Before each implementation commit, run the relevant tests. Before push, run:

```powershell
python -m pytest -q
python -m compileall -q src scripts tests
git diff --check
```

## 9. Operational Commands

The final runbook will provide exact Windows commands. The intended sequence
is:

```powershell
python scripts/run_matrix.py --family main_comparison --simulation \
  --scale s1 --scale s6 --method <repeat-for-five-methods> \
  --seed 0 --seed 1 --seed 2 --seed 3 --seed 4 --dry-run

python scripts/prepare_m3_pilot.py <registered paths>
python scripts/run_matrix.py <same canonical selection> --max-jobs 50
python scripts/evaluate_matrix.py <same canonical selection> \
  --split validation --max-jobs 50
python scripts/audit_m3_pilot.py <manifest and output paths>
python scripts/build_m3_pilot_artifacts.py <manifest and output paths>
```

PowerShell examples will use backticks or argument arrays rather than the
illustrative backslashes shown above.

## 10. Acceptance Criteria

The code change is complete when:

- all selector, manifest, audit, artifact, CLI, and regression tests pass;
- the repository compiles and `git diff --check` passes;
- the implementation and runbook are committed and pushed;
- a dry run proves that the current protocol selects exactly 50 canonical M3
  training jobs and 100 expected validation rows.

The project reaches M3 only when, in addition:

- all 50 full-budget controlled-simulation jobs complete;
- all 100 independent validation rows complete;
- the resource-service chain remains activated;
- `m3-pilot-readiness.json` reports `m3_ready: true`;
- the M3 evidence package is built from the audited inputs.

At M3, permitted wording is limited to "pilot results indicate" or equivalent
provisional language. Formal Chapter 4.5 claims require the later frozen M4
matrix and sealed-test evidence.

## 11. Explicit Non-Goals

- No sealed-test unlock or evaluation.
- No change to the public SR-MAPPO algorithm name.
- No HAPPO or AG-SR-MAPPO implementation.
- No Word-document modification.
- No field-validation claim.
- No relaxation of the full Chapter 4.5 artifact completeness contract.
- No automatic claim that the proposed method is superior.
