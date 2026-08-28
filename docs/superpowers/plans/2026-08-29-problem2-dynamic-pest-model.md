# Problem-2 Dynamic Pest Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the local static pest-decrease adapter with a self-contained, deterministic Problem-1-lineage Holling-Tanner dynamic ecology and make that ecology mandatory for every future primary Problem-2 experiment.

**Architecture:** A new `problem2.ecology` package owns immutable parameters, pure numerical operators, pesticide-effect and wind state, deterministic scenario generation, and complete ecology snapshots. `DynamicPestEnvironment` wraps the existing physical environment, consumes only accepted positive physical spray events, advances ecology in the approved order, then rebuilds unchanged-size role observations and critic state. A fail-closed experiment policy separates historical G5 artifacts from the new `dynamic_pest_v1` namespace and rejects static primary or sealed execution.

**Tech Stack:** Python 3.11, NumPy, PyYAML, PyTorch checkpoint serialization, pytest, existing Problem-2 environment and experiment APIs.

**Spec:** `docs/superpowers/specs/2026-08-28-problem2-dynamic-pest-model-design.md`

## Global Constraints

- Public algorithm name remains `SR-MAPPO`; describe Problem 2 as its air-ground heterogeneous extension.
- Do not introduce HAPPO or rename the method to `AG-SR-MAPPO`.
- Pesticide is the only replenished resource; battery replenishment remains inactive.
- The protected Problem-1 repository is read-only and is never a runtime dependency.
- Adopt only committed Problem-1 snapshot `1ca9e5ccc5f77ed775cd2b607dd70d635720accf` and the four source blobs recorded in the approved spec.
- OSM is simulation input, not real-deployment evidence.
- Existing `outputs/problem2_sr_mappo_v1/g5` bytes remain historical and are never overwritten or relabeled.
- New dynamic evidence is rooted at `outputs/problem2_sr_mappo_v1/dynamic_pest_v1`.
- Dynamic ecology is mandatory for primary, formal, and sealed runs; static ecology is allowed only as an explicitly labeled development diagnostic.
- Observation dimensions remain `43 + 68N` for each UAV, `28` for the vehicle, and `45 + 70N` for the critic.
- Reward is signed normalized one-step prey change; endpoint reduction may be negative.
- Highest maturity after code and unit/integration verification is M2. G6 formal execution and G7 sealed access remain blocked.
- Follow red-green-refactor for every production behavior and record each important phase's verification, commit, push, and remote hash in `docs/PROJECT_STATE.md`.

## File Map

- `configs/problem2/dynamic_pest_v1.yaml`: versioned normalized ecology parameter contract.
- `docs/evidence/dynamic_pest_v1/source_lineage.yaml`: protected Problem-1 commit/blob lineage and claim boundary.
- `docs/evidence/dynamic_pest_v1/raw_episode_schema.yaml`: direct dynamic-ecology episode fields.
- `docs/evidence/dynamic_pest_v1/heterogeneous_interface.yaml`: fixed dimensions and exact ecology slot semantics.
- `src/problem2/ecology/config.py`: immutable validated config loading and canonical contract hash.
- `src/problem2/ecology/dynamics.py`: reflected Laplacian, upwind advection, reaction terms, and substep integration.
- `src/problem2/ecology/pesticide.py`: radial effect deposition, mortality, duration, decay, and state round trip.
- `src/problem2/ecology/scenario.py`: scenario-owned wind RNG, Gaussian prey/predator initialization, and canonical identity.
- `src/problem2/ecology/system.py`: complete ecology transition ordering, summaries, local context, snapshots, and restoration.
- `src/problem2/training/dynamic_env.py`: physical-to-ecological adapter and signed team reward.
- `src/problem2/experiments/ecology_policy.py`: dynamic defaults, static diagnostic restrictions, output-root confinement, and provenance guards.
- Existing environment, training, validation, checkpoint, CLI, and audit modules are modified only where the new contract crosses their boundary.

---

### Task 1: Freeze The Versioned Ecology And Lineage Contracts

**Files:**
- Create: `configs/problem2/dynamic_pest_v1.yaml`
- Create: `docs/evidence/dynamic_pest_v1/source_lineage.yaml`
- Create: `src/problem2/ecology/__init__.py`
- Create: `src/problem2/ecology/config.py`
- Create: `tests/ecology/test_config_and_lineage.py`

**Interfaces:**
- Produces: `DYNAMIC_ECOLOGY_VERSION = "problem2-dynamic-pest-v1"`.
- Produces: `DynamicEcologyConfig.from_yaml(path: Path) -> DynamicEcologyConfig`.
- Produces: `DynamicEcologyConfig.canonical_payload() -> dict[str, object]` and `contract_sha256`.
- Produces: `verify_problem1_lineage(path: Path, *, resolve_git: bool = True) -> dict[str, str]`.
- Consumes later: every scenario, checkpoint, run row, and experiment guard stores `contract_sha256` and `DYNAMIC_ECOLOGY_VERSION`.

- [ ] **Step 1: Write failing contract and lineage tests**

