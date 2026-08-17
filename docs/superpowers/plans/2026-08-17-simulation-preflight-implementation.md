# Controlled Simulation Preflight Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the current problem-2 worktree. Each task must follow red-green-refactor and end with an independent commit.

**Goal:** Replace the field-calibration runtime blocker with a controlled-simulation profile and deterministic technical preflight, then allow full SR-MAPPO experiment jobs to run under an explicit `simulation` execution profile.

**Architecture:** Keep `configs/parameter_registry.yaml`, `configs/field_dynamics.yaml`, scales, scenarios, and algorithm files as authoritative runtime inputs. Add one `configs/simulation_profile.yaml` evidence manifest and a pure preflight module that emits errors versus warnings. Thread the profile through job identities, orchestrator, training, matrix execution, evaluation, and validation freeze without changing SR-MAPPO algorithm semantics or the existing standalone field-readiness audit.

**Tech Stack:** Python 3.11, PyYAML, NumPy, PyTorch, pytest, JSON/JSONL artifacts, PowerShell-compatible CLI paths.

**Spec:** `docs/superpowers/specs/2026-08-17-simulation-preflight-design.md`

## Global Constraints

- Keep the public algorithm name `SR-MAPPO`; do not add HAPPO or `AG-SR-MAPPO`.
- Treat OSM GraphML and its metadata as read-only; require configured SHA-256 identities.
- Real equipment, field, bioassay, and expert calibration gaps are warnings, never simulation errors.
- Preserve train/validation/sealed-test isolation and one-time sealed-test unlock semantics.
- Do not modify Word files or the first-problem repository.
- Use explicit SI units and preserve source values plus scene-scale conversions.
- Every production behavior change must have a failing test observed before implementation.

---

### Task 1: Freeze And Validate The Simulation Profile

**Files:**
- Create: `configs/simulation_profile.yaml`
- Create: `tests/experiments/test_simulation_preflight.py`
- Create: `src/problem2/experiments/simulation_preflight.py`
- Modify: `src/problem2/field/wind_field.py`
- Modify: `src/problem2/field/pest_dynamics.py`
- Modify: `configs/field_dynamics.yaml`
- Modify: `configs/parameter_registry.yaml`
- Test: `tests/unit/test_field_dynamics.py`

**Interfaces:**
- `load_simulation_profile(config_dir: str | Path) -> SimulationProfile`
- `audit_simulation_preflight(config_dir: str | Path, *, resource_report: str | Path | None = None) -> SimulationPreflightReport`
- `SimulationPreflightReport.ready: bool`
- `SimulationPreflightReport.to_dict() -> dict[str, object]`

**Parameter/model review required by this task:**

- Set `vehicle_service_capacity` to `0.8 L`, equal to one UAV's current usable
  scene-scale fill, because the old `5.0 L` value could never bind before UAV
  free capacity. Keep `vehicle_inventory=5.0 L` as the vehicle's total stock.
- Preserve `1.0 L` rated scene capacity, `0.8` usable fraction, `0.01 L/s`
  spray flow, `0.02 L/s` transfer rate, `10 s` preparation, `5 m` rendezvous,
  `1 m/s` UAV/vehicle speed and `1 s` decision interval, but record their
  derived endurance and service times in the profile.
- Record the field model as mechanistic and run numerical CFL/diffusion checks
  using each scale's metric cell size. Do not silently amplify efficacy or
  mortality to force the 85% threshold; emit a treatment-capacity warning when
  the deterministic upper-bound diagnostic shows the endpoint is unreachable.
- Use a mass-conserving closed boundary for pest advection. Keep the existing
  open boundary for pesticide exposure so spray drift can leave the field. A
  pest leaving the grid must not be counted as pesticide control.
- Add explicit rationale, selection rule, sensitivity policy, and reference or
  scene-scale conversion metadata for all 11 engineering records and all
  field-dynamics records.

