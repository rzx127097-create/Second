# M3 Pilot Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run an auditable 50-job, 100-validation-row controlled-simulation pilot that can advance problem 2 from M2 to M3 without accessing the sealed test set.

**Architecture:** Select a canonical `s1`/`s6` subset from the existing Chapter 4.5 matrix, preserve its immutable job identities, freeze the selection in an M3 manifest, and validate every job/checkpoint/evaluation link before producing pilot-only statistics and artifacts. The full Chapter 4.5 completeness rules remain unchanged; M3 receives a separate strict subset contract.

**Tech Stack:** Python 3.11+, `dataclasses`, `argparse`, JSON/JSONL/CSV, SHA-256, NumPy, PyYAML, matplotlib, PyTorch checkpoint files, pytest, PowerShell, Git.

**Spec:** `docs/superpowers/specs/2026-08-18-m3-pilot-pipeline-design.md`

## Global Constraints

- Keep the public algorithm name `SR-MAPPO`; do not add HAPPO or `AG-SR-MAPPO`.
- Use `configs/experiments/chapter4_5.yaml`; do not create a second M3 experiment protocol.
- The fixed pilot is `main_comparison`, scales `s1` and `s6`, all five registered methods, seeds `0` through `4`, full configured update budget, and `simulation` execution profile.
- Evaluate validation scenarios only; reject and never read the sealed-test split in the M3 audit/artifact path.
- Preserve `JobIdentity`; selection must not rewrite `condition_id`, hashes, intervention, or job ID.
- Require current resource-service activation evidence before freezing an M3 manifest.
- Label all results `pilot`, `validation`, and `controlled_simulation`; do not infer method superiority automatically.
- Do not modify Word documents.
- Write tests before implementation; never skip, weaken, or falsify a failing test.
- Use the isolated worktree `C:\Users\RZX\Desktop\论文\毕业论文\Second\.worktrees\problem2-code-framework` and branch `feature/problem2-code-framework`.
- Use `C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe` for verification.
- Commit each independently testable task and push after the full implementation passes.

## File Structure

| File | Responsibility |
| --- | --- |
| `src/problem2/experiments/orchestrator.py` | Pure canonical job filtering, retaining existing planning and identity behavior. |
| `scripts/run_matrix.py` | Repeatable scale/method/seed filters for training. |
| `scripts/evaluate_matrix.py` | The same filters for shared-scenario validation. |
| `src/problem2/experiments/m3_pilot.py` | Fixed M3 profile, manifest creation/loading, expected evaluation identities, and atomic manifest persistence. |
| `scripts/prepare_m3_pilot.py` | Machine-readable CLI that freezes the current canonical M3 manifest. |
| `src/problem2/experiments/m3_audit.py` | Job, checkpoint, evaluation, resource, provenance, and sealed-split readiness checks. |
| `scripts/audit_m3_pilot.py` | Machine-readable audit CLI and report writer. |
| `src/problem2/artifacts/m3_pilot.py` | Manifest-bound M3 statistics, pilot figures/tables, and evidence manifest. |
| `scripts/build_m3_pilot_artifacts.py` | Artifact CLI that requires a passing readiness report. |
| `tests/experiments/test_orchestrator.py` | Selector unit tests. |
| `tests/e2e/test_chapter45_smoke.py` | Training/evaluation CLI filter tests. |
| `tests/experiments/test_m3_pilot.py` | Manifest and readiness-audit unit tests. |
| `tests/experiments/test_m3_artifacts.py` | Exact-subset artifact and traceability tests. |
| `tests/m3_fixtures.py` | Shared constructor for complete 50-job/100-row synthetic evidence used only by tests. |
| `docs/verification/section-4-5-runbook.md` | Exact preparation, run, resume, audit, and artifact commands. |

---

### Task 1: Canonical Job Selection

**Files:**
- Modify: `src/problem2/experiments/orchestrator.py:17-134`
- Modify: `tests/experiments/test_orchestrator.py:1-65`

**Interfaces:**
- Consumes: `tuple[PlannedJob, ...]` returned by `Chapter45Orchestrator.plan()`.
- Produces: `select_jobs(jobs, *, scales=(), methods=(), seeds=()) -> tuple[PlannedJob, ...]`.

- [ ] **Step 1: Write failing selector tests**

Add tests that assert the exact M3 shape, original plan ordering, duplicate-filter normalization, and fail-fast unknown values:

```python
from problem2.experiments.orchestrator import Chapter45Orchestrator, select_jobs


def test_select_jobs_builds_canonical_m3_subset(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    planned = orchestrator.plan("main_comparison", execution_profile="simulation")
    selected = select_jobs(
        planned,
        scales=("s1", "s6"),
        methods=orchestrator.spec.main_methods,
        seeds=(0, 1, 2, 3, 4),
    )

    assert len(selected) == 50
    assert {job.identity.scale for job in selected} == {"s1", "s6"}
    assert {job.identity.method for job in selected} == set(orchestrator.spec.main_methods)
    assert {job.identity.training_seed for job in selected} == {0, 1, 2, 3, 4}
    assert selected == tuple(job for job in planned if job.identity.scale in {"s1", "s6"})
    assert all(job.identity.condition_id != "direct" for job in selected)


def test_select_jobs_normalizes_duplicates_and_rejects_unknowns(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path)
    planned = orchestrator.plan("main_comparison", execution_profile="simulation")
    assert len(select_jobs(planned, scales=("s1", "s1"), seeds=(0, 0))) == 5
    with pytest.raises(ValueError, match="unknown scale.*s9"):
        select_jobs(planned, scales=("s9",))
    with pytest.raises(ValueError, match="unknown method.*happpo"):
        select_jobs(planned, methods=("happpo",))
    with pytest.raises(ValueError, match="unknown seed.*99"):
        select_jobs(planned, seeds=(99,))
```

- [ ] **Step 2: Run the tests and verify the missing import failure**

Run:

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/experiments/test_orchestrator.py -q
```

Expected: FAIL because `select_jobs` does not exist.

- [ ] **Step 3: Implement the pure selector**

Add this public function and export it from `orchestrator.py`:

```python
def select_jobs(
    jobs: tuple[PlannedJob, ...],
    *,
    scales: Collection[str] = (),
    methods: Collection[str] = (),
    seeds: Collection[int] = (),
) -> tuple[PlannedJob, ...]:
    requested_scales = tuple(dict.fromkeys(str(value) for value in scales))
    requested_methods = tuple(dict.fromkeys(str(value) for value in methods))
    requested_seeds = tuple(dict.fromkeys(int(value) for value in seeds))
    available_scales = {job.identity.scale for job in jobs}
    available_methods = {job.identity.method for job in jobs}
    available_seeds = {job.identity.training_seed for job in jobs}
    for kind, requested, available in (
        ("scale", requested_scales, available_scales),
        ("method", requested_methods, available_methods),
        ("seed", requested_seeds, available_seeds),
    ):
        unknown = [value for value in requested if value not in available]
        if unknown:
            raise ValueError(f"unknown {kind} filter values: {unknown}")
    return tuple(
        job for job in jobs
        if (not requested_scales or job.identity.scale in requested_scales)
        and (not requested_methods or job.identity.method in requested_methods)
        and (not requested_seeds or job.identity.training_seed in requested_seeds)
    )
```

Import `Collection` from `collections.abc` and add `select_jobs` to `__all__`.

- [ ] **Step 4: Run selector tests**

Run the command from Step 2.

Expected: all orchestrator tests PASS and the existing 150/90/150/120/60 family counts remain unchanged.

- [ ] **Step 5: Commit the selector**

```powershell
git add src/problem2/experiments/orchestrator.py tests/experiments/test_orchestrator.py
git commit -m "feat: add canonical experiment job selection"
```

---

### Task 2: Filtered Training and Evaluation CLIs

**Files:**
- Modify: `scripts/run_matrix.py:24-132`
- Modify: `scripts/evaluate_matrix.py:92-242`
- Modify: `tests/e2e/test_chapter45_smoke.py:1-220`

**Interfaces:**
- Consumes: `select_jobs()` from Task 1.
- Produces: repeatable `--scale`, `--method`, and `--seed` arguments on both matrix CLIs.

- [ ] **Step 1: Write failing dry-run and validation filter tests**

Add a dry-run test for exactly 50 simulation identities and a fail-fast invalid filter test:

```python
def test_m3_filters_select_exactly_fifty_canonical_jobs(tmp_path: Path) -> None:
    arguments = [
        "--config-dir", "configs", "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison", "--output-root", str(tmp_path),
        "--simulation", "--dry-run", "--scale", "s1", "--scale", "s6",
    ]
    for method in (
        "sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar",
        "mappo_mobile", "sr_mappo_two_stage",
    ):
        arguments.extend(("--method", method))
    for seed in range(5):
        arguments.extend(("--seed", str(seed)))
    result, payload = _run(*arguments)
    assert result.returncode == 0
    assert payload["family_job_count"] == 150
    assert payload["selected_job_count"] == 50
    assert len(payload["jobs"]) == 50
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_matrix_filters_reject_unknown_values_before_writes(tmp_path: Path) -> None:
    result, payload = _run(
        "--config-dir", "configs", "--family", "main_comparison",
        "--output-root", str(tmp_path), "--simulation", "--dry-run",
        "--scale", "s9",
    )
    assert result.returncode != 0
    assert "unknown scale" in payload["error"]
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []
```

Extend the existing matrix-evaluation smoke test to pass `--scale s1`,
`--method sr_mappo_mobile`, and `--seed 0`, then assert
`selected_job_count == 1` and `family_job_count == 150`.

- [ ] **Step 2: Verify tests fail on unknown CLI arguments**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/e2e/test_chapter45_smoke.py -q
```