```python
def test_dynamic_contract_loads_exact_approved_values() -> None:
    cfg = DynamicEcologyConfig.from_yaml(ROOT / "configs/problem2/dynamic_pest_v1.yaml")
    assert cfg.version == "problem2-dynamic-pest-v1"
    assert (cfg.beta, cfg.m, cfg.s, cfg.d1, cfg.d2) == (1.5, 2.0, 0.25, 0.3, 0.3)
    assert (cfg.integration_interval, cfg.substeps) == (0.005, 3)
    assert (cfg.effect_amount, cfg.effect_duration, cfg.decay_rate, cfg.spray_radius) == (0.85, 15, 0.92, 4)
    assert cfg.predator_sensitivity == 0.1
    assert cfg.wind_strength_range == (0.0, 0.5)
    assert len(cfg.contract_sha256) == 64


def test_lineage_resolves_only_the_approved_commit_and_blobs() -> None:
    resolved = verify_problem1_lineage(
        ROOT / "docs/evidence/dynamic_pest_v1/source_lineage.yaml"
    )
    assert resolved["source_commit"] == "1ca9e5ccc5f77ed775cd2b607dd70d635720accf"
    assert resolved["runtime_import_allowed"] == "false"
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/ecology/test_config_and_lineage.py -q`

Expected: collection fails because `problem2.ecology.config` does not exist.

- [ ] **Step 3: Add the exact frozen YAML records and minimal strict loader**

The config must declare every approved value, `assumption_status: provisional_normalized_simulation`, `dynamic_wind: true`, `replenished_resource: pesticide`, and `battery_replenishment_enabled: false`. The loader rejects unknown/missing keys, booleans where numbers are required, non-finite values, invalid bounds, non-positive `substeps`, and any identity drift. Hash canonical JSON encoded as UTF-8 with `sort_keys=True`, `separators=(",", ":")`, and `allow_nan=False`.

The lineage YAML must record the four approved paths/blob IDs from the spec, `read_only: true`, and all runtime/checkpoint/output import flags as false. `resolve_git=True` verifies `git rev-parse` and `git ls-tree`; `False` validates the registry structure without requiring the external repository.

- [ ] **Step 4: Run focused tests and contract drift mutations**

Run: `python -m pytest tests/ecology/test_config_and_lineage.py -q`

Expected: all tests pass, including parameter deletion, unknown-key, invalid-range, source-commit, blob, and runtime-import mutation cases.

- [ ] **Step 5: Check formatting and commit the contract phase**

Run: `git diff --check`

Commit: `git add configs/problem2/dynamic_pest_v1.yaml docs/evidence/dynamic_pest_v1/source_lineage.yaml src/problem2/ecology/__init__.py src/problem2/ecology/config.py tests/ecology/test_config_and_lineage.py && git commit -m "feat: freeze dynamic pest ecology contract"`

---

### Task 2: Implement Independently Verifiable Holling-Tanner Numerics

**Files:**
- Create: `src/problem2/ecology/dynamics.py`
- Create: `tests/ecology/test_dynamics.py`

**Interfaces:**
- Consumes: `DynamicEcologyConfig`.
- Produces: `validate_density_pair(prey, predator) -> tuple[np.ndarray, np.ndarray]`.
- Produces: `reflected_laplacian(field: np.ndarray, dx: float) -> np.ndarray`.
- Produces: `upwind_advection(field: np.ndarray, wind: tuple[float, float], dx: float) -> np.ndarray`.
- Produces: `reaction_terms(prey, predator, config) -> tuple[np.ndarray, np.ndarray]`.
- Produces: `holling_tanner_substep(prey, predator, wind, config) -> tuple[np.ndarray, np.ndarray]`.
- Produces: `advance_holling_tanner(prey, predator, wind, config) -> tuple[np.ndarray, np.ndarray]` using exactly `config.substeps` with `dt=config.integration_interval/config.substeps`.

- [ ] **Step 1: Write hand-computable Laplacian and signed-upwind tests**

```python
def test_reflected_laplacian_matches_hand_computed_corner_and_center() -> None:
    field = np.array([[1.0, 2.0, 4.0], [3.0, 5.0, 8.0], [6.0, 9.0, 10.0]])
    observed = reflected_laplacian(field, dx=1.0)
    assert observed[0, 0] == pytest.approx(6.0)
    assert observed[1, 1] == pytest.approx(-1.0)


@pytest.mark.parametrize(
    ("wind", "expected"),
    [((2.0, 0.0), np.array([[2.0, -2.0, -4.0]])),
     ((-2.0, 0.0), np.array([[-2.0, -4.0, 4.0]]))],
)
def test_upwind_advection_uses_wind_sign(wind, expected) -> None:
    field = np.array([[1.0, 2.0, 4.0]])
    assert np.allclose(upwind_advection(field, wind, 1.0), expected)
```

The test expectations are computed from reflected padding and the Problem-1 one-sided formulas, not from production helpers.

- [ ] **Step 2: Run numerical operator tests and verify RED**

Run: `python -m pytest tests/ecology/test_dynamics.py -q`

Expected: import fails because `problem2.ecology.dynamics` is missing.

- [ ] **Step 3: Implement reflected padding and upwind operators**

Use `np.pad(field, 1, mode="reflect")`; return `-(wx * du_dx + wy * du_dy)`. Validate finite two-dimensional non-empty arrays and positive finite `dx` before calculation.

- [ ] **Step 4: Write independent reaction, one-substep, and three-substep gold tests**

The test module must contain a small explicit loop named `_independent_reference_advance` that repeats the equations from the spec with NumPy indexing and never imports or calls any production dynamics function. Assert one-substep and three-substep output with `rtol=0`, `atol=1e-12`, including prey-below-`1e-6` predator fallback, reaction clipping, advection multipliers `0.05/0.01`, and output clips `[0, 1/beta]` and `[0, 2/beta]`.

