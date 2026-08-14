# Section 4.5 Experiment System Implementation Plan

> **For agentic workers:** Execute inline with the test-driven-development and systematic-debugging workflows. Every behavior change follows failing test -> implementation -> focused test -> full regression -> independent commit.

**Goal:** Complete the Chapter 4.5 code path so all five main methods, mechanism diagnostics, sensitivity/adaptation studies, ablations, shared-scenario evaluation, paired statistics and traceable figures/tables can be executed from one frozen protocol.

**Architecture:** Keep the physical environment as the single transition authority. Method profiles may change only the declared role controller, SR-MAPPO stability flags or staged-training schedule; experiment interventions are immutable scenario overrides layered over the same configuration and scenario registry. A persisted orchestrator expands a frozen protocol into training/evaluation jobs, resumes by immutable identity, and feeds validated long-format rows into hierarchical paired statistics and a single artifact manifest.

**Tech Stack:** Python 3.11, dataclasses, NumPy, PyYAML, PyTorch, pytest, matplotlib and the existing problem2 package.

**Spec:** `docs/design/section-4.2-design-contract.md`, `docs/thesis/chapter4-outline.md`, `docs/verification/complete-project-runbook.md`, and the six `sr-mappo-problem2` reference contracts.

## Global Constraints

- Keep the public algorithm name `SR-MAPPO`; do not add HAPPO or `AG-SR-MAPPO`.
- Keep pesticide replenishment as the primary resource and one vehicle in the main experiment.
- Do not mark provisional engineering parameters or scenarios as verified.
- All five main methods share physical dynamics, resource totals, scenario IDs, horizons and evaluation budgets.
- Fixed support freezes the vehicle at a declared road node; rolling A* controls only the vehicle role; MAPPO differs only through the registered SR stability switches; two-stage training has an explicit stage boundary.
- Training, validation and sealed-test scenario identities remain disjoint; sealed test stays blocked until every formal gate is verified.
- Diagnostic upper bounds are labelled diagnostics and never ranked as ordinary algorithms.
- No Word document is modified by this plan.

---

### Task 1: Freeze the executable Chapter 4.5 protocol and portable process boundary

**Files:**
- Create: `configs/experiments/chapter4_5.yaml`
- Create: `src/problem2/experiments/specification.py`
- Modify: `src/problem2/config.py`
- Modify: `scripts/run_matrix.py`
- Test: `tests/experiments/test_experiment_specification.py`
- Test: `tests/e2e/test_cli_and_recovery.py`

**Interfaces:**
- `load_experiment_spec(path: Path, config: ConfigBundle) -> Chapter45Spec`
- `Chapter45Spec.expand(family: str) -> tuple[ExperimentCondition, ...]`
- `run_utf8_json_child(command: Sequence[str], *, cwd: Path) -> dict[str, object]`

**Acceptance tests:** reject duplicate condition IDs, unknown methods/scales/parameters, train-test overlap, invalid sensitivity levels and any diagnostic listed as a main method. Reproduce a Windows child-process JSON path containing Chinese characters and verify strict UTF-8 decoding succeeds because the child environment is explicitly UTF-8.

### Task 2: Implement method profiles for the five fair main comparisons

**Files:**
- Create: `src/problem2/experiments/methods.py`
- Modify: `src/problem2/experiments/rollout_runner.py`
- Modify: `src/problem2/algorithms/sr_mappo/trainer.py`
- Modify: `scripts/train.py`
- Modify: `src/problem2/baselines/policies.py`
- Test: `tests/experiments/test_method_profiles.py`
- Test: `tests/e2e/test_training_methods.py`

**Interfaces:**
- `method_profile(name: str, algorithm_config: Mapping[str, object]) -> MethodProfile`
- `RoleActionOverride.actions(snapshot, transition) -> Mapping[str, int]`
- `train_policy(..., method_profile: MethodProfile) -> list[EpisodeRecord]`

**Acceptance tests:** SR-MAPPO mobile samples both actors; fixed support and rolling A* replace only vehicle actions and mark vehicle policy samples invalid; MAPPO disables exactly the registered stability components without changing optimizer/network/environment budgets; two-stage training uses A* vehicle control before the frozen boundary and joint learning afterward. Stored actions and old log probabilities must describe the behavior actually executed.

### Task 3: Add immutable environment interventions for mechanism, sensitivity, adaptation and ablation families

**Files:**
- Create: `src/problem2/scenarios/interventions.py`
- Modify: `src/problem2/scenarios/factory.py`
- Modify: `src/problem2/section4_2/adapter.py`
- Test: `tests/experiments/test_scenario_interventions.py`

**Interfaces:**
- `ScenarioIntervention` carries one condition ID plus typed parameter, support and road changes.
- `build_synthetic_scenario(..., intervention: ScenarioIntervention | None = None) -> ScenarioBundle`