Expected: FAIL because the new selector arguments are not registered.

- [ ] **Step 3: Implement identical filter parsing and ordering in both CLIs**

In each parser add:

```python
parser.add_argument("--scale", action="append", default=[])
parser.add_argument("--method", action="append", default=[])
parser.add_argument("--seed", action="append", type=int, default=[])
```

After obtaining the canonical family plan, apply:

```python
family_jobs = orchestrator.plan(args.family, execution_profile=execution_profile)
jobs = select_jobs(
    family_jobs,
    scales=args.scale,
    methods=args.method,
    seeds=args.seed,
)
```

Apply `--max-jobs` only after filtering. Emit these unambiguous fields from
both CLIs:

```python
"family_job_count": len(family_jobs),
"selected_job_count": len(jobs),
"executed_job_count": len(selected),
```

For backwards compatibility, retain `total_count` as `len(jobs)` in
`run_matrix.py` and `total_job_count` as `len(jobs)` in
`evaluate_matrix.py`. In dry-run output, `jobs` contains the complete filtered
selection and no output directory is created.

- [ ] **Step 4: Run focused and existing e2e tests**

```powershell
& $python -m pytest tests/experiments/test_orchestrator.py tests/e2e/test_chapter45_smoke.py -q
```

Expected: PASS, including existing resume and evaluation-reuse behavior.

- [ ] **Step 5: Commit the CLI filters**

```powershell
git add scripts/run_matrix.py scripts/evaluate_matrix.py tests/e2e/test_chapter45_smoke.py
git commit -m "feat: filter canonical matrix jobs"
```

---

### Task 3: Frozen M3 Pilot Manifest

**Files:**
- Create: `src/problem2/experiments/m3_pilot.py`
- Create: `scripts/prepare_m3_pilot.py`
- Create: `tests/experiments/test_m3_pilot.py`
- Modify: `src/problem2/experiments/__init__.py`

**Interfaces:**
- Consumes: `Chapter45Orchestrator`, `select_jobs`, a current resource-activation JSON report, and the registered validation scenario list.
- Produces: `M3PilotProfile`, `build_m3_manifest()`, `load_m3_manifest()`, `write_m3_manifest()`, and a schema-versioned immutable JSON manifest.

- [ ] **Step 1: Write failing profile and manifest tests**

Create a fixture that writes a current resource report using the orchestrator's
actual config, commit, and source hashes. Test exact counts and semantic reuse:

```python
def _resource_report(orchestrator: Chapter45Orchestrator, path: Path) -> Path:
    payload = {
        "activated": True,
        "diagnosis": "resource_service_chain_activated",
        "config_hash": orchestrator.config_hash,
        "git_commit": orchestrator.git_provenance.commit,
        "source_tree_hash": orchestrator.git_provenance.source_tree_hash,
        "simulation_profile_sha256": "a" * 64,
        "record_count": 45,
        "provisional": True,
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_m3_manifest_has_fifty_jobs_and_one_hundred_evaluations(tmp_path: Path) -> None:
    orchestrator = Chapter45Orchestrator(ROOT / "configs", tmp_path / "runs")
    orchestrator.git_provenance = GitProvenance(
        orchestrator.git_commit, orchestrator.git_provenance.source_tree_hash, False,
    )
    report = _resource_report(orchestrator, tmp_path / "resource.json")
    manifest = build_m3_manifest(orchestrator, resource_report_path=report)
    assert manifest["schema_version"] == 1
    assert manifest["profile"]["scales"] == ["s1", "s6"]
    assert len(manifest["jobs"]) == 50
    assert len(manifest["evaluations"]) == 100
    assert {row["scenario_id"] for row in manifest["evaluations"]} == {
        "val_001", "val_s1_002", "val_s6_001", "val_s6_002",
    }
    assert len({row["job_id"] for row in manifest["jobs"]}) == 50
    assert all(row["split"] == "validation" for row in manifest["evaluations"])
```