- [ ] **Step 5: Run gold tests and verify RED**

Run: `python -m pytest tests/ecology/test_dynamics.py -q`

Expected: operator tests pass and reaction/integration tests fail because the functions are absent.

- [ ] **Step 6: Implement the minimal reaction and integration functions**

Use prey predation denominator `prey + 1.0 + 1e-10`, predator denominator `max(prey, 1e-8)`, fallback `-0.1 * predator`, reaction clip `[-0.5, 0.5]`, and simultaneous state updates from the same prior substep.

- [ ] **Step 7: Run focused and property tests**

Run: `python -m pytest tests/ecology/test_dynamics.py -q`

Expected: all tests pass, including shape mismatch, NaN/Inf, negative density, one-cell-axis rejection for reflected padding, and input arrays remaining byte-identical.

- [ ] **Step 8: Commit the numerical kernel**

Commit: `git add src/problem2/ecology/dynamics.py tests/ecology/test_dynamics.py && git commit -m "feat: add Holling-Tanner numerical kernel"`

---

### Task 3: Implement Persistent Pesticide Effect And Dynamic Wind

**Files:**
- Create: `src/problem2/ecology/pesticide.py`
- Create: `tests/ecology/test_pesticide.py`
- Create: `tests/ecology/test_wind.py`
- Modify: `src/problem2/ecology/scenario.py` (created in this task with wind types; scenario generation is completed in Task 4)

**Interfaces:**
- Consumes: `DynamicEcologyConfig`.
- Produces: `AcceptedSpray(row: int, col: int, delta_l: float)`.
- Produces: `PesticideEffectField.empty(shape, config)`, `deposit(spray, reference_volume_l)`, `apply_mortality(prey, predator)`, `decay()`, `state_dict()`, and `from_state_dict()`.
- Produces: immutable `WindState(direction: float, strength: float, step_count: int)` with `vector`.
- Produces: `DynamicWind(rng: np.random.Generator, state: WindState, config)`, `update()`, `state_dict()`, and `from_state_dict()`.

- [ ] **Step 1: Write failing radial deposition and physical-volume scaling tests**

```python
def test_one_full_accepted_spray_deposits_the_approved_radial_profile() -> None:
    field = PesticideEffectField.empty((11, 11), CONFIG)
    field.deposit(AcceptedSpray(5, 5, 0.25), reference_volume_l=0.25)
    assert field.concentration[5, 5] == pytest.approx(0.85)
    assert field.concentration[5, 9] == pytest.approx(0.17)
    assert field.concentration[5, 10] == 0.0
    assert field.duration[5, 5] == 15
    assert field.spray_count[5, 5] == 1


def test_partial_spray_receives_only_proportional_effect() -> None:
    field = PesticideEffectField.empty((3, 3), CONFIG)
    field.deposit(AcceptedSpray(1, 1, 0.125), reference_volume_l=0.25)
    assert field.concentration[1, 1] == pytest.approx(0.425)
```

- [ ] **Step 2: Run pesticide tests and verify RED**

Run: `python -m pytest tests/ecology/test_pesticide.py -q`

Expected: import fails because the pesticide module is missing.

- [ ] **Step 3: Implement radial deposition and strict spray validation**

Iterate offsets within radius 4, use Euclidean distance, weight `1-r/5`, cap concentration at `1.0`, take max duration with 15, and increment only the center spray-count cell. Reject non-positive/non-finite `delta_l`, invalid reference volume, and out-of-bounds centers; rejected physical spray events are filtered by the wrapper and never call `deposit`.

- [ ] **Step 4: Add failing mortality, overlap, decay, expiration, and round-trip tests**

Assert prey kill `min(concentration*2, 0.98)`, predator kill `min(concentration*0.1, 0.3)`, overlap capping, duration decrement before expiration, concentration multiplication by `0.92`, concentration below `1e-6` clearing, and exact array/dtype restoration.

- [ ] **Step 5: Implement mortality, decay, and state round trip; rerun tests**

Run: `python -m pytest tests/ecology/test_pesticide.py -q`

Expected: all pesticide tests pass and physical litre fields are absent from ecological state, preserving ledger separation.

- [ ] **Step 6: Write failing deterministic wind tests**

```python
def test_dynamic_wind_same_seed_replays_and_different_seed_diverges() -> None:
    left = DynamicWind.initialize(np.random.default_rng(20000), CONFIG)
    right = DynamicWind.initialize(np.random.default_rng(20000), CONFIG)
    other = DynamicWind.initialize(np.random.default_rng(20001), CONFIG)
    assert [left.update() for _ in range(8)] == [right.update() for _ in range(8)]
    assert left.state != other.state
    assert 0.0 <= left.state.strength <= 0.5
```

- [ ] **Step 7: Run wind tests and verify RED**

Run: `python -m pytest tests/ecology/test_wind.py -q`

Expected: wind API is incomplete.

- [ ] **Step 8: Implement scenario-owned wind RNG and exact state restoration**

Initialize direction uniformly on `[0, 2*pi)` and strength uniformly on `[0.0, 0.5]`. Each update increments `step_count`, adds `Normal(0,0.1)` plus `0.005*sin(step_count/50)` to direction, wraps direction modulo `2*pi`, adds `Normal(0,0.05)` to strength, and clips strength. State serialization includes NumPy bit-generator name and a deep copy of its state.

- [ ] **Step 9: Run both suites and commit**

Run: `python -m pytest tests/ecology/test_pesticide.py tests/ecology/test_wind.py -q`