- [ ] **Step 1: Write failing tests**

  Add tests that load a complete fixture profile and assert: assumption sources
  produce warnings only; a missing rationale produces an error; a runtime value
  mismatch produces an error; unstable wind/diffusion produces an error; an
  inactive resource report produces a warning; a malformed conservation report
  produces an error; and `field_calibrated_ready` is absent from the execution
  decision because simulation preflight has no field-calibration gate.
  Add a field-dynamics test that a pest-only wind update conserves total density
  while the existing pesticide advection test retains open-boundary loss.

- [ ] **Step 2: Run the tests and verify the expected failure**

  Run:

  ```powershell
  pytest -q tests/experiments/test_simulation_preflight.py
  ```

  Expected: collection or assertion failures because the profile and module do
  not exist yet.

- [ ] **Step 3: Add the profile and minimal implementation**

  Implement typed report/issue dataclasses, canonical profile hashing, runtime
  path lookup, finite-range/unit checks, derived regime calculations, road and
  scenario checks, stability checks, optional resource-report classification,
  and the treatment-capacity diagnostic warning. Use `error` and `warning`
  lists rather than a boolean formal gate. Implement
  `WindField.advect(..., boundary="open"|"closed")`; make `PestDynamics`
  call the closed mode and keep `PesticideField` on the open default. Change
  the normalized efficacy/mortality pair only after the analytical
  reachability diagnostic demonstrates that the old pair cannot reach the
  declared endpoint; record the new pair and levels in the profile.

- [ ] **Step 4: Run targeted tests and inspect numerical diagnostics**

  Run:

  ```powershell
  pytest -q tests/experiments/test_simulation_preflight.py
  python scripts/audit_simulation_preflight.py --config-dir configs --report runs/simulation-preflight.json
  ```

  Confirm the report contains the 11 engineering values, field parameters,
  cell sizes, spray endurance, nominal service time, CFL/diffusion numbers and
  explicit warnings. If the treatment-capacity diagnostic shows the old
  efficacy/mortality pair is analytically incapable of reaching 85% even with
  ideal exposure, update that pair using the pre-registered reachability rule
  and rerun the diagnostic; do not choose it from policy outcomes.

- [ ] **Step 5: Commit**

  ```powershell
  git add configs/simulation_profile.yaml src/problem2/experiments/simulation_preflight.py tests/experiments/test_simulation_preflight.py
  git commit -m "feat: add controlled simulation preflight"
  ```

### Task 2: Add The Preflight CLI And Scenario Simulation Readiness

**Files:**
- Create: `scripts/audit_simulation_preflight.py`
- Modify: `src/problem2/scenarios/factory.py`
- Modify: `src/problem2/experiments/evaluation.py`
- Test: `tests/experiments/test_simulation_preflight.py`
- Test: `tests/integration/test_environment_step.py`

**Interfaces:**
- CLI accepts `--config-dir`, optional `--resource-report`, `--report`, and
  `--strict`; it prints one JSON object and returns nonzero only for errors in
  strict mode.
- `ScenarioBundle.assert_simulation_ready() -> None` checks frozen GIS,
  mechanistic dynamics, source metadata hash, and parameter/profile identity.
- `evaluate_policy(..., evidence_mode="simulation")` invokes the simulation
  readiness assertion and never calls `assert_formal_ready()`.

- [ ] **Step 1: Write failing tests**

  Test that the CLI returns zero with assumption warnings, returns nonzero for
  a corrupted road hash, and emits deterministic JSON. Test that a scenario
  with `dynamics_kind=reaction_diffusion_advection_exposure` passes simulation
  readiness while `assert_formal_ready()` would still reject provisional
  parameters.

- [ ] **Step 2: Run targeted tests and observe failure**

  ```powershell
  pytest -q tests/experiments/test_simulation_preflight.py tests/integration/test_environment_step.py
  ```

- [ ] **Step 3: Implement the CLI and scenario/evaluation adapter**

  Keep the old formal assertion available for compatibility, but route only
  simulation evaluation through the new assertion. Include profile hash and
  warning records in evaluation metadata.

- [ ] **Step 4: Run targeted tests**

  ```powershell
  pytest -q tests/experiments/test_simulation_preflight.py tests/integration/test_environment_step.py
  python scripts/audit_simulation_preflight.py --config-dir configs --strict
  ```

