# G3 Heterogeneous SR-MAPPO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and independently verify the heterogeneous SR-MAPPO learning interface, run a controlled development training smoke, and persist a G3-to-G4 handoff without touching formal or sealed evaluation.

**Architecture:** Build a small role-separated PyTorch package under `src/problem2/algorithms/` and a deterministic observation/training adapter under `src/problem2/training/`. The G2 environment remains the source of legal masks and physical state; G3 stores exact behavior-time masks and normalized policy inputs so PPO replay is independent of later environment state. A machine-readable G3 configuration and gate report bind all dimensions, flags, dependencies, tests, and training artifacts.

**Tech Stack:** Python 3.11, NumPy, PyYAML, PyTorch `2.13.0+cpu` in the current verified environment, pytest, existing G2 road/service/resource modules.

**Spec:** `docs/superpowers/specs/2026-08-20-g3-heterogeneous-marl-design.md`

## Global Constraints

- The public algorithm name is `SR-MAPPO`; do not introduce HAPPO or `AG-SR-MAPPO`.
- Actors use role-local observations only; the centralized critic uses structured global state only during training.
- UAV and vehicle actors have disjoint parameters and optimizers; one shared UAV actor serves homogeneous UAVs.
- G3 must preserve exact masks, candidate mappings, masked old log-probabilities, normalized policy inputs, valid actor samples, termination flags, and normalization versions in each rollout transition.
- Team GAE is computed once per joint transition; true termination cuts bootstrap and time-limit truncation bootstraps from the stored terminal-observation value.
- Forced single-action samples remain in critic/GAE data and are excluded from the corresponding actor loss with `valid_actor_sample`.
- Evaluation freezes all normalization state; sealed-test scenario IDs remain inaccessible.
- G2 remains the trusted physical foundation; candidate branch code may be read selectively but never merged wholesale or treated as accepted evidence.
- Training during this plan is a non-sealed development smoke only. Formal jobs, validation tuning, and sealed evaluation remain unauthorized.
- Battery replenishment remains disabled and pesticide is the only replenished resource.

### Task 1: Freeze G3 contract and dependency surface

**Files:**
- Create: `configs/problem2/g3_heterogeneous_marl.yaml`
- Create: `requirements-g3.lock`
- Modify: `pyproject.toml`
- Create: `tests/g3/test_g3_config.py`
- Create: `docs/evidence/g3/g3_contract.yaml`

**Interfaces:**
- The configuration loader exposes `load_g3_config(path) -> G3Config`.
- `G3Config` exposes `uav_count`, `uav_obs_dim`, `vehicle_obs_dim`,
  `critic_state_dim`, `uav_action_dim`, `vehicle_action_dim`, `max_candidate_slots`,
  `gamma`, `gae_lambda`, `ppo_epochs`, `rollout_horizon`, `total_updates`,
  `stability_components`, and `training_partition`.
- The config hashes canonical YAML bytes and records the PyTorch dependency
  floor/version used by the training smoke.

- [ ] **Step 1: Write failing config tests**

```python
def test_g3_config_freezes_dimensions_and_roles():
    config = load_g3_config(Path("configs/problem2/g3_heterogeneous_marl.yaml"))
    assert config.uav_count == 2
    assert config.uav_obs_dim == 179
    assert config.vehicle_obs_dim == 28
    assert config.critic_state_dim == 185
    assert config.uav_action_dim == 6
    assert config.vehicle_action_dim == 5
    assert config.max_candidate_slots == 4
    assert config.stability_components["value_clipping"] is True

def test_g3_config_rejects_sealed_training_partition():
    payload = yaml.safe_load(
        Path("configs/problem2/g3_heterogeneous_marl.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["training_partition"] = "sealed_test"
    with pytest.raises(G3ConfigError):
        load_g3_payload(payload)
```

- [ ] **Step 2: Run the config tests and verify they fail because the loader and config do not exist**

Run: `python -m pytest tests/g3/test_g3_config.py -q`

Expected: import/attribute failures for the new G3 loader.

- [ ] **Step 3: Add the loader, frozen YAML, lock file, and optional RL dependency**

The YAML must declare `uav_count: 2`, `uav_obs_dim: 179`,
`vehicle_obs_dim: 28`, `critic_state_dim: 185`, six UAV actions, five vehicle
actions, `max_candidate_slots: 4`, `training_partition: development`, and all
seven stability flags. `pyproject.toml` keeps the G2 dependency set intact and
adds an `rl` extra for PyTorch. `requirements-g3.lock` records the current
verified CPU package version without changing `requirements-g2.lock`.

- [ ] **Step 4: Run the focused config tests**

Run: `python -m pytest tests/g3/test_g3_config.py -q`

Expected: all focused config tests pass.

- [ ] **Step 5: Commit**