Also test rejection of dirty provenance, inactive diagnosis, stale config hash,
missing `s6` validation scenarios, and an existing conflicting manifest.

- [ ] **Step 2: Verify the new module import fails**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/experiments/test_m3_pilot.py -q
```

Expected: FAIL because `problem2.experiments.m3_pilot` does not exist.

- [ ] **Step 3: Implement the fixed profile and manifest schema**

Define `M3PilotProfile` exactly as follows:

```python
@dataclass(frozen=True)
class M3PilotProfile:
    version: int = 1
    family: str = "main_comparison"
    execution_profile: str = "simulation"
    scales: tuple[str, ...] = ("s1", "s6")
    methods: tuple[str, ...] = (
        "sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar",
        "mappo_mobile", "sr_mappo_two_stage",
    )
    training_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    split: str = "validation"


```

Implement these exact public signatures: `build_m3_manifest(orchestrator:
Chapter45Orchestrator, *, resource_report_path: str | Path, created_at: str |
None = None) -> dict[str, object]`, `write_m3_manifest(path: str | Path,
manifest: Mapping[str, object]) -> tuple[Path, bool]`, and
`load_m3_manifest(path: str | Path) -> dict[str, object]`. The Boolean returned
by `write_m3_manifest` is `True` only when an existing semantically identical
manifest was reused.

The implementation must:

- require a clean worktree;
- assert protocol methods and seeds exactly equal the fixed profile;
- select canonical simulation jobs with `select_jobs()`;
- derive scenario IDs from `config.experiments["validation_scenarios"]` by scale;
- assert two validation scenarios for each selected scale;
- record job identities with expected `f"jobs/{job_id}.json"` and
  `f"checkpoints/{job_id}.pt"` relative paths;
- record evaluation keys and expected
  `f"raw/evaluation-{job_id}-{scenario_id}.jsonl"` relative paths;
- store the resource-report SHA-256 and provenance;
- calculate `semantic_sha256` over canonical JSON excluding `created_at` and
  `semantic_sha256` itself;
- atomically write new manifests;
- reuse an existing manifest only when `semantic_sha256` matches, preserving
  its original bytes and creation time;
- reject conflicting existing files.

- [ ] **Step 4: Implement the preparation CLI**

Use exact arguments:

```python
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--protocol", type=Path)
parser.add_argument("--output-root", type=Path, required=True)
parser.add_argument("--resource-report", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
```

The CLI prints one JSON object with `status`, `manifest`, `semantic_sha256`,
`job_count`, `evaluation_count`, and `reused`, and returns nonzero on any
validation failure.

- [ ] **Step 5: Run unit and CLI tests**

```powershell
& $python -m pytest tests/experiments/test_m3_pilot.py -q
& $python -m compileall -q src/problem2/experiments/m3_pilot.py scripts/prepare_m3_pilot.py
```

Expected: PASS with exact counts 50 and 100.

- [ ] **Step 6: Commit the manifest subsystem**

```powershell
git add src/problem2/experiments/m3_pilot.py src/problem2/experiments/__init__.py scripts/prepare_m3_pilot.py tests/experiments/test_m3_pilot.py
git commit -m "feat: freeze canonical M3 pilot manifests"
```

---

### Task 4: M3 Readiness Audit

**Files:**
- Create: `src/problem2/experiments/m3_audit.py`
- Create: `scripts/audit_m3_pilot.py`
- Create: `tests/m3_fixtures.py`
- Modify: `tests/experiments/test_m3_pilot.py`

**Interfaces:**
- Consumes: one frozen M3 manifest, its output root, job records, checkpoints, validation JSONL files, and the manifest-bound resource report.
- Produces: `audit_m3_pilot() -> dict[str, object]` and `m3-pilot-readiness.json` with `m3_ready` plus per-check diagnostics.

- [ ] **Step 1: Add failing complete and incomplete audit tests**

Create `tests/m3_fixtures.py` with
`materialize_complete_m3_evidence(manifest: Mapping[str, object], run_root:
Path) -> list[Path]`. It materializes all 50 `JobRecord` files, 50 checkpoint
files, and 100 strict evaluation rows and returns the evaluation paths. Each
evaluation row must include all fields in `M3_REQUIRED_METRICS`:

```python
M3_REQUIRED_METRICS = (
    "reduction_rate", "success", "transferred_l", "request_count",
    "request_completion_rate", "requested_l", "request_wait_mean_s",
    "request_wait_p90_s", "wait_s", "pesticide_disabled_s",
    "effective_spray_s", "service_s", "rendezvous_road_distance_m",
    "uav_rendezvous_distance_m", "vehicle_distance_m", "vehicle_idle_s",
    "vehicle_inventory_initial_l", "vehicle_inventory_final_l",
    "vehicle_inventory_utilization", "decision_time_mean_ms",
)
```

The success test asserts:

```python
report = audit_m3_pilot(manifest_path, output_root=run_root)
assert report["m3_ready"] is True
assert report["highest_maturity"] == "M3"
assert report["counts"] == {
    "expected_jobs": 50, "completed_jobs": 50,
    "expected_evaluations": 100, "valid_evaluations": 100,
}
assert all(check["passed"] for check in report["checks"])
```

Parameterized failing cases must cover one missing job, `failed` status,
checkpoint SHA mismatch, checkpoint step below `target_updates`, duplicate
run ID, non-finite metric, stale resource hash, identity mismatch, and a
`sealed_test` row. Each case must return `m3_ready: false` with a named failed
check while preserving the source files.

- [ ] **Step 2: Run tests and verify the audit import fails**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/experiments/test_m3_pilot.py -q
```

Expected: FAIL because `m3_audit.py` is absent.

- [ ] **Step 3: Implement audit checks as independent named functions**

Use a small result helper so one failed check does not hide remaining
diagnostics:

```python
@dataclass(frozen=True)
class AuditCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


```

Implement the exact public signature `audit_m3_pilot(manifest_path: str |
Path, *, output_root: str | Path) -> dict[str, object]`.

Implement checks named:

```text
manifest_shape
resource_activation
job_records
checkpoint_integrity
evaluation_identity
metric_finiteness
sealed_test_exclusion
provenance_chain
```

Use `load_job_record()` for persisted identities, recompute checkpoint hashes,
require `checkpoint_step == target_updates`, require exactly one JSON object per
expected evaluation file, and call `validate_episode_records(rows, strict=True)`
on the combined rows. Validate every row against its manifest job/scenario key,
including `run_id == f"{job_id}:0:{scenario_id}"`, `split == "validation"`,
`execution_profile == "simulation"`, checkpoint SHA/step, family, condition,
config/protocol/source hashes, and finite required metrics.

The audit must return a report even when evidence is incomplete. Set
`highest_maturity` to `M3` only when all checks pass; otherwise set it to `M2`.
The report must include `manifest_semantic_sha256` and a
`report_semantic_sha256` calculated from canonical JSON after excluding only
`report_semantic_sha256`. This makes manual alteration detectable by the
artifact builder.

- [ ] **Step 4: Implement atomic audit CLI reporting**

Use arguments:

```python
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--output-root", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
```

Write JSON through a temporary file plus `os.replace`, print the same report as
one compact JSON object, and return `0` only when `m3_ready` is true.

- [ ] **Step 5: Run audit tests and compilation**

```powershell
& $python -m pytest tests/experiments/test_m3_pilot.py -q
& $python -m compileall -q src/problem2/experiments/m3_audit.py scripts/audit_m3_pilot.py
```

Expected: all success and failure-path tests PASS.

- [ ] **Step 6: Commit the readiness audit**

```powershell
git add src/problem2/experiments/m3_audit.py scripts/audit_m3_pilot.py tests/m3_fixtures.py tests/experiments/test_m3_pilot.py
git commit -m "feat: audit M3 pilot readiness"
```

---

### Task 5: Manifest-Bound M3 Evidence Package

**Files:**
- Create: `src/problem2/artifacts/m3_pilot.py`
- Create: `scripts/build_m3_pilot_artifacts.py`
- Create: `tests/experiments/test_m3_artifacts.py`
- Modify: `src/problem2/artifacts/__init__.py`

**Interfaces:**
- Consumes: a passing readiness report, its frozen manifest, all manifest-listed validation rows, current configuration, and the Chapter 4.5 protocol.
- Produces: `build_m3_pilot_artifacts()` and a hash-linked pilot evidence package.

- [ ] **Step 1: Write failing exact-package tests**

Import `materialize_complete_m3_evidence` from `tests.m3_fixtures`, build the
complete fixed manifest from Task 3, materialize all evidence under the test
run root, write the passing readiness report returned by `audit_m3_pilot`, and
assert:

```python
bundle = build_m3_pilot_artifacts(
    manifest_path,
    readiness_path,
    tmp_path / "artifacts",
    config_dir=ROOT / "configs",
    protocol_path=ROOT / "configs" / "experiments" / "chapter4_5.yaml",
)
assert bundle.paths["validated_csv"].is_file()
assert bundle.paths["locked_summary_json"].is_file()
assert bundle.paths["main_comparison_svg"].is_file()
assert bundle.paths["main_comparison_pdf"].is_file()
assert bundle.paths["main_comparison_png"].is_file()
assert bundle.paths["main_comparison_table_tsv"].is_file()
summary = json.loads(bundle.paths["locked_summary_json"].read_text(encoding="utf-8"))
assert summary["maturity"] == "m3_pilot_validation_controlled_simulation"
assert summary["record_count"] == 100
assert summary["identity"]["split"] == ["validation"]
assert summary["uncertainty"]["confirmatory"] is False
```

Add rejection tests for `m3_ready: false`, a changed readiness field without a
matching `report_semantic_sha256`, a manifest hash mismatch, missing evaluation
input, extra manifest evaluation, mixed checkpoint provenance, and sealed-test
input.

- [ ] **Step 2: Verify the artifact module import fails**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/experiments/test_m3_artifacts.py -q
```

Expected: FAIL because `problem2.artifacts.m3_pilot` does not exist.

- [ ] **Step 3: Implement manifest-bound input loading and summaries**

Define:

```python
@dataclass(frozen=True)
class M3ArtifactBundle:
    paths: dict[str, Path]


```

Implement the exact public signature
`build_m3_pilot_artifacts(manifest_path: str | Path, readiness_path: str |
Path, output_root: str | Path, *, config_dir: str | Path, protocol_path: str |
Path) -> M3ArtifactBundle`.

The builder must first recompute `report_semantic_sha256`, verify the readiness
file has `m3_ready: true`, verify `manifest_semantic_sha256` against the loaded
manifest, and hash every evaluation file again. Read only manifest-listed
validation paths. Call `validate_episode_records(rows,
strict=True)`, add `analysis_group = method`, and use:

```python
summaries = summarize_metric_groups(
    rows,
    group_fields=("family", "analysis_group", "method", "scale"),
    metrics=METRICS + ("vehicle_inventory_initial_l", "vehicle_inventory_final_l"),
    draws=int(spec.statistics["bootstrap_draws"]),
    seed=0,
    confidence_level=float(spec.statistics["confidence_level"]),
)
```

Compute `main_reduction` and `main_success` with
`hierarchical_paired_summary()`, reference `sr_mappo_mobile`, the protocol
pairing unit, and `confirmatory=False`. Do not assign significance or
superiority labels.

- [ ] **Step 4: Reuse existing Nature-style main figure and three-line table writers**

Build a locked summary with only the complete M3 main-comparison family:

```python
locked_summary = {
    "schema_version": 1,
    "locked": True,
    "maturity": "m3_pilot_validation_controlled_simulation",
    "record_count": len(rows),
    "identity": identity,
    "uncertainty": {
        "pairing_unit": spec.statistics["pairing_unit"],
        "bootstrap_draws": int(spec.statistics["bootstrap_draws"]),
        "confidence_level": float(spec.statistics["confidence_level"]),
        "multiplicity": spec.statistics["multiplicity"],
        "practical_equivalence_margin": spec.statistics["practical_equivalence_margin"],
        "practical_equivalence_basis": spec.statistics["practical_equivalence_basis"],
        "confirmatory": False,
    },
    "metric_definitions": METRIC_DEFINITIONS,
    "families": {"main_comparison": summaries},
    "paired": {"main_reduction": paired_reduction, "main_success": paired_success},
}
```

Use `build_chapter45_figures(locked_summary, figure_root,
allow_partial=True)` and `build_chapter45_tables(locked_summary, table_root,
allow_partial=True)` so output styling remains
consistent while the full-family completeness validator remains untouched.
Write `m3-validation-long.csv`, `locked_summary.json`, figures in SVG/PDF/600
dpi PNG, table TSV/Markdown, and `m3-artifact-manifest.json`. The manifest must
hash the M3 manifest, readiness report, resource report, every raw evaluation,
and every generated output.

- [ ] **Step 5: Implement the artifact CLI**

Use exact arguments:

```python
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--readiness", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--protocol", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
```

Print one JSON object containing `status` and all output paths. Return nonzero
without partial outputs if the readiness or evidence identity is invalid.

- [ ] **Step 6: Run artifact tests and compilation**

```powershell
& $python -m pytest tests/experiments/test_m3_artifacts.py tests/experiments/test_chapter45_artifacts.py tests/artifacts/test_traceability.py -q
& $python -m compileall -q src/problem2/artifacts/m3_pilot.py scripts/build_m3_pilot_artifacts.py
```

Expected: PASS; existing full Chapter 4.5 incomplete-family rejection still
passes unchanged.

- [ ] **Step 7: Commit the evidence package**

```powershell
git add src/problem2/artifacts/m3_pilot.py src/problem2/artifacts/__init__.py scripts/build_m3_pilot_artifacts.py tests/experiments/test_m3_artifacts.py
git commit -m "feat: build traceable M3 pilot evidence"
```

---

### Task 6: End-to-End Regression and Runbook

**Files:**
- Modify: `tests/e2e/test_chapter45_smoke.py`
- Modify: `docs/verification/section-4-5-runbook.md`

**Interfaces:**
- Consumes: all Tasks 1-5.
- Produces: one tested Windows execution sequence and regression proof that filtered smoke jobs resume and validation rows are reused.

- [ ] **Step 1: Add an end-to-end filtered smoke recovery test**

Run one selected identity twice and then evaluate it twice:

```python
def test_filtered_smoke_job_and_validation_resume_by_identity(tmp_path: Path) -> None:
    train_args = (
        "--config-dir", "configs", "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison", "--output-root", str(tmp_path),
        "--smoke", "--scale", "s1", "--method", "sr_mappo_mobile",
        "--seed", "0", "--max-jobs", "1",
    )
    first_result, first = _run(*train_args)
    second_result, second = _run(*train_args)
    assert first_result.returncode == second_result.returncode == 0
    assert first["jobs"][0]["job_id"] == second["jobs"][0]["job_id"]
    job_path = Path(first["jobs"][0]["output"]["job_file"])
    assert json.loads(job_path.read_text(encoding="utf-8"))["attempts"] == 1

    evaluate_args = (
        "--config-dir", "configs", "--protocol", "configs/experiments/chapter4_5.yaml",
        "--family", "main_comparison", "--output-root", str(tmp_path),
        "--split", "validation", "--smoke", "--scale", "s1",
        "--method", "sr_mappo_mobile", "--seed", "0", "--max-jobs", "1",
    )
    evaluated_first, payload_first = _run_script("evaluate_matrix.py", *evaluate_args)
    evaluated_second, payload_second = _run_script("evaluate_matrix.py", *evaluate_args)
    assert evaluated_first.returncode == evaluated_second.returncode == 0
    assert len(payload_first["evaluations"]) == 2
    assert all(item["reused"] is True for item in payload_second["evaluations"])
```

- [ ] **Step 2: Run the focused end-to-end test**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest tests/e2e/test_chapter45_smoke.py -q
```

Expected: PASS with one training attempt and byte-stable validation reuse.

- [ ] **Step 3: Add exact M3 commands to the runbook**

Document these variables and commands without abbreviations:

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
$runRoot = "runs\m3-pilot"
$resourceRoot = "runs\m3-resource-pilot"
$methods = @("sr_mappo_mobile", "sr_mappo_fixed", "sr_mappo_astar", "mappo_mobile", "sr_mappo_two_stage")
$selection = @("--scale", "s1", "--scale", "s6")
foreach ($method in $methods) { $selection += @("--method", $method) }
foreach ($seed in 0..4) { $selection += @("--seed", "$seed") }

& $python scripts/run_resource_pilot.py --config-dir configs `
  --output "$resourceRoot\raw.jsonl" --report "$resourceRoot\activation.json" `
  --scale s1 --scale s3 --scale s6 --episodes 3

& $python scripts/run_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml --family main_comparison `
  --output-root $runRoot --simulation --dry-run @selection

& $python scripts/prepare_m3_pilot.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml --output-root $runRoot `
  --resource-report "$resourceRoot\activation.json" `
  --manifest "$runRoot\m3-pilot-manifest.json"

& $python scripts/run_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml --family main_comparison `
  --output-root $runRoot --simulation --max-jobs 50 @selection

& $python scripts/evaluate_matrix.py --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml --family main_comparison `
  --output-root $runRoot --split validation --simulation --max-jobs 50 @selection

& $python scripts/audit_m3_pilot.py --manifest "$runRoot\m3-pilot-manifest.json" `
  --output-root $runRoot --report "$runRoot\m3-pilot-readiness.json"

& $python scripts/build_m3_pilot_artifacts.py `
  --manifest "$runRoot\m3-pilot-manifest.json" `
  --readiness "$runRoot\m3-pilot-readiness.json" --config-dir configs `
  --protocol configs/experiments/chapter4_5.yaml `
  --output "$runRoot\artifacts"
```

Document that the same filtered training/evaluation commands resume completed
identities, and a single failed job can be selected with one scale, method, and
seed. State that M3 is not reached until the audit returns `m3_ready: true`.

- [ ] **Step 4: Run documentation and focused regression checks**

```powershell
git diff --check
& $python -m pytest tests/experiments/test_orchestrator.py tests/experiments/test_m3_pilot.py tests/experiments/test_m3_artifacts.py tests/e2e/test_chapter45_smoke.py -q
```

Expected: PASS and no whitespace errors.

- [ ] **Step 5: Commit the runbook and end-to-end test**

```powershell
git add tests/e2e/test_chapter45_smoke.py docs/verification/section-4-5-runbook.md
git commit -m "docs: add M3 pilot execution runbook"
```

---

### Task 7: Full Verification, Push, and M3 Execution

**Files:**
- Verify: all tracked source, test, script, configuration, and documentation files.
- Generate only under ignored run roots: `runs/m3-resource-pilot`, `runs/m3-pilot`.

**Interfaces:**
- Consumes: the committed pipeline and current configuration/protocol.
- Produces: pushed implementation, current activation evidence, 50 jobs, 100 validation rows, `m3_ready: true`, and the M3 evidence package.

- [ ] **Step 1: Run the complete repository verification suite**

```powershell
$python = "C:\Users\RZX\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
& $python -m pytest -q
& $python -m compileall -q src scripts tests
git diff --check
```

Expected: all tests PASS, compilation exits zero, and `git diff --check` emits
no output. Diagnose any failure from the complete traceback, add a regression
test, and rerun both focused and full suites.

- [ ] **Step 2: Commit any verification fixes and ensure a clean source tree**

```powershell
git status --short
git log -6 --oneline
```

Expected: no uncommitted tracked or untracked source files. If verification
required a fix, commit the test and fix together with a specific message before
continuing.

- [ ] **Step 3: Push the tested implementation**

```powershell
git push origin feature/problem2-code-framework
git rev-parse HEAD
git rev-parse origin/feature/problem2-code-framework
```

Expected: local and remote commit hashes are identical.

- [ ] **Step 4: Regenerate current resource-activation evidence**

Run the exact resource command from Task 6 with full registered horizons. Then
inspect the report and require:

```text
activated = true
diagnosis = resource_service_chain_activated
config_hash = current config hash
git_commit = pushed HEAD
source_tree_hash = current clean source-tree hash
```

If activation fails, stop at M2, preserve the report, diagnose the state
machine/parameter mechanism, add a regression test for any code defect, and do
not launch the 50 jobs.

- [ ] **Step 5: Freeze and inspect the M3 manifest**

Run the dry-run and preparation commands from Task 6. Verify emitted counts are
exactly 50 jobs and 100 evaluations, all jobs use `simulation`, all update
budgets equal the registered `total_updates`, and no evaluation key contains
`sealed_test`.

- [ ] **Step 6: Run the full M3 training subset with recovery**

Run the 50-job command from Task 6. Keep one GPU worker. If execution is
interrupted, rerun the identical command; completed identities must be reused.
For a failure, obtain the failing `job_id` from the matrix JSON output and
inspect `Join-Path "runs\m3-pilot\jobs" "$jobId.json"`; retain the traceback,
fix only demonstrated defects, rerun tests, commit and push the fix, regenerate
the source-bound manifest, and rerun identities affected by the new source
hash. Never lower the update budget or change hyperparameters silently.

- [ ] **Step 7: Run all 100 shared validation evaluations**

Run the validation command from Task 6. Verify exactly two validation records
per training identity, deterministic reuse on a repeated command, finite
metrics, and no learning-state updates during evaluation.

- [ ] **Step 8: Audit and build the M3 evidence package**

Run the audit and artifact commands from Task 6. Require:

```text
m3_ready = true
highest_maturity = M3
completed_jobs = 50
valid_evaluations = 100
```

Verify every listed artifact exists and the artifact manifest hashes match its
inputs and outputs.

- [ ] **Step 9: Report the achieved maturity without overclaiming**

Report the pushed commit, test count, job/evaluation counts, readiness path,
artifact path, any rerun identities, and the highest passed gate. Use only
"pilot results indicate" wording for scientific interpretation. If any audit
check remains false, report M2 and the exact failed evidence link rather than
claiming M3.