- [ ] **Step 5: Commit**

  ```powershell
  git add scripts/audit_simulation_preflight.py src/problem2/scenarios/factory.py src/problem2/experiments/evaluation.py tests/experiments/test_simulation_preflight.py tests/integration/test_environment_step.py
  git commit -m "feat: expose simulation preflight CLI"
  ```

### Task 3: Thread `simulation` Through Job Identities And Matrix Planning

**Files:**
- Modify: `src/problem2/experiments/job_identity.py`
- Modify: `src/problem2/experiments/orchestrator.py`
- Modify: `scripts/run_matrix.py`
- Test: `tests/experiments/test_orchestrator.py`
- Test: `tests/e2e/test_cli_and_recovery.py`

**Interfaces:**
- `make_job_identity(..., execution_profile="simulation")` accepts exactly
  `smoke`, `simulation`, or legacy `formal` only for backward-compatible
  inspection; new full jobs use `simulation`.
- `Chapter45Orchestrator.plan(..., execution_profile="simulation")` uses full
  configured updates and rollout horizon.
- `run_matrix.py --simulation` runs preflight, reports warnings, and passes
  `--simulation` to each child.

- [ ] **Step 1: Write failing tests**

  Assert that simulation and smoke identities differ, simulation planning uses
  the configured `total_updates` and `rollout_horizon`, and matrix dry-run
  reports `evidence_mode=controlled_simulation` with warnings but no rejection.
  Assert that `--simulation --smoke` fails before planning.

- [ ] **Step 2: Run tests and verify failure**

  ```powershell
  pytest -q tests/experiments/test_orchestrator.py tests/e2e/test_cli_and_recovery.py -k "simulation or identity"
  ```

- [ ] **Step 3: Implement profile propagation**

  Add explicit parser flags, select `simulation` for non-smoke full execution,
  invoke the preflight once in the parent process, preserve dirty-source
  rejection for full jobs, and include preflight metadata in matrix JSON.

- [ ] **Step 4: Run targeted tests**

  ```powershell
  pytest -q tests/experiments/test_orchestrator.py tests/e2e/test_cli_and_recovery.py -k "simulation or identity"
  python scripts/run_matrix.py --config-dir configs --family main_comparison --output-root runs/planning --simulation --dry-run
  ```

- [ ] **Step 5: Commit**

  ```powershell
  git add src/problem2/experiments/job_identity.py src/problem2/experiments/orchestrator.py scripts/run_matrix.py tests/experiments/test_orchestrator.py tests/e2e/test_cli_and_recovery.py
  git commit -m "feat: plan simulation execution identities"
  ```

### Task 4: Run Full Simulation Training And Deterministic Evaluation

**Files:**
- Modify: `scripts/train.py`
- Modify: `scripts/evaluate.py`
- Modify: `scripts/evaluate_matrix.py`
- Modify: `src/problem2/experiments/freeze.py`
- Modify: `scripts/freeze_sealed_test.py`
- Tests: `tests/e2e/test_cli_and_recovery.py`, `tests/e2e/test_chapter45_smoke.py`, and freeze tests

**Interfaces:**
- `train.py --simulation` uses full hidden dimension and rollout horizon,
  stores `execution_profile=simulation`, profile hash and warning metadata.
- `evaluate.py --simulation` accepts only simulation checkpoints, calls
  `evaluate_policy(..., evidence_mode="simulation")`, and keeps deterministic
  normalization frozen.
- `freeze_sealed_test.py freeze --simulation` creates a simulation evidence
  freeze and accepts completed simulation jobs, never mixing smoke/formal jobs.

- [ ] **Step 1: Write failing tests**

  Add one short simulation training test with a temporary config reducing
  `total_updates` to 1 while retaining the configured hidden dimension; assert
  the job identity and checkpoint profile. Add tests for simulation evaluation,
  simulation freeze acceptance, smoke/simulation mismatch rejection, and sealed
  test requirements.