Commit: `git add src/problem2/ecology/pesticide.py src/problem2/ecology/scenario.py tests/ecology/test_pesticide.py tests/ecology/test_wind.py && git commit -m "feat: add pesticide effect and dynamic wind"`

---

### Task 4: Generate Deterministic Dynamic Scenarios And Canonical Identities

**Files:**
- Modify: `src/problem2/ecology/scenario.py`
- Create: `tests/ecology/test_scenario.py`

**Interfaces:**
- Produces: `DynamicPestScenario` with partition, scenario ID, scale ID, grid shape, initial prey/predator/effect state, initial wind state, RNG state, config hash, source commit, implementation version, and `scenario_sha256`.
- Produces: `generate_dynamic_scenario(partition, scenario_id, scale_id, grid_shape, config) -> DynamicPestScenario`.
- Produces: `DynamicPestScenario.state_dict()` and `from_state_dict()` with deep-copy isolation.

- [ ] **Step 1: Write failing initialization and pairing tests**

```python
def test_dynamic_scenario_replays_byte_identically_for_every_paired_method() -> None:
    scenarios = [generate_dynamic_scenario("validation", 20000, "g20x20_d2", (20, 20), CONFIG) for _ in range(5)]
    assert len({scenario.scenario_sha256 for scenario in scenarios}) == 1
    assert all(scenario.initial_prey.tobytes() == scenarios[0].initial_prey.tobytes() for scenario in scenarios)
    assert all(scenario.initial_predator.tobytes() == scenarios[0].initial_predator.tobytes() for scenario in scenarios)


def test_scenario_hash_changes_for_material_ecology_change() -> None:
    baseline = generate_dynamic_scenario("development", 10000, "g20x20_d2", (20, 20), CONFIG)
    changed = generate_dynamic_scenario("development", 10000, "g20x20_d2", (20, 20), replace(CONFIG, beta=1.4))
    assert baseline.scenario_sha256 != changed.scenario_sha256
```

- [ ] **Step 2: Run scenario tests and verify RED**

Run: `python -m pytest tests/ecology/test_scenario.py -q`

Expected: generation API is missing.

- [ ] **Step 3: Implement Gaussian source generation with a dedicated Generator**

Use one or two prey sources and one or two predator sources. Sample centers with integer coordinates in `[h//4, 3*h//4)` and `[w//4, 3*w//4)`. Prey uses sigma `min(h,w)/5`, peak `0.10`, and final clip `0.5`; predator uses sigma `6.0`, peak `0.30`, and non-negative output. Use vectorized coordinate grids and float64 arrays. Construct empty pesticide arrays before initializing wind from the same scenario-owned generator.

- [ ] **Step 4: Implement canonical identity and strict restoration**

Hash canonical metadata JSON plus little-endian contiguous prey, predator, concentration, duration, and spray-count bytes. Canonical metadata includes partition, scenario ID, scale, shape, config hash, initial wind, bit-generator name/state, source commit, and implementation version. Reject development/validation/sealed ID mismatches and any non-canonical or incomplete restored state.

- [ ] **Step 5: Run replay, global-RNG isolation, mutation, and hash tests**

Run: `python -m pytest tests/ecology/test_scenario.py -q`

Expected: all pass; generating a scenario leaves `np.random.get_state()` byte-identical.

- [ ] **Step 6: Commit scenario identity**

Commit: `git add src/problem2/ecology/scenario.py tests/ecology/test_scenario.py && git commit -m "feat: add deterministic dynamic pest scenarios"`

---

### Task 5: Build The Ordered Ecology System And Complete State Round Trip

**Files:**
- Create: `src/problem2/ecology/system.py`
- Create: `tests/ecology/test_system.py`

**Interfaces:**
- Consumes: `DynamicPestScenario`, `AcceptedSpray`, dynamics functions, pesticide field, and dynamic wind.
- Produces: `EcologyTransition(prey_before_total, prey_after_total, predator_before_total, predator_after_total, deposited_effect, wind_vector, step_count)`.
- Produces: `DynamicEcologySystem.from_scenario(scenario, config, reference_spray_l)`.
- Produces: `step(accepted_sprays: Sequence[AcceptedSpray]) -> EcologyTransition`.
- Produces: `global_summary() -> tuple[float, ...]` of exactly eight field-summary and nine global-context values.
- Produces: `local_context(row, col) -> tuple[float, ...]` of exactly six values.
- Produces: `state_dict()` and `load_state_dict()` for prey, predator, pesticide, wind, RNG, counters, and scenario/config hashes.

- [ ] **Step 1: Write a failing update-order spy test and no-spray dynamics test**

Use monkeypatched pure dependencies that append labels and assert this exact order:

```python
assert calls == [
    "deposit", "wind", "mortality", "substep-1", "substep-2", "substep-3", "decay"
]
```

Also assert a no-spray, non-equilibrium field changes because reaction/diffusion/advection remain active.

- [ ] **Step 2: Run system tests and verify RED**

Run: `python -m pytest tests/ecology/test_system.py -q`

Expected: system module is missing.

- [ ] **Step 3: Implement the approved ordered transition**

Deposit all accepted sprays first, update wind once, apply mortality once, execute exactly three Holling-Tanner substeps, then decay effect. Return direct before/after totals and cumulative deposited center-equivalent effect. Do not accept physical actions, resource ledgers, or policy objects in this layer.

- [ ] **Step 4: Add failing summary/local-context and snapshot tests**