**Acceptance tests:** unlimited pesticide and teleport remain diagnostic modes; no-support, matched-fixed, rolling-A* and mobile modes retain declared total-resource rules; capacity, speed, setup time and rendezvous radius overrides preserve units/ranges; hotspot-road separation, demand dispersion, simultaneous requests and local road blockage are deterministic from the scenario seed. Every intervention is recorded in episode metadata and configuration identity.

### Task 4: Complete persisted training/evaluation orchestration

**Files:**
- Create: `src/problem2/experiments/orchestrator.py`
- Modify: `src/problem2/experiments/job_identity.py`
- Modify: `src/problem2/experiments/runner.py`
- Modify: `scripts/run_matrix.py`
- Modify: `scripts/evaluate.py`
- Test: `tests/experiments/test_orchestrator.py`
- Test: `tests/e2e/test_chapter45_smoke.py`

**Interfaces:**
- Job identity adds `family`, `condition_id`, `scenario_split` and protocol hash.
- `Chapter45Orchestrator.plan(family) -> tuple[PlannedJob, ...]`
- `Chapter45Orchestrator.run(..., smoke: bool, max_jobs: int | None) -> MatrixReport`

**Acceptance tests:** all five main methods have real workers; successful jobs are never rerun; failed identities retain full tracebacks and may be retried alone; checkpoint/config/protocol hashes are validated; dry-run has no writes; GPU device and worker count are explicit; provisional configuration allows smoke only; formal and sealed-test execution fail closed.

### Task 5: Expand event-derived metrics and resource-activation diagnostics

**Files:**
- Modify: `src/problem2/experiments/metrics.py`
- Modify: `src/problem2/artifacts/validate_logs.py`
- Modify: `scripts/audit_resource_activation.py`
- Test: `tests/experiments/test_metrics_and_activation.py`

**Interfaces:**
- Episode rows include request count/completion, mean and upper-tail wait, disabled/effective spray/service/vehicle-idle time, rendezvous distance, actual transfer, final inventory, inventory utilization, decision runtime and termination reason.
- `audit_resource_activation(records) -> ResourceActivationReport` distinguishes total shortage from spatial-temporal mismatch.

**Acceptance tests:** all metrics derive only from state/event ledgers, retain units, reject missing/negative/non-finite values and conserve pesticide. The audit never declares an activated mechanism when requests or disabled time are absent.

### Task 6: Implement seed/scenario paired inference and multiplicity control

**Files:**
- Modify: `src/problem2/artifacts/summarize.py`
- Create: `src/problem2/artifacts/statistics.py`
- Test: `tests/experiments/test_statistics.py`

**Interfaces:**
- `hierarchical_paired_bootstrap(records, reference, metric, draws, seed) -> list[PairedEstimate]`
- `holm_adjust(p_values: Sequence[float]) -> list[float]`
- Summaries first aggregate shared scenarios within training seed, then infer across training seeds.

**Acceptance tests:** preserve pairing by scale/seed/scenario, reject incomplete confirmatory pairs, return deterministic percentile intervals/effect sizes, handle success probability separately, and label exploratory comparisons. Scenarios from one trained policy are never counted as independent training seeds.

### Task 7: Generate the complete traceable Chapter 4.5 artifact package

**Files:**
- Modify: `src/problem2/artifacts/figures.py`
- Modify: `src/problem2/artifacts/tables.py`
- Modify: `src/problem2/artifacts/evidence_manifest.py`
- Modify: `scripts/build_artifacts.py`
- Create: `scripts/build_chapter45_artifacts.py`
- Test: `tests/experiments/test_chapter45_artifacts.py`

**Interfaces:**
- One locked summary produces main comparison, mechanism chain, sensitivity/adaptation and ablation figures in SVG/PDF/PNG plus three-line-table TSV/Markdown.
- The manifest records exact input/output hashes, protocol/config/Git identity, metric definitions, uncertainty method, scenario selection rule and provisional/formal maturity.

**Acceptance tests:** figures use a white background, Arial-compatible fonts and color-blind-safe colors; no manual table values; trajectory/timeline examples require pre-registered scenario IDs; mixed provenance or stale hashes are rejected.

### Task 8: Full verification, documentation, commits and GitHub delivery

**Files:**
- Modify: `README.md`
- Modify: `docs/verification/complete-project-runbook.md`
- Create: `docs/verification/section-4-5-runbook.md`
- Test: `tests/e2e/test_complete_project.py`

**Verification:**
- `pytest -q`
- `python -m compileall -q src scripts`
- `git diff --check`
- protocol dry-run for every experiment family
- one five-method CPU smoke matrix
- deterministic shared validation smoke
- resource-activation audit and Chapter 4.5 artifact build

The final report states the highest passed maturity gate, the exact commit/push status, any remaining parameter/literature/OSM evidence blockers, and the claims currently permitted.