- [ ] **Step 2: Run tests and verify failure**

  ```powershell
  pytest -q tests/e2e/test_cli_and_recovery.py tests/e2e/test_chapter45_smoke.py -k "simulation or freeze"
  ```

- [ ] **Step 3: Implement the minimum full-profile path**

  Replace provisional/formal rejection branches only for `simulation`; preserve
  smoke reductions and all source/checkpoint/hash validation. Update freeze
  identity fields to accept the simulation evidence mode.

- [ ] **Step 4: Run targeted end-to-end tests**

  ```powershell
  pytest -q tests/e2e/test_cli_and_recovery.py tests/e2e/test_chapter45_smoke.py -k "simulation or freeze"
  ```

- [ ] **Step 5: Commit**

  ```powershell
  git add scripts/train.py scripts/evaluate.py scripts/evaluate_matrix.py src/problem2/experiments/freeze.py scripts/freeze_sealed_test.py tests/e2e/test_cli_and_recovery.py tests/e2e/test_chapter45_smoke.py
  git commit -m "feat: run and freeze controlled simulation jobs"
  ```

### Task 5: Update Runbooks And Perform The Parameter/Model Review

**Files:**
- Modify: `README.md`
- Modify: `docs/verification/complete-project-runbook.md`
- Modify: `docs/verification/section-4-5-runbook.md`
- Modify: `configs/parameter_registry.yaml`
- Modify: `configs/field_dynamics.yaml`
- Modify: `configs/environment.yaml`
- Modify: `configs/algorithms/sr_mappo.yaml` only when a tested stability or scale issue is demonstrated
- Test: `tests/unit/test_config.py`, `tests/experiments/test_parameter_audit.py`

**Parameter/model acceptance decisions:**

- Keep the 85% threshold as the declared research outcome, not as a target to
  force through coefficients.
- Keep `reaction_diffusion_advection_exposure`, but report treatment-capacity
  diagnostics and require sensitivity/diagnostic evidence before interpreting
  85% success.
- Keep one vehicle, six scales, shared scenarios, role-separated SR-MAPPO
  actors, centralized critic, and all five stability groups.
- Modify a numerical or ecological parameter only with a failing test or
  deterministic diagnostic that establishes the defect; record the reason and
  sensitivity range in the profile.

- [ ] **Step 1: Write failing documentation/config consistency tests**

  Assert that the service-capacity value equals the usable UAV capacity, every
  profile runtime path resolves, the configured `decision_dt` matches the
  scales file, `vehicle_speed * dt` and `uav_speed * dt` are metric quantities,
  and SR-MAPPO stability flags are all present.

- [ ] **Step 2: Run tests and inspect failures**

  ```powershell
  pytest -q tests/unit/test_config.py tests/experiments/test_parameter_audit.py
  ```

- [ ] **Step 3: Apply only justified configuration/documentation changes**

  Update stale comments that call the mechanistic scenario “smoke only”, add
  the explicit simulation claim boundary and service-capacity rationale, and
  preserve all public source metadata.

- [ ] **Step 4: Run full regression and static checks**

  ```powershell
  pytest -q
  python -m compileall -q src scripts
  git diff --check
  ```

- [ ] **Step 5: Commit**

  ```powershell
  git add README.md docs/verification/complete-project-runbook.md docs/verification/section-4-5-runbook.md configs/parameter_registry.yaml configs/field_dynamics.yaml configs/environment.yaml configs/algorithms/sr_mappo.yaml tests/unit/test_config.py tests/experiments/test_parameter_audit.py
  git commit -m "docs: document controlled simulation execution and parameter review"
  ```

## Final Verification And Handoff

After all task commits, run:

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
git status --short --branch
python scripts/audit_simulation_preflight.py --config-dir configs --report runs/simulation-preflight.json --strict
python scripts/run_matrix.py --config-dir configs --protocol configs/experiments/chapter4_5.yaml --family main_comparison --output-root runs/planning --simulation --dry-run
```

The expected endpoint is a clean worktree, a passing technical preflight with
possible explicit warnings, and a 150-job simulation dry-run. This is readiness
for pilot execution, not evidence that SR-MAPPO outperforms the baselines.