Global field summary is: normalized prey total, prey mean, max, standard deviation, high-density ratio (`prey > 0.2`), nonzero coverage, mean pesticide concentration, max pesticide concentration. Global context is six matching predator statistics plus wind direction cosine, sine, and strength normalized by `0.5`. Local context is prey, predator, concentration, centered prey gradient x/y with reflected edges, and 3x3 reflected neighborhood mean prey.

Snapshot test: advance four steps, serialize, restore into a fresh system, then advance both systems for ten steps with the same accepted spray sequence and assert exact equality of every array, wind state, RNG state, transition, and canonical state digest.

- [ ] **Step 5: Implement summaries, local context, and strict snapshots**

State restoration rejects scenario/config hash drift, wrong shape/dtype, NaN/Inf, negative arrays, out-of-range concentration/duration, and unsupported bit-generator. All public array properties return copies or read-only views.

- [ ] **Step 6: Run system tests and commit**

Run: `python -m pytest tests/ecology/test_system.py -q`

Commit: `git add src/problem2/ecology/system.py tests/ecology/test_system.py && git commit -m "feat: add ordered dynamic ecology system"`

---

### Task 6: Integrate Accepted Physical Spray Events And Signed Rewards

**Files:**
- Create: `src/problem2/training/dynamic_env.py`
- Modify: `src/problem2/training/tuning.py`
- Modify: `src/problem2/training/cooperative_env.py`
- Modify: `src/problem2/training/physical_training.py`
- Create: `tests/ecology/test_dynamic_environment.py`
- Modify: `tests/g5/test_physical_candidate_training.py`

**Interfaces:**
- Produces: `DynamicPestEnvironment(physical_environment, ecology, *, partition, source_provenance)`.
- Produces: `build_development_environment(...)` and `build_validation_environment(...)` returning `DynamicPestEnvironment` by default.
- Produces: explicit `build_static_diagnostic_environment(...)` restricted to development and marked `primary_eligible=False`.
- Produces: wrapper `state_dict()` / `load_state_dict()` preserving complete physical/ecological current state and immutable scenario identity.

- [ ] **Step 1: Write failing accepted/rejected event integration tests**

Build a one-cell road fixture with two UAVs: one has exactly one full spray volume and one has zero pesticide. Submit spray for both. Assert one positive `spray` event causes one radial deposit at the spraying UAV's action-complete mapped cell; the rejected/zero `delta_l` event causes no deposit, no ecological spray count, and no `sprayed_pesticide_l` increment.

- [ ] **Step 2: Run wrapper tests and verify RED**

Run: `python -m pytest tests/ecology/test_dynamic_environment.py -q`

Expected: `DynamicPestEnvironment` is missing.

- [ ] **Step 3: Implement the wrapper and replace the local subtraction adapter**

Call `physical.step` first; extract only events with `kind == "spray"` and finite positive `delta_l`; map the action-complete UAV metric position through AOI bounds to ecology row/column; call `ecology.step`; update `physical.initial_total_pest`, `physical.final_total_pest`, `physical.field_summary`, `physical.ecology_global_context`, and `physical.uav_ecology_context`; rebuild the physical view from the completed state. Preserve exact sampled actions, masks, candidate mapping, events, truncation, and resource ledger.

Set `team_reward = (prey_before_total - prey_after_total) / initial_total_prey` with no clamp. Set `metric_source = "dynamic_ecology_environment"`, ecology version/hash/scenario hash, predator totals, concentration diagnostics, wind diagnostics, dynamic-step count, and cumulative deposited effect in the view.

- [ ] **Step 4: Add failing signed-growth, counterfactual, conservation, and restore tests**

Assert no-spray growth can make reward negative, final prey may exceed initial prey, a matched spray trajectory reduces prey more than no-spray at the same step, the physical pesticide conservation residual remains unchanged by ecological effect, and interruption after step `k` plus environment restore reproduces uninterrupted transitions exactly.

- [ ] **Step 5: Implement state round trip and explicit static diagnostic restriction**

Static diagnostic construction requires `partition="development"`, `purpose="static_ecology_diagnostic"`, and an output root outside all primary/validation/sealed namespaces. It exposes `ecology_mode="static_diagnostic"` and cannot be passed to primary runners.

- [ ] **Step 6: Update physical episode logging to direct ecology fields**

Replace `environment.initial_pest`/`environment.pest` accesses with stable wrapper properties `initial_prey`/`prey`. Add ecology version/config/scenario hashes, initial/final predator totals, cumulative deposited effect, terminal mean/max concentration, wind direction/strength, and dynamic-step count. Set `resumable_mid_training` only when the checkpoint state contains the environment snapshot and cursor needed for exact continuation.

- [ ] **Step 7: Run wrapper and physical integration tests**

Run: `python -m pytest tests/ecology/test_dynamic_environment.py tests/g5/test_physical_candidate_training.py -q`

Expected: all pass with no change to physical litre conservation semantics.

- [ ] **Step 8: Commit and push the core integration phase**

Commit: `git add src/problem2/training/dynamic_env.py src/problem2/training/tuning.py src/problem2/training/cooperative_env.py src/problem2/training/physical_training.py tests/ecology/test_dynamic_environment.py tests/g5/test_physical_candidate_training.py && git commit -m "feat: integrate dynamic ecology with physical spraying"`

Run: `git push origin codex/problem2-dynamic-pest-model`

Record the pushed commit and focused verification in `docs/PROJECT_STATE.md` before starting the observation/gate revalidation phase.