```powershell
git add configs/problem2/g3_heterogeneous_marl.yaml requirements-g3.lock pyproject.toml tests/g3/test_g3_config.py docs/evidence/g3/g3_contract.yaml
git commit -m "feat: freeze g3 heterogeneous marl contract"
```

### Task 2: Implement replay-critical common math and rollout storage

**Files:**
- Create: `src/problem2/algorithms/common/masked_distribution.py`
- Create: `src/problem2/algorithms/common/gae.py`
- Create: `src/problem2/algorithms/common/normalization.py`
- Create: `src/problem2/algorithms/sr_mappo/rollout.py`
- Create: `tests/g3/test_common_math_and_rollout.py`

**Interfaces:**
- `masked_categorical(logits, mask)` returns a Torch categorical distribution
  with exact zero probability for invalid actions.
- `compute_gae(rewards, values, terminated, truncated, last_value, next_values,
  gamma, gae_lambda)` returns float32 advantage and return arrays.
- `RunningNormalizer.update`, `.normalize(values, update=False)`, `.state_dict`, and
  `.load_state_dict` implement role-separated frozen statistics.
- `RolloutBatch.add(transition)`, `.finish(gamma, gae_lambda)`,
  `.normalize_advantages()`, and
  `.role_valid_mask(role)` preserve the complete G3 rollout contract.

- [ ] **Step 1: Write failing tests for masked replay, GAE, normalization, and rollout metadata**
- [ ] **Step 2: Run `python -m pytest tests/g3/test_common_math_and_rollout.py -q` and confirm expected missing-module failures**
- [ ] **Step 3: Implement the minimal common modules and rollout dataclass**
- [ ] **Step 4: Run the focused suite and inspect numeric tolerances**
- [ ] **Step 5: Commit**

```powershell
git add src/problem2/algorithms/common src/problem2/algorithms/sr_mappo/rollout.py tests/g3/test_common_math_and_rollout.py
git commit -m "feat: add g3 replay math and rollout contract"
```

### Task 3: Implement role-local observations, actors, critic, and losses

**Files:**
- Create: `src/problem2/environment/observations.py`
- Create: `src/problem2/environment/action_masks.py`
- Create: `src/problem2/algorithms/sr_mappo/actors.py`
- Create: `src/problem2/algorithms/sr_mappo/critic.py`
- Create: `src/problem2/algorithms/sr_mappo/losses.py`
- Create: `tests/g3/test_role_interfaces.py`

**Interfaces:**
- `build_role_observations(snapshot, uav_count, max_candidate_slots)` returns
  role-local NumPy arrays with dimensions `179` and `28`.
- `build_structured_critic_state(snapshot, uav_count, max_candidate_slots)`
  returns a `185`-element vector with stable block ordering.
- `RoleActor(input_dim, action_dim, hidden_dim=128, orthogonal_initialization=True,
  layer_normalization=True)` accepts only a role observation tensor and returns
  logits.
- `CentralCritic(state_dim, hidden_dim=128, orthogonal_initialization=True,
  layer_normalization=True)` accepts only the structured critic vector and
  returns one team value per row.
- `ppo_policy_loss`, `value_loss`, and `entropy_bonus` are pure tensor losses.

- [ ] **Step 1: Write failing tests for dimensions, information boundaries, role parameter disjointness, and loss numerics**
- [ ] **Step 2: Run the focused role suite and verify expected failures**
- [ ] **Step 3: Implement observation packing with explicit fixed block sizes**
- [ ] **Step 4: Implement actors, critic, and losses with orthogonal initialization and optional layer normalization**
- [ ] **Step 5: Run the focused role suite**
- [ ] **Step 6: Commit**

```powershell
git add src/problem2/environment src/problem2/algorithms/sr_mappo/actors.py src/problem2/algorithms/sr_mappo/critic.py src/problem2/algorithms/sr_mappo/losses.py tests/g3/test_role_interfaces.py
git commit -m "feat: implement role-local heterogeneous policy interfaces"
```

### Task 4: Implement SR-MAPPO collection, trainer, and atomic checkpoint

**Files:**
- Create: `src/problem2/algorithms/sr_mappo/algorithm.py`
- Create: `src/problem2/algorithms/sr_mappo/trainer.py`
- Create: `src/problem2/algorithms/common/checkpoint.py`
- Create: `src/problem2/algorithms/common/config_diff.py`
- Create: `tests/g3/test_training_and_checkpoint.py`

**Interfaces:**
- `SRMAPPOAlgorithm.act(observations, masks, deterministic, return_details)`
  samples from the exact stored mask and returns actions, normalized inputs,
  masked log-probabilities, entropies, and normalizer versions.
- `SRMAPPOAlgorithm.value(state)` returns the centralized team value.
- `SRMAPPOTrainer.update(batch, epochs, progress)` updates critic, UAV actor,
  and vehicle actor with disjoint optimizers and returns update counts.
- `save_checkpoint(path, algorithm, step, provenance)` writes atomically.
- `load_checkpoint(path, algorithm_factory)` restores model, trainer,
  normalizers, RNG, and provenance.
