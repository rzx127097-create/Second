# Complete Problem 2 Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing tested domain and SR-MAPPO modules into a runnable, traceable second-problem project covering environment interaction, training, evaluation, fair baselines, experiment recovery and artifact generation.

**Architecture:** Keep deterministic physical simulation independent from learning. A single episode adapter will expose role observations, structured critic state, masks, rewards and event-complete logs; a runner will collect the adapter output into `RolloutBatch` and update SR-MAPPO; evaluation and baselines will consume the same scenario interface; matrix jobs will persist immutable identities and checkpoints; artifact builders will consume only validated long-format logs. Provisional engineering values remain explicitly labelled and cannot be described as formal evidence.

**Tech Stack:** Python 3.11, NumPy, PyYAML, PyTorch CPU/GPU optional, pytest, pandas and matplotlib for artifact generation.

**Spec:** `docs/design/section-4.1-design-contract.md`, `docs/design/section-4.2-design-contract.md`, `docs/plans/2026-08-14-section-4-4-sr-mappo.md`, and `C:\Users\RZX\.codex\skills\sr-mappo-problem2\references\experiment-and-statistics-protocol.md`.

## Global Constraints

- Keep the flagship algorithm name `SR-MAPPO`; do not add HAPPO or rename the method.
- The primary resource is pesticide-only replenishment; battery exchange is outside scope.
- Use one replenishment vehicle in the primary experiment while preserving multi-vehicle slots in interfaces.
- OSM and synthetic roads are simulation inputs, never deployment evidence.
- Do not modify any Word document.
- Do not invent or freeze engineering parameters; provisional configuration is allowed for smoke tests only.
- Keep train, validation and sealed-test scenario identities separate.
- Every raw result records config hash, Git commit, method, scale, seed, split and scenario.
- Any failed job preserves its error and can be retried by identity without rerunning successful jobs.
- Every task below follows failing test -> implementation -> focused test -> full regression -> independent commit.

## File Map

- `src/problem2/scenarios/`: deterministic synthetic scenario construction and scale-specific environment factories.
- `src/problem2/experiments/rollout_runner.py`: environment-to-rollout collection and policy update loop.
- `src/problem2/experiments/metrics.py`: episode metrics and event log normalization.
- `src/problem2/experiments/runner.py`: persisted train/evaluate job execution and recovery.
- `src/problem2/experiments/evaluation.py`: shared-scenario deterministic evaluation.
- `src/problem2/baselines/`: existing policy adapters extended to common episode interface.
- `scripts/train.py`, `scripts/evaluate.py`, `scripts/run_matrix.py`: real CLI entry points.
- `src/problem2/artifacts/`: validated summaries and plots consumed by CLI.
- `tests/e2e/`: end-to-end CPU smoke tests for training, resume, evaluation and matrix dry-run.

### Task 1: Scenario factory and unified decision adapter

**Files:**
- Create: `src/problem2/scenarios/factory.py`
- Create: `src/problem2/scenarios/__init__.py`
- Modify: `src/problem2/section4_2/adapter.py`
- Test: `tests/e2e/test_scenario_factory.py`

**Interfaces:**
- `build_synthetic_scenario(scale_id: str, seed: int, *, config_dir: str | Path) -> ScenarioBundle`.
- `ScenarioBundle.reset() -> DecisionSnapshot` and `ScenarioBundle.step(actions: Mapping[str, str]) -> StepSnapshot`.
- `DecisionSnapshot` exposes `role_observations`, `critic_state`, `action_masks`, `candidate_mapping`, `episode_id`, `step` and `normalization_version`.

- [ ] Write a failing test that builds `s1`, resets twice with the same seed, checks identical positions/density/resource totals, and completes at least one legal step.
- [ ] Run `pytest tests/e2e/test_scenario_factory.py -q` and observe the missing factory failure.
- [ ] Implement deterministic provisional scenario creation from `configs/scales.yaml`, a rectangular pest field, one road graph, fixed role slots, observation builders, masks and reward component extraction.
- [ ] Run the focused test and assert pesticide conservation and event ordering.
- [ ] Commit `feat: add unified problem2 scenario factory`.

### Task 2: Real rollout collection and SR-MAPPO training runner

**Files:**
- Create: `src/problem2/experiments/rollout_runner.py`
- Create: `src/problem2/experiments/metrics.py`
- Modify: `src/problem2/algorithms/sr_mappo/algorithm.py`
- Modify: `src/problem2/algorithms/sr_mappo/rollout.py`
- Test: `tests/e2e/test_training_smoke.py`

**Interfaces:**
- `run_training_episode(bundle, algorithm, trainer, *, horizon: int, episode_id: str) -> EpisodeRecord`.
- `train_policy(bundle_factory, algorithm, trainer, *, updates: int, rollout_horizon: int, checkpoint_path: Path | None, start_update: int = 0) -> list[EpisodeRecord]`.
- `EpisodeRecord.to_row() -> dict[str, object]` with reduction rate, success, reward components, waits, disabled time, vehicle distance and pesticide totals.

- [ ] Write a failing CPU smoke test that trains one update on `s1` with two UAVs, saves a checkpoint, reloads it and continues one update.
- [ ] Run the focused test and observe that no episode runner exists.
- [ ] Implement policy input extraction from `ScenarioBundle`, action conversion from numeric role actions to environment slot actions, `RolloutBatch` writes, team value estimation, GAE, PPO epochs, metrics and atomic checkpoint calls.
- [ ] Run the smoke test with PyTorch CPU and verify finite losses, non-empty event logs and unchanged checkpoint metadata after resume.
- [ ] Commit `feat: add end-to-end SR-MAPPO rollout runner`.