---

### Task 7: Populate Existing Observation And Critic Padding Without Shape Drift

**Files:**
- Modify: `src/problem2/environment/observations.py`
- Modify: `src/problem2/training/cooperative_env.py`
- Modify: `docs/evidence/dynamic_pest_v1/heterogeneous_interface.yaml`
- Create: `tests/ecology/test_ecology_observations.py`
- Modify: `tests/g3/test_role_interfaces.py`

**Interfaces:**
- Consumes snapshot keys: `field_summary` (8), `ecology_global_context` (9), and per-UAV `ecology_local_context` (6).
- Produces unchanged role and critic shapes with documented exact index slices.
- Keeps vehicle observation ecology-free and actor signatures free of critic-only fields.

- [ ] **Step 1: Write failing exact-index and action-complete tests**

For `N=2`, assert:

```python
assert observations["uav"].shape == (2, 43 + 68 * 2)
assert observations["vehicle"].shape == (1, 28)
assert critic.shape == (45 + 70 * 2,)
assert np.array_equal(observations["uav"][0, 12:20], field_summary)
assert np.array_equal(observations["uav"][0, 25:34], global_context)
assert np.array_equal(observations["uav"][0, 34:40], uav0_local)
assert np.array_equal(critic[29:38], global_context)
assert np.array_equal(critic[45 + 9:45 + 15], uav0_local)
```

Use the actual established index calculations from the builder when implementing; if the existing pre-ecology base order yields different unoccupied slices, freeze those exact non-overlapping slices in both the test and interface YAML before production editing. The eight field-summary slots already begin after the 7 own-state and 5 vehicle-state values.

- [ ] **Step 2: Run observation tests and verify RED**

Run: `python -m pytest tests/ecology/test_ecology_observations.py tests/g3/test_role_interfaces.py -q`

Expected: ecology-context assertions fail while legacy dimension assertions pass.

- [ ] **Step 3: Populate only existing zero padding and document indices**

Insert global and local values into named base lists before `_pad`; append six local values to each critic per-agent block after its nine existing physical values. Reject ecology vectors with wrong length or non-finite entries instead of silently padding them. Preserve fallback zeros only for explicitly static diagnostic snapshots.

- [ ] **Step 4: Verify actor visibility and semantic checkpoint incompatibility**

Add tests that vehicle observations are byte-identical when ecology-only snapshot values change, UAV observations do not expose `critic_only`, and checkpoint provenance/config hash changes when the dynamic ecology contract hash changes even though tensor dimensions do not.

- [ ] **Step 5: Run G3 interface and checkpoint suites**

Run: `python -m pytest tests/ecology/test_ecology_observations.py tests/g3/test_role_interfaces.py tests/g3/test_training_and_checkpoint.py tests/g5/test_checkpoint_resume.py -q`

- [ ] **Step 6: Commit the fixed-shape interface**

Commit: `git add src/problem2/environment/observations.py src/problem2/training/cooperative_env.py docs/evidence/dynamic_pest_v1/heterogeneous_interface.yaml tests/ecology/test_ecology_observations.py tests/g3/test_role_interfaces.py && git commit -m "feat: expose dynamic ecology in fixed observations"`

---

### Task 8: Accept Dynamic Outcomes And Emit Direct Ecology Provenance

**Files:**
- Create: `docs/evidence/dynamic_pest_v1/raw_episode_schema.yaml`
- Modify: `src/problem2/training/tuning.py`
- Modify: `src/problem2/evaluation/validator.py`
- Modify: `src/problem2/evaluation/schema.py`
- Modify: `tests/g5/test_validation_tuning.py`
- Create: `tests/ecology/test_dynamic_episode_validation.py`

**Interfaces:**
- Consumes: direct fields emitted by `DynamicPestEnvironment` and physical `EpisodeRecord`.
- Produces: `validate_dynamic_episode(row: Mapping[str, Any]) -> None`.
- Produces: dynamic raw-row mapping that retains exact endpoint formula and ecology provenance.

- [ ] **Step 1: Write failing negative-reduction and no-spray-predation tests**

```python
def test_dynamic_validator_accepts_growth_beyond_initial_total() -> None:
    row = valid_dynamic_row(initial_total_pest=10.0, final_total_pest=12.0, spray_action_count=0)
    row["reduction_rate"] = -0.2
    validate_dynamic_episode(row)


def test_dynamic_validator_accepts_predation_reduction_without_spray() -> None:
    row = valid_dynamic_row(initial_total_pest=10.0, final_total_pest=9.0, spray_action_count=0)
    row["reduction_rate"] = 0.1
    validate_dynamic_episode(row)
```

- [ ] **Step 2: Run validation tests and verify RED**

Run: `python -m pytest tests/ecology/test_dynamic_episode_validation.py tests/g5/test_validation_tuning.py -q`

Expected: current validator rejects final pest above initial and positive no-spray reduction.

- [ ] **Step 3: Implement direct dynamic validation**

Require finite non-negative initial/final prey and predator totals, positive initial prey, exact `1-final/(initial+registered_epsilon)` derivation, success threshold `>=0.85`, non-negative spray/deposition counts, dynamic step count matching the episode horizon, exact ecology config/scenario hashes, pesticide-only replenishment, battery inactive, and `metric_source="dynamic_ecology_environment"`. Do not infer ecological provenance from spray count.

- [ ] **Step 4: Add strict dynamic raw schema and mapping**