- `configuration_diff(sr_config, mappo_config)` returns a machine-readable
  diff restricted to the declared stability flags.

- [ ] **Step 1: Write failing tests for gradient isolation, update counts, evaluation freeze, checkpoint round trip, RNG restoration, and configuration diff**
- [ ] **Step 2: Run `python -m pytest tests/g3/test_training_and_checkpoint.py -q` and verify expected failures**
- [ ] **Step 3: Implement algorithm collection and exact mask replay**
- [ ] **Step 4: Implement role-isolated trainer, value clipping/Huber objective, and learning-rate decay**
- [ ] **Step 5: Implement atomic checkpoint and configuration diff**
- [ ] **Step 6: Run focused training/checkpoint tests**
- [ ] **Step 7: Commit**

```powershell
git add src/problem2/algorithms tests/g3/test_training_and_checkpoint.py
git commit -m "feat: add g3 sr-mappo trainer and checkpointing"
```

### Task 5: Add a controlled non-sealed development training runner

**Files:**
- Create: `src/problem2/training/development_env.py`
- Create: `src/problem2/training/train_g3_smoke.py`
- Create: `tests/g3/test_training_smoke.py`
- Create: `scripts/run_g3_training_smoke.py`

**Interfaces:**
- `DevelopmentCooperativeEnv(seed, config)` produces deterministic role-local
  observations, structured critic state, legal masks, shared rewards,
  termination/truncation, candidate mappings, and resource-neutral transitions
  without reading validation or sealed scenario IDs.
- `run_training_smoke(config_path, output_root, seed, updates)` writes a raw
  JSONL development log, a checkpoint, and a provenance report containing
  config hash, source-tree commit, update count, finite-loss checks, and
  `sealed_test_accessed: false`.

- [ ] **Step 1: Write failing tests for deterministic reset, legal action masks, finite rollout/update, and sealed-range refusal**
- [ ] **Step 2: Run the smoke tests and verify missing-runner failures**
- [ ] **Step 3: Implement the smallest deterministic development environment adapter**
- [ ] **Step 4: Implement the training loop with one rollout per update and atomic checkpointing**
- [ ] **Step 5: Run the smoke tests**
- [ ] **Step 6: Commit**

```powershell
git add src/problem2/training scripts/run_g3_training_smoke.py tests/g3/test_training_smoke.py
git commit -m "feat: add nonsealed g3 training smoke"
```

### Task 6: Run the G3 acceptance suite and produce the gate report

**Files:**
- Create: `scripts/audit_g3_marl.py`
- Create: `tests/g3/test_g3_audit.py`
- Create: `outputs/problem2_sr_mappo_v1/g3/g3-marl-audit.json`
- Create: `outputs/problem2_sr_mappo_v1/g3/training-smoke.jsonl`
- Create: `outputs/problem2_sr_mappo_v1/g3/checkpoints/g3-smoke.pt`
- Create: `docs/audits/g3-marl-compliance.md`
- Create: `HANDOFFG3.md`
- Modify: `docs/PROJECT_STATE.md`

- [ ] **Step 1: Write failing audit tests for required test names, report fields, provenance, and no sealed access**
- [ ] **Step 2: Run the audit tests and verify the report is absent**
- [ ] **Step 3: Implement the fail-closed G3 auditor**
- [ ] **Step 4: Run the complete G3 suite, full regression suite, compileall, and diff hygiene**

```powershell
python -m pytest tests/g3 -q
python -m pytest -q
python -m compileall -q src scripts
git diff --check
```

- [ ] **Step 5: Run the G3 smoke with a fresh development seed and audit the generated artifacts**
- [ ] **Step 6: Ask an independent reviewer to inspect the full G3 diff and repair all Critical/Important findings**
- [ ] **Step 7: Commit**

```powershell
git add scripts/audit_g3_marl.py tests/g3/test_g3_audit.py outputs/problem2_sr_mappo_v1/g3 docs/audits/g3-marl-compliance.md HANDOFFG3.md docs/PROJECT_STATE.md
git commit -m "docs: record g3 heterogeneous marl verification"
```

### Task 7: Persist G3 and authorize the G4 handoff

- [ ] **Step 1: Run the complete fresh verification after the content commit**
- [ ] **Step 2: Push the G3 branch to `origin`**
- [ ] **Step 3: Record the pushed content hash in `docs/PROJECT_STATE.md`**
- [ ] **Step 4: Create and push a separate persistence-record commit**
- [ ] **Step 5: Verify local HEAD, upstream HEAD, and `git ls-remote` agree**
- [ ] **Step 6: Confirm the highest maturity remains M2 unless an independently registered pilot criterion is met; mark G3 passed and G4 as next authorized gate**

G4 is authorized only after the persistence record exists. G4 must begin with
resource activation and counterfactual probes; it must not use the G3 smoke as
endpoint evidence.