### Task 3: Deterministic evaluation and common policy protocol

**Files:**
- Modify: `src/problem2/experiments/evaluation.py`
- Modify: `src/problem2/experiments/runner.py`
- Create: `src/problem2/experiments/policy_protocol.py`
- Test: `tests/e2e/test_evaluation_smoke.py`

**Interfaces:**
- `evaluate_policy(policy, scenario_factory, *, scenarios: Sequence[str], split: str, deterministic: bool) -> list[EpisodeRecord]`.
- `PolicyProtocol.act(snapshot) -> Mapping[str, str]` and `PolicyProtocol.name -> str`.

- [ ] Write a failing test that evaluates a deterministic hold policy twice on the same validation scenario and compares every metric row.
- [ ] Implement shared snapshot/action conversion, frozen normalization evaluation, exact scenario IDs and evaluation rows without optimizer updates.
- [ ] Add evaluation checkpoint loading and integrity validation.
- [ ] Run focused and full tests.
- [ ] Commit `feat: add shared deterministic evaluation protocol`.

### Task 4: Fair baseline adapters

**Files:**
- Modify: `src/problem2/baselines/fixed_support.py`
- Modify: `src/problem2/baselines/priority_dispatch.py`
- Modify: `src/problem2/baselines/rolling_astar.py`
- Create: `src/problem2/baselines/policies.py`
- Test: `tests/e2e/test_baseline_protocol.py`

**Interfaces:**
- Each baseline implements `PolicyProtocol` and consumes the same `DecisionSnapshot` without changing physical constraints.
- `make_policy(method: str, checkpoint: Path | None = None) -> PolicyProtocol`.

- [ ] Write a failing test that runs all five registered methods for one episode and checks identical scenario/horizon/resource metadata.
- [ ] Implement policy adapters for mobile SR-MAPPO, stationary support, rolling A*, same-source MAPPO stability ablation and two-stage initialization; keep planner decisions separate from road execution.
- [ ] Run focused and full tests; reject unknown methods and future-information shortcuts unless explicitly labelled oracle.
- [ ] Commit `feat: expose fair common baseline protocol`.

### Task 5: Persisted jobs, real CLI and recovery

**Files:**
- Modify: `src/problem2/experiments/job_identity.py`
- Modify: `src/problem2/experiments/runner.py`
- Modify: `src/problem2/experiments/recovery.py`
- Modify: `scripts/train.py`
- Modify: `scripts/evaluate.py`
- Modify: `scripts/run_matrix.py`
- Test: `tests/e2e/test_cli_and_recovery.py`

**Interfaces:**
- `python scripts/train.py --config-dir configs --scale s1 --seed 0 --updates 1 --output-root artifacts/runs`.
- `python scripts/evaluate.py --config-dir configs --checkpoint <path> --split validation --scenario val_001`.
- `python scripts/run_matrix.py --config-dir configs --output-root artifacts/runs --dry-run`.
- Job files contain `job_id`, config hash, Git commit, status, attempts, checkpoint path and error.

- [ ] Write failing CLI tests for train, evaluate and matrix dry-run, plus a failed worker that resumes only the failed job.
- [ ] Implement argument parsing, configuration identity, Git commit capture, atomic job records, retry limits, checkpoint existence checks and split isolation.
- [ ] Keep formal execution blocked when parameter status is provisional, while allowing explicit `--smoke` mode.
- [ ] Run subprocess smoke commands and assert machine-readable JSON output.
- [ ] Commit `feat: add runnable training evaluation and matrix CLIs`.

### Task 6: Artifact and evidence pipeline

**Files:**
- Modify: `src/problem2/artifacts/validate_logs.py`
- Modify: `src/problem2/artifacts/summarize.py`
- Modify: `src/problem2/artifacts/figures.py`
- Modify: `src/problem2/artifacts/tables.py`
- Modify: `src/problem2/artifacts/evidence_manifest.py`
- Modify: `scripts/build_artifacts.py`
- Test: `tests/e2e/test_artifact_pipeline.py`

**Interfaces:**
- `build_artifacts(input_jsonl: Path, output_root: Path, *, manifest: Path) -> ArtifactBundle`.
- Output includes validated CSV, summary JSON, three-line-table TSV/Markdown, SVG/PNG figure and evidence manifest.

- [ ] Write a failing test from two episode rows that expects a validated table, summary and figure manifest.
- [ ] Implement schema validation, paired scenario/seed aggregation, finite-value checks, confidence interval fields without overstating significance, Nature-style matplotlib output and source trace manifest.
- [ ] Run the pipeline on smoke logs and verify every output path exists and points to the input Git/config identity.
- [ ] Commit `feat: complete traceable artifact pipeline`.

### Task 7: Full project verification and documentation

**Files:**
- Modify: `README.md`
- Create: `docs/verification/complete-project-runbook.md`
- Create: `tests/e2e/test_complete_project.py`

- [ ] Write a final test that runs the smallest smoke matrix, resumes one checkpoint, evaluates one validation scene and builds artifacts.
- [ ] Run `pytest -q`, `python -m compileall -q src scripts`, `git diff --check`, all CLI smoke commands and the final test.
- [ ] Document exact commands, provisional-parameter boundary, output schema, recovery behavior and claims that are not permitted before M3/M4.
- [ ] Commit `docs: document complete problem2 project runbook`.
- [ ] Request final read-only code review, fix Critical/Important issues, rerun all verification and push the branch.

## Delivery Gates

- M2 complete project code: all Tasks 1-7 pass tests and CPU smoke commands.
- M3 pilot remains pending until engineering parameter evidence and independent validation scenarios are frozen.
- M4 formal evidence remains pending until the full matrix, sealed test and artifact manifests are produced.