The schema adds: `ecology_version`, `ecology_config_sha256`, `ecology_scenario_sha256`, `initial_total_predator`, `final_total_predator`, `cumulative_deposited_effect`, `terminal_mean_concentration`, `terminal_max_concentration`, `terminal_wind_direction`, `terminal_wind_strength`, and `dynamic_step_count`. Existing resource, action, mechanism, partition, identity, and source fields remain required.

- [ ] **Step 5: Run validator/schema regression tests**

Run: `python -m pytest tests/ecology/test_dynamic_episode_validation.py tests/g5/test_validation_tuning.py tests/g5/test_orchestration_and_validation.py tests/test_g1_registries.py -q`

- [ ] **Step 6: Commit dynamic evidence rows**

Commit: `git add docs/evidence/dynamic_pest_v1/raw_episode_schema.yaml src/problem2/training/tuning.py src/problem2/evaluation/validator.py src/problem2/evaluation/schema.py tests/ecology/test_dynamic_episode_validation.py tests/g5/test_validation_tuning.py && git commit -m "feat: validate dynamic pest outcomes"`

---

### Task 9: Enforce Dynamic-By-Default Experiment Execution And New Output Namespace

**Files:**
- Create: `src/problem2/experiments/ecology_policy.py`
- Modify: `src/problem2/training/preflight.py`
- Modify: `src/problem2/training/pilot.py`
- Modify: `src/problem2/experiments/orchestrator.py`
- Modify: `scripts/run_g3_training_smoke.py`
- Modify: `scripts/run_g4_mechanism_probe.py`
- Modify: `scripts/run_g5_smoke.py`
- Modify: `scripts/run_g5_pilots.py`
- Modify: `scripts/run_g5_jobs.py`
- Modify: `scripts/run_g5_validation_tuning.py`
- Modify: `scripts/preflight_g6.py`
- Modify: `scripts/run_g6_jobs.py`
- Modify: `scripts/preflight_g7.py`
- Modify: `scripts/run_g7_evaluation.py`
- Create: `tests/ecology/test_experiment_ecology_policy.py`
- Modify: `tests/g5/test_sealed_guards.py`
- Modify: `tests/g5/test_end_to_end_smoke.py`

**Interfaces:**
- Produces: `EcologyMode.DYNAMIC` and `EcologyMode.STATIC_DIAGNOSTIC`.
- Produces: `DYNAMIC_OUTPUT_ROOT = Path("outputs/problem2_sr_mappo_v1/dynamic_pest_v1")`.
- Produces: `resolve_output_root(repository_root, gate, requested_root, *, primary, partition, ecology_mode) -> Path`.
- Produces: `assert_dynamic_primary_environment(environment, *, partition) -> None`.

- [ ] **Step 1: Write failing matrix tests covering every experiment family and CLI**

Parametrize all registered families: algorithm convergence/scale, required five-method comparison, vehicle heuristics, joint/two-stage, SR-MAPPO ablation, and SR-MAPPO sensitivity. Assert default mode is dynamic and output is under `dynamic_pest_v1/<gate>`. Parametrize each CLI entrypoint and assert a static primary request exits nonzero before constructing an environment or writing an artifact.

- [ ] **Step 2: Run policy and sealed-guard tests and verify RED**

Run: `python -m pytest tests/ecology/test_experiment_ecology_policy.py tests/g5/test_sealed_guards.py -q`

Expected: policy module is absent and old G5 output roots remain accepted by current scripts.

- [ ] **Step 3: Implement fail-closed ecology and output policy**

Primary development, validation, formal, and sealed runs accept only dynamic environments whose version/config/scenario hashes match the loaded contract. Static diagnostics accept only development IDs `10000-10019`, `primary=False`, explicit purpose, and a `diagnostics/static_ecology` subdirectory. Reject historical `outputs/problem2_sr_mappo_v1/g5` as a destination for new runs.

- [ ] **Step 4: Wire every runner and CLI through the policy**

Remove implicit historical G5 defaults from active commands. Until renewed candidates/budgets are frozen, validation tuning, G6, and G7 continue to fail closed with a message that dynamic G3-G5 prerequisites are incomplete. Keep sealed unlock count `0`; no test opens or mutates the sealed lock.

- [ ] **Step 5: Verify ablation and sensitivity vary SR-MAPPO only**

Add a configuration-diff test showing every SR-MAPPO ablation/sensitivity condition retains identical ecology config hash, scenario hash, wind stream, predator field, physical resource budget, horizon, and information timing. Only the registered SR component or hyperparameter may differ.

- [ ] **Step 6: Run experiment and CLI regression suites**

Run: `python -m pytest tests/ecology/test_experiment_ecology_policy.py tests/g5/test_experiment_matrix.py tests/g5/test_end_to_end_smoke.py tests/g5/test_sealed_guards.py -q`

- [ ] **Step 7: Commit and push experiment-default enforcement**

Commit: `git add src/problem2/experiments/ecology_policy.py src/problem2/training/preflight.py src/problem2/training/pilot.py src/problem2/experiments/orchestrator.py scripts/run_g3_training_smoke.py scripts/run_g4_mechanism_probe.py scripts/run_g5_smoke.py scripts/run_g5_pilots.py scripts/run_g5_jobs.py scripts/run_g5_validation_tuning.py scripts/preflight_g6.py scripts/run_g6_jobs.py scripts/preflight_g7.py scripts/run_g7_evaluation.py tests/ecology/test_experiment_ecology_policy.py tests/g5/test_sealed_guards.py tests/g5/test_end_to_end_smoke.py && git commit -m "feat: require dynamic ecology for primary experiments"`

Run: `git push origin codex/problem2-dynamic-pest-model`

Record the pushed hash and gate status in `docs/PROJECT_STATE.md` before verification Task 10.

---

### Task 10: Revalidate G3-G5 Interfaces With A Bounded Dynamic Smoke

**Files:**
- Create: `scripts/audit_dynamic_pest.py`
- Create: `tests/ecology/test_dynamic_audit.py`
- Modify: `docs/PROJECT_STATE.md`
- Create under output root when executed: `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation.json`
- Create under output root when executed: `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/smoke/` bounded raw logs and manifest

**Interfaces:**
- Produces: machine-readable implementation audit with source/config hashes, test commands, scenario replay digest, conservation residual, signed-reward evidence, observation dimensions, static-primary rejection, and sealed unlock count.
- Produces: bounded non-claiming dynamic smoke for one development scenario and at least SR-MAPPO plus one same-environment comparator.

- [ ] **Step 1: Write a failing audit test**

Test that `audit_dynamic_pest.py --root <repo> --output <tmp>` emits JSON with `status="pass"`, `maturity="M2"`, `ecology_mode="dynamic"`, `battery_replenishment_enabled=false`, `sealed_accessed=false`, and checks named `numerics`, `scenario_replay`, `accepted_spray`, `conservation`, `fixed_dimensions`, `signed_reward`, and `static_primary_rejected`.

- [ ] **Step 2: Run audit test and verify RED**

Run: `python -m pytest tests/ecology/test_dynamic_audit.py -q`

Expected: audit script is missing.

- [ ] **Step 3: Implement the deterministic audit and bounded smoke command**

The audit uses development scenario `10000`, scale `g20x20_d2`, fixed actions, no validation IDs, no sealed IDs, and no efficacy/superiority assertion. The smoke writes only below `dynamic_pest_v1/g5/smoke`, records environment/config/scenario/source hashes, and marks evidence `development_smoke_only`.

- [ ] **Step 4: Run focused ecology and reopened G3-G5 suites**

Run: `python -m pytest tests/ecology tests/g3 tests/g4 tests/g5 -q`

Expected: all pass. Any failure stops the gate and is fixed with a new failing regression test before rerun.

- [ ] **Step 5: Run the complete repository regression suite**

Run: `python -m pytest -q`

Expected: all tests pass with no warnings promoted by repository policy.

- [ ] **Step 6: Run deterministic audit and bounded dynamic smoke**

Run: `python scripts/audit_dynamic_pest.py --root . --output outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation.json`

Run: `python scripts/run_g5_smoke.py --root . --output-root outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/smoke --method sr_mappo_mobile`

Expected: both exit 0, use development IDs only, and report no validation or sealed access.

- [ ] **Step 7: Review the complete branch**

Run: `git diff origin/main...HEAD --check`

Run: `rg -n "TB[D]|TO[D]O|implement[ ]later|fill[ ]in[ ]details|AG-SR-MAPP[O]|HAPP[O]" src/problem2 tests/ecology configs/problem2/dynamic_pest_v1.yaml docs/evidence/dynamic_pest_v1 scripts/audit_dynamic_pest.py`

Expected: no placeholder, forbidden name, or unfinished implementation match. Legitimate historical mentions outside the scanned dynamic paths remain untouched.

- [ ] **Step 8: Update the authoritative state without overstating maturity**

Record exact test counts/times, audit and smoke artifact hashes, all pushed commits, remote branch hash, unchanged protected external repositories, unchanged historical G5 evidence, M2 as the highest maturity, G3-G5 still reopened until complete multi-seed independent pilots, and G6/G7 blocked. Permitted wording is limited to implementation/interface/invariant verification.

- [ ] **Step 9: Commit, push, and verify remote persistence**

Commit: `git add scripts/audit_dynamic_pest.py tests/ecology/test_dynamic_audit.py outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation.json outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/smoke docs/PROJECT_STATE.md && git commit -m "test: verify dynamic pest integration"`

Run: `git push origin codex/problem2-dynamic-pest-model`

Run: `git rev-parse HEAD; git ls-remote origin refs/heads/codex/problem2-dynamic-pest-model`

Expected: local HEAD and remote hash match exactly.

## Plan Self-Review Record

- Spec coverage: Tasks 1-5 cover source lineage, Holling-Tanner, reflected diffusion, upwind advection, dynamic wind, pesticide deposition/duration/decay, deterministic scenarios, and complete state/RNG replay. Tasks 6-8 cover accepted physical spray events, action-complete observations, signed reward, negative reduction, checkpoint semantics, and direct raw evidence. Tasks 9-10 cover every primary family, static fail-closed behavior, output migration, G3-G5 reopening, sealed lock preservation, verification, and project-state persistence.
- Type consistency: `DynamicEcologyConfig`, `AcceptedSpray`, `DynamicPestScenario`, `DynamicEcologySystem`, and `DynamicPestEnvironment` are introduced once and consumed under the same names/signatures in later tasks.
- Historical boundary: no task edits or rewrites files below `outputs/problem2_sr_mappo_v1/g5`; all generated evidence targets `dynamic_pest_v1`.
- Maturity boundary: the plan produces M2 implementation evidence only. Multi-seed G4/G5 pilot completion, G6 formal jobs, G7 sealed evaluation, statistics, and thesis claims remain separate future gates.
