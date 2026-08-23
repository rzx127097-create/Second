# G5 Fair-Pilot and Method-Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, pilot, audit, and freeze the complete Problem-2 experiment system needed for fair G6 formal jobs and one-time G7 sealed analysis without running either gate.

**Architecture:** Extend the verified G2/G3 code into one role-aware algorithm protocol with shared environment, mask, checkpoint, identity, metric, and validation contracts. Keep method-specific learning logic in separate packages, express experiment families as immutable manifests, and drive all pilot, tuning, statistics, and later G6/G7 execution paths through shared orchestration code. Resolve the G4 lineage inconsistency before accepting any G5 pilot artifact, then freeze every scientific input with Git and SHA-256 provenance while the sealed partition remains locked.

**Tech Stack:** Python 3.11, NumPy 2.4, PyYAML 6, NetworkX 3.6, PyTorch 2.13 CPU/CUDA, pytest 9, existing G2 road/service/resource modules and G3 heterogeneous SR-MAPPO modules.

**Spec:** `docs/superpowers/specs/2026-08-22-g5-pilot-freeze-design.md`

## Global Constraints

- The public algorithm name is `SR-MAPPO`; Problem 2 is its air-ground heterogeneous extension. Do not introduce HAPPO or `AG-SR-MAPPO`.
- Pesticide is the only replenished resource. Battery replenishment remains disabled.
- OSM/GraphML data are read-only simulation inputs, not field-deployment evidence.
- G4 remains diagnostic support-probe evidence. It is not a learned-policy or treatment-efficacy result.
- Resolve and push the G4 lineage reconciliation before accepting any G5 pilot artifact.
- Problem-1 code is read-only lineage at commit `1ca9e5ccc5f77ed775cd2b607dd70d635720accf`; no Problem-1 runtime import, checkpoint, output, log, or result may enter Problem-2 evidence.
- All Problem-2 artifacts stay below `outputs/problem2_sr_mappo_v1`; G5 artifacts stay below `outputs/problem2_sr_mappo_v1/g5`.
- Development pilot training seeds are exactly `51001`, `51002`, `51003`; development scenario IDs are exactly `10000-10019`.
- Formal training seeds remain `42`, `123`, `2024`, `3407`, `7919`; validation IDs remain `20000-20049`; sealed IDs remain `30000-30099`.
- G5 may access validation only after candidate manifests and the tie-break rule are hashed. No G5 executable may access sealed IDs, and `actual_unlock_count` remains `0`.
- Training seed is the independent replication level; scenarios are paired within seed.
- Primary outcomes are reduction rate and the probability that $\mathrm{reduction\_rate} \ge 0.85$.
- The hierarchical paired bootstrap uses `10,000` replicates and RNG seed `20260822`; practical-equivalence margins are `0.02` for reduction rate and `0.05` for success probability.
- A poor result, long wait, failure to reach `0.85`, or unfavorable ranking is never an exclusion reason.
- Formal training jobs and sealed evaluation are prohibited in G5. G5 creates and audits their manifests and executables only.
- No existing Word file or protected external asset may be modified.
- Preserve `requirements-g3.lock` and its CPU-only G3 evidence. G5 GPU work uses the project-local `.venv-g5` and must not replace packages in the Codex/Hermes host environment.
- Every important G5 phase must pass fresh verification, be committed, pushed, and recorded in `docs/PROJECT_STATE.md` before the next phase begins.
- Formula-like prose in Markdown uses editable LaTeX notation; code paths and identifiers remain literal code spans.

## File Ownership Map

- `src/problem2/algorithms/protocol.py`: common heterogeneous learning protocol and typed transition/evaluation results.
- `src/problem2/algorithms/common/`: shared masks, networks, replay, normalization, checkpoint, identity, and diagnostics.
- `src/problem2/algorithms/{sr_mappo,mappo,ippo,maddpg,iql}/`: method-specific networks and update mathematics only.
- `src/problem2/heuristics/`: fixed support, rolling A*, nearest-feasible, urgency, and deterministic controller adapters.
- `src/problem2/training/`: environment-backed collection, training, tuning, checkpoint selection, and resume.
- `src/problem2/evaluation/`: deterministic evaluation, metric accumulation, partition guards, and state-freeze proofs.
- `src/problem2/experiments/`: family manifests, job generation/deduplication, orchestration, ledgers, and audits.
- `src/problem2/statistics/`: convergence summaries, hierarchical paired bootstrap, Holm adjustment, equivalence classification, and mechanism summaries.
- `configs/problem2/g5/`: executable method, pilot, tuning, budget, family, ablation, sensitivity, metric, and statistics contracts.
- `docs/evidence/g5/`: source lineage, fairness, estimand, exclusion, selection, and freeze registries.
- `tests/g5/`: G5 unit, integration, negative-path, smoke, and audit acceptance suites.
- `scripts/`: thin CLI entry points over tested library functions.
- `outputs/problem2_sr_mappo_v1/g5/`: generated G5 pilots, validation results, audits, manifests, and freeze artifacts.

---

### Task 1: Reconcile and persist the accepted G4 lineage

**Files:**
- Create: `scripts/audit_g4_lineage.py`
- Create: `tests/g5/test_g4_lineage_reconciliation.py`
- Create: `docs/audits/g4-lineage-reconciliation.md`
- Modify: `HANDOFFG4.md`
- Modify: `docs/PROJECT_STATE.md`
- Regenerate only if required by the audit: `outputs/problem2_sr_mappo_v1/g4/**`

**Interfaces:**
- `audit_g4_lineage(repository_root: Path, output_root: Path) -> G4LineageReport` resolves every recorded Git object and verifies the provenance, source tree, source-file hashes, source-bundle hash, contract hash, artifact hashes, and manifest bytes.
- `G4LineageReport.status` is `pass` only when one exact generator commit/tree/file-hash/bundle-hash tuple is consistent across canonical artifacts and current documentation.
- The repair decision is deterministic: preserve the current canonical bundle only if all embedded hashes reproduce from its recorded clean generator; otherwise regenerate from the intended clean generator `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` and replace the canonical bundle through the existing G4 generator/auditor.

- [x] **Step 1: Write failing lineage tests**

```python
def test_lineage_audit_rejects_nonexistent_recorded_commit(repo_copy):
    replace_text(repo_copy / "HANDOFFG4.md", "4e8156712986", "4e81567aef9e")
    with pytest.raises(G4LineageError, match="not a Git object"):
        audit_g4_lineage(repo_copy, repo_copy / "outputs/problem2_sr_mappo_v1/g4")

def test_lineage_audit_requires_one_exact_generator_tuple(repository_root):
    report = audit_g4_lineage(
        repository_root,
        repository_root / "outputs/problem2_sr_mappo_v1/g4",
    )
    assert report.status == "pass"
    assert len(report.generator_commits) == 1
    assert len(report.source_trees) == 1
```

- [x] **Step 2: Run `python -m pytest tests/g5/test_g4_lineage_reconciliation.py -q` and confirm failure because the reconciliation auditor does not exist**
- [x] **Step 3: Implement the fail-closed auditor and run it against the current canonical bundle**
- [x] **Step 4: Apply the deterministic repair branch selected by the audit, rerun the G4 generator only when required, and update the reconciliation report, handoff, and project state with real full hashes**
- [x] **Step 5: Run the focused test, `python -m pytest tests/g4 tests/g5/test_g4_lineage_reconciliation.py -q`, the G4 CLI audit, `python -m compileall -q src scripts`, and `git diff --check`**
- [x] **Step 6: Commit and push the G4 reconciliation content**

```powershell
git add scripts/audit_g4_lineage.py tests/g5/test_g4_lineage_reconciliation.py docs/audits/g4-lineage-reconciliation.md HANDOFFG4.md docs/PROJECT_STATE.md outputs/problem2_sr_mappo_v1/g4
git commit -m "fix: reconcile g4 evidence lineage"
git push origin codex/problem2-g5-pilot-freeze
```

- [x] **Step 7: Record the pushed content hash and verification in `docs/PROJECT_STATE.md`, commit `docs: record g4 lineage persistence`, push, and verify local HEAD, upstream HEAD, and `git ls-remote` match**

### Task 2: Freeze the G5 registry, fairness, budget-selection, and partition contracts

**Files:**
- Create: `src/problem2/experiments/g5_contract.py`
- Create: `requirements-g5.lock`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `configs/problem2/g5/protocol.yaml`
- Create: `configs/problem2/g5/methods.yaml`
- Create: `configs/problem2/g5/pilot.yaml`
- Create: `configs/problem2/g5/tuning_candidates.yaml`
- Create: `configs/problem2/g5/budget_rule.yaml`
- Create: `configs/problem2/g5/metrics.yaml`
- Create: `configs/problem2/g5/statistics.yaml`
- Create: `docs/evidence/g5/problem1_lineage.yaml`
- Create: `docs/evidence/g5/heterogeneous_interface.yaml`
- Create: `docs/evidence/g5/fairness_matrix.yaml`
- Create: `docs/evidence/g5/exclusion_contract.yaml`
- Create: `docs/evidence/g5/checkpoint_selection.yaml`
- Modify: `docs/evidence/g1/scenario_seed_manifest.yaml`
- Create: `tests/g5/test_g5_contracts.py`
- Create: `scripts/audit_g5_contracts.py`

**Interfaces:**
- `load_g5_contract(root: Path) -> G5Contract` rejects unknown/duplicate YAML keys, non-finite values, overlapping partitions, battery replenishment, forbidden names, unresolved lineage blobs, missing fairness flags, and validation/sealed leakage.
- `G5Contract.methods` contains exactly `sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`, `maddpg_mobile`, and `iql_mobile` as the five learning algorithms and separately registers all Problem-2 conditions.
- `requirements-g5.lock` retains the G2 dependency lock and pins `torch==2.13.0+cu126` from `https://download.pytorch.org/whl/cu126`; the wheel availability preflight was verified for Windows CPython 3.11. G3's `torch==2.13.0+cpu` lock remains unchanged.
- `.venv-g5` is ignored by Git. Every G5 CPU/CUDA verification after this task runs from `.venv-g5`; `torch.cuda.is_available()` must be true there while ordinary CPU tensor execution remains supported.
- `select_formal_budget(runtime_rows, candidate_budgets) -> BudgetDecision` selects the largest value in the frozen candidate grid `[50000, 100000, 200000]` for which the conservative projected slowest-method `g30x50_d4` job is at most `12` hours and the checkpoint count is at least `20`; if no candidate passes, G5 fails instead of inventing a smaller scientific budget. Checkpoint interval is the selected budget divided by `20` and must be integral.
- Tuning contains four immutable candidates per learning algorithm. Selection maximizes mean validation reduction rate, then success probability, then lower interaction count, then lexicographically smaller config hash.
- SR-MAPPO, MAPPO, and IPPO candidates keep learning rate `3e-4`, clipping radius `0.20`, entropy coefficient `0.010`, discount `0.99`, GAE trace `0.95`, and hidden width/depth fixed so the sensitivity center remains identical to the primary job. Their four `(rollout_horizon, ppo_epochs, minibatch_size)` candidates are `(32, 2, 64)`, `(64, 2, 64)`, `(64, 4, 128)`, and `(128, 4, 128)`.
- MADDPG candidates keep network capacity, replay capacity, discount, exploration endpoints, and interaction budget fixed. Their four `(actor_lr, critic_lr, tau, batch_size)` candidates are `(1e-4, 3e-4, 0.005, 64)`, `(3e-4, 3e-4, 0.005, 64)`, `(1e-4, 1e-3, 0.010, 128)`, and `(3e-4, 1e-3, 0.010, 128)`.
- IQL candidates keep network capacity, replay capacity, discount, initial/final exploration, and interaction budget fixed. Their four `(learning_rate, target_update_interval, epsilon_decay, batch_size)` candidates are `(1e-4, 100, 0.999, 64)`, `(3e-4, 100, 0.999, 64)`, `(3e-4, 250, 0.995, 128)`, and `(5e-4, 250, 0.995, 128)`.

- [x] **Step 1: Write failing tests for the exact CUDA dependency lock, unchanged G3 CPU lock, exact methods, Problem-1 blob resolution, partition disjointness, fairness invariants, candidate immutability, budget-rule edge cases, metric definitions, and sealed denial**
- [x] **Step 2: Run `python -m pytest tests/g5/test_g5_contracts.py -q` and confirm missing-contract failures**
- [x] **Step 3: Create the isolated G5 environment, install the G5 lock, and verify CPU/CUDA execution without modifying the host environment**

```powershell
py -3.11 -m venv .venv-g5
.venv-g5/Scripts/python.exe -m pip install -r requirements-g5.lock
.venv-g5/Scripts/python.exe -c "import torch; assert torch.__version__ == '2.13.0+cu126'; assert torch.cuda.is_available(); print(torch.__version__, torch.cuda.get_device_name(0))"
```

- [x] **Step 4: Implement strict loaders and create the canonical YAML registries with exact values from the G5 design**
- [x] **Step 5: Add development seeds/scenarios to the G1 seed registry without changing formal, validation, or sealed identities**
- [x] **Step 6: Implement `scripts/audit_g5_contracts.py` to print hashes, methods, partitions, fairness booleans, and `sealed_accessed=false`**
- [x] **Step 7: Run the focused suite and exact registry/document checks from `.venv-g5`**

```powershell
$g5AuditTemp = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ("g5-contract-" + [guid]::NewGuid()))
.venv-g5/Scripts/python.exe -m pytest tests/g5/test_g5_contracts.py tests/test_g1_registries.py tests/test_g1_feature_branch_audit.py -q
.venv-g5/Scripts/python.exe scripts/audit_g1_registries.py --root docs/evidence/g1 --report (Join-Path $g5AuditTemp "registry-audit.json")
.venv-g5/Scripts/python.exe scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown (Join-Path $g5AuditTemp "feature-branch-audit.md") --json (Join-Path $g5AuditTemp "feature-branch-audit.json")
.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py
.venv-g5/Scripts/python.exe C:/Users/RZX/.codex/skills/thesis-formula-symbol-guard/scripts/audit_formula_symbols.py docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md
.venv-g5/Scripts/python.exe -m compileall -q src scripts
git diff --check
```
- [x] **Step 8: Commit, push, record the pushed hash in project state, and push the persistence record before algorithm implementation begins**

```powershell
git add requirements-g5.lock pyproject.toml .gitignore src/problem2/experiments/g5_contract.py configs/problem2/g5 docs/evidence/g5 docs/evidence/g1/scenario_seed_manifest.yaml tests/g5/test_g5_contracts.py scripts/audit_g5_contracts.py docs/PROJECT_STATE.md
git commit -m "feat: freeze g5 experiment contracts"
git push origin codex/problem2-g5-pilot-freeze
```

### Task 3: Define the shared heterogeneous algorithm, transition, replay, and checkpoint protocol

**Files:**
- Create: `src/problem2/algorithms/protocol.py`
- Create: `src/problem2/algorithms/common/networks.py`
- Create: `src/problem2/algorithms/common/replay.py`
- Create: `src/problem2/algorithms/common/diagnostics.py`
- Modify: `src/problem2/algorithms/common/checkpoint.py`
- Modify: `src/problem2/algorithms/common/masked_distribution.py`
- Modify: `src/problem2/algorithms/__init__.py`
- Create: `tests/g5/test_algorithm_protocol.py`
- Create: `tests/g5/test_checkpoint_resume.py`

**Interfaces:**
- `HeterogeneousAlgorithm` defines `act`, `observe`, `update`, `set_evaluation`, `state_dict`, `load_state_dict`, and `diagnostics` for both UAV and vehicle roles.
- `RoleBatch` stores role-local observations, exact behavior masks, actions, rewards, next observations/masks, termination/truncation, scenario identity, and transition identity.
- `JointReplayBuffer.state_dict()` includes data, insertion index, size, RNG state, and schema version.
- `save_training_checkpoint(path, state, provenance) -> CheckpointRecord` writes to a same-filesystem temporary path, flushes, verifies reload and SHA-256, atomically renames, and retains the previous valid checkpoint.
- `load_training_checkpoint(path: Path, algorithm_factory: Callable[[], HeterogeneousAlgorithm], expected_hashes: Mapping[str, str]) -> tuple[HeterogeneousAlgorithm, CheckpointRecord]` rejects source/config/protocol/ancestry drift.

- [x] **Step 1: Write failing protocol-conformance tests with a minimal fake two-role algorithm**

```python
@pytest.mark.parametrize("role,shape", [("uav", (2, 6)), ("vehicle", (1, 5))])
def test_protocol_never_selects_masked_action(two_role_algorithm, batch, role, shape):
    result = two_role_algorithm.act(batch.observations, batch.masks, deterministic=False)
    assert result.actions[role].shape == shape[:1]
    assert batch.masks[role][np.arange(shape[0]), result.actions[role]].all()
```

- [x] **Step 2: Write failing checkpoint tests for hash-after-reload, method-specific state, replay/rollout position, all RNG states, atomic replacement, and uninterrupted-versus-resumed next-update equivalence**
- [x] **Step 3: Run both focused files and confirm the new protocol/checkpoint APIs are absent**
- [x] **Step 4: Implement the protocol, shared networks/replay/diagnostics, and versioned G5 checkpoint adapter while preserving G3 checkpoint loading**
- [x] **Step 5: Run focused tests plus `.venv-g5/Scripts/python.exe -m pytest tests/g3 -q` to prove backward compatibility**
- [x] **Step 6: Commit `feat: add shared g5 heterogeneous algorithm protocol`, push, and persist the verified hash**

### Task 4: Adapt SR-MAPPO and implement same-source MAPPO and role-local PPO/IPPO

**Files:**
- Modify: `src/problem2/algorithms/sr_mappo/algorithm.py`
- Modify: `src/problem2/algorithms/sr_mappo/trainer.py`
- Modify: `src/problem2/algorithms/sr_mappo/rollout.py`
- Create: `src/problem2/algorithms/mappo/__init__.py`
- Create: `src/problem2/algorithms/mappo/algorithm.py`
- Create: `src/problem2/algorithms/ippo/__init__.py`
- Create: `src/problem2/algorithms/ippo/algorithm.py`
- Create: `src/problem2/algorithms/ippo/trainer.py`
- Create: `tests/g5/test_on_policy_algorithms.py`

**Interfaces:**
- `build_algorithm(method_id, contract, device) -> HeterogeneousAlgorithm` returns protocol-conforming implementations.
- SR-MAPPO retains the shared UAV actor, separate vehicle actor, centralized team critic, GAE/PPO, and all five stability groups.
- MAPPO uses the same heterogeneous actors, critic, rollout, and budget interface and differs only in the exact stability flags declared by `methods.yaml`.
- IPPO uses a shared UAV local actor/value pair and a separate vehicle local actor/value pair; neither local value function accepts structured critic-only state.

- [x] **Step 1: Write failing parameterized tests for both roles, stored-mask log-prob replay, GAE gold values, actor/critic information boundaries, optimizer isolation, deterministic evaluation freeze, and complete checkpoints for all three methods**
- [x] **Step 2: Write a configuration-diff test proving SR-MAPPO versus MAPPO differs only in the frozen stability groups**
- [x] **Step 3: Run `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_on_policy_algorithms.py -q` and confirm expected failures**
- [x] **Step 4: Adapt SR-MAPPO to the protocol without changing its accepted G3 mathematics; implement MAPPO as a same-source configuration adapter**
- [x] **Step 5: Implement role-local IPPO values and updates with the same masks, interactions, horizons, and diagnostics**
- [x] **Step 6: Run the focused suite, G3 regression, compileall, and diff hygiene**
- [ ] **Step 7: Commit `feat: implement g5 on-policy comparison algorithms`, push, and persist the verified hash**

### Task 5: Implement heterogeneous discrete MADDPG and IQL

**Files:**
- Create: `src/problem2/algorithms/maddpg/__init__.py`
- Create: `src/problem2/algorithms/maddpg/algorithm.py`
- Create: `src/problem2/algorithms/maddpg/networks.py`
- Create: `src/problem2/algorithms/maddpg/trainer.py`
- Create: `src/problem2/algorithms/iql/__init__.py`
- Create: `src/problem2/algorithms/iql/algorithm.py`
- Create: `src/problem2/algorithms/iql/networks.py`
- Create: `src/problem2/algorithms/iql/trainer.py`
- Create: `tests/g5/test_off_policy_algorithms.py`

**Interfaces:**
- MADDPG has shared UAV and separate vehicle discrete actors, centralized role Q critics, target networks, replay, and straight-through masked Gumbel-Softmax actor updates.
- `masked_straight_through_gumbel(logits, mask, temperature) -> Tensor` returns zero mass and zero actor gradient for illegal actions.
- IQL has shared UAV and separate vehicle Q/target-Q networks; `masked_bootstrap_max(q, mask)` excludes illegal next actions and raises on all-false masks.
- Deterministic MADDPG evaluation uses masked actor argmax; deterministic IQL evaluation uses masked greedy actions with $\varepsilon=0$.

- [ ] **Step 1: Write failing MADDPG tests for both roles, joint-action critic input, stored masks, illegal-action zero mass/gradient, target updates, replay round trip, and deterministic evaluation**
- [ ] **Step 2: Write failing IQL tests for both roles, masked $\varepsilon$-greedy behavior, illegal bootstrap exclusion, target updates, replay round trip, and $\varepsilon=0$ evaluation**
- [ ] **Step 3: Run the focused suite and confirm missing-module failures**
- [ ] **Step 4: Implement MADDPG networks/updates and verify actor gradients reach only the selected role actor while all illegal logits remain excluded**
- [ ] **Step 5: Implement IQL networks/updates and verify role parameter, optimizer, target, exploration, and replay isolation**
- [ ] **Step 6: Run focused, algorithm-protocol, checkpoint-resume, and G3 regression suites**
- [ ] **Step 7: Commit `feat: implement heterogeneous maddpg and iql`, push, and persist the verified hash**

### Task 6: Implement the physical training/evaluation adapter, formal metrics, and support controllers

**Files:**
- Create: `src/problem2/training/cooperative_env.py`
- Create: `src/problem2/evaluation/metrics.py`
- Create: `src/problem2/evaluation/runner.py`
- Create: `src/problem2/evaluation/partitions.py`
- Create: `src/problem2/heuristics/__init__.py`
- Create: `src/problem2/heuristics/fixed.py`
- Create: `src/problem2/heuristics/astar.py`
- Create: `src/problem2/heuristics/nearest.py`
- Create: `src/problem2/heuristics/urgency.py`
- Create: `src/problem2/heuristics/two_stage.py`
- Create: `tests/g5/test_environment_metrics.py`
- Create: `tests/g5/test_heuristics.py`

**Interfaces:**
- `Problem2CooperativeEnv` wraps the verified G2 road, motion, service, and pesticide ledger and emits G3 role observations/masks without replacing sampled actions.
- `EpisodeMetrics` directly accumulates road-route rendezvous distance, realized service travel, total pending/reserved waiting exposure including unresolved terminal waits, completed-request wait, pesticide-disabled UAV-time, return UAV-time, effective positive spray steps, service outcomes, transfer/inventory, resource residual, and decision-only runtime.
- `evaluate_episode(environment: Problem2CooperativeEnv, policy: PolicyAdapter, partition: str, scenario_id: int, deterministic: bool = True) -> EpisodeRecord` freezes learning/normalization/exploration state and returns a before/after byte identity proof.
- A*, nearest, and urgency controllers use observable current requests/road state only, deterministic tie-breaking, frozen replanning, and no future pest/demand state.
- Two-stage training consumes exactly the same total interaction budget as joint SR-MAPPO and records both stage budgets in checkpoint ancestry.

- [ ] **Step 1: Write failing metric tests for the exact G5 definitions, including unresolved terminal wait, zero transfer, partial service, actual road detour, and pesticide conservation**
- [ ] **Step 2: Write failing controller tests for fixed-resource matching, A* versus Dijkstra on sampled graphs, deterministic ties, unreachable requests, service feasibility, no-future-state signatures, and two-stage budget equality**
- [ ] **Step 3: Run both focused suites and confirm missing-adapter failures**
- [ ] **Step 4: Implement the adapter and direct event metrics over the accepted G2 state machine**
- [ ] **Step 5: Implement fixed, A*, nearest, urgency, and two-stage adapters; time only controller decision computation**
- [ ] **Step 6: Run focused tests plus all G2/G3/G4 regressions**
- [ ] **Step 7: Commit `feat: add g5 environment metrics and support controllers`, push, and persist the verified hash**

### Task 7: Generate exact experiment families, configuration diffs, and the deduplicated 375-job graph

**Files:**
- Create: `src/problem2/experiments/identity.py`
- Create: `src/problem2/experiments/families.py`
- Create: `src/problem2/experiments/matrix.py`
- Create: `src/problem2/experiments/ablation.py`
- Create: `src/problem2/experiments/sensitivity.py`
- Create: `configs/problem2/g5/families.yaml`
- Create: `configs/problem2/g5/ablations.yaml`
- Create: `configs/problem2/g5/sensitivity.yaml`
- Create: `tests/g5/test_experiment_matrix.py`
- Create: `scripts/generate_g5_manifests.py`

**Interfaces:**
- `canonical_training_identity(method, scale, training_seed, config_hash, git_commit) -> str` preserves the G1 serialization and SHA-256 rule.
- `experiment_identity(family, condition_id, protocol_hash, canonical_training_identity) -> str` binds family references without changing canonical training identity.
- `build_training_graph(contract) -> TrainingGraph` yields raw family references and exactly `375` unique formal training jobs: `150 + 90 + 60 + 25 + 50`.
- The required Problem-2 IDs are exactly `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`, and `sr_mappo_two_stage`; additional heuristic IDs are exactly `sr_mappo_nearest` and `sr_mappo_urgency`.
- Remove-one IDs are exactly `no_observation_normalization`, `no_return_normalization`, `no_network_stabilization`, `no_robust_value_update`, and `no_learning_rate_decay`. `no_network_stabilization` jointly disables orthogonal initialization and layer normalization; `no_robust_value_update` jointly disables value clipping and Huber value loss.
- `validate_ablation_diff(full, variant)` permits exactly one declared remove-one group.
- `validate_sensitivity_diff(center, variant)` permits exactly one axis and one registered noncenter value.

- [ ] **Step 1: Write failing tests for exact six-scale/five-seed coverage, base count `150`, total count `375`, dependency references, unsafe dedup rejection, and deterministic manifest order/hash**
- [ ] **Step 2: Write failing tests for the five remove-one groups and five three-level algorithm/mechanism sensitivity axes, including center deduplication**
- [ ] **Step 3: Run the focused suite and confirm missing matrix APIs**
- [ ] **Step 4: Implement identity, family expansion, strict canonical deduplication, ablation, and one-factor sensitivity validation**
- [ ] **Step 5: Generate development/pilot manifests and unexecuted G6/G7 skeleton manifests below `outputs/problem2_sr_mappo_v1/g5/manifests` without including sealed scenario payloads**
- [ ] **Step 6: Run the generator twice and assert byte-identical output and exact counts**
- [ ] **Step 7: Commit `feat: generate frozen g5 experiment graph`, push, and persist the verified hash**

### Task 8: Implement append-only orchestration, artifact schemas, validation, recovery, and sealed lock guards

**Files:**
- Create: `src/problem2/experiments/ledger.py`
- Create: `src/problem2/experiments/orchestrator.py`
- Create: `src/problem2/experiments/recovery.py`
- Create: `src/problem2/experiments/artifacts.py`
- Create: `src/problem2/evaluation/schema.py`
- Create: `src/problem2/evaluation/validator.py`
- Create: `src/problem2/evaluation/sealed_lock.py`
- Create: `docs/evidence/g5/raw_episode_schema.yaml`
- Create: `docs/evidence/g5/validated_long_table_schema.yaml`
- Create: `docs/evidence/g5/artifact_manifest_schema.yaml`
- Create: `tests/g5/test_orchestration_and_validation.py`
- Create: `tests/g5/test_sealed_guards.py`
- Create: `scripts/run_g5_jobs.py`
- Create: `scripts/validate_g5_artifacts.py`
- Create: `scripts/preflight_g6.py`
- Create: `scripts/run_g6_jobs.py`
- Create: `scripts/resume_g6_jobs.py`
- Create: `scripts/preflight_g7.py`
- Create: `scripts/unlock_g7.py`
- Create: `scripts/run_g7_evaluation.py`

**Interfaces:**
- Job states are `pending -> running -> completed`, `running -> failed -> pending` for same-identity retry, and any hash/input drift -> `stale`; transitions are append-only with lease/attempt metadata.
- Validators reject duplicate identities, nonmonotonic counters, stale hashes, non-finite values, illegal actions, resource mismatch, wrong partitions, missing terminal rows, and incomplete expected cells.
- Quarantine retains original bytes, locator, reason, and source hash; rows are never silently deleted.
- `assert_partition_allowed(gate="G5", partition, scenario_id)` permits development and pre-authorized validation only and rejects every sealed ID/path/flag.
- G6/G7 preflight code is callable in dry-run mode during G5 but cannot mutate the sealed lock or execute sealed rows.
- G6 preflight verifies the exact frozen Git/remote hashes, registry hashes, G4 reconciliation, road-cache provenance, disk space for atomic writes, output confinement, hardware/runtime inventory, and absence of sealed identities before queue creation.
- The G6 scheduler deterministically interleaves method/seed/scale blocks, permits exactly one GPU training lease, and retains peak memory/runtime/environment records per attempt.
- `unlock_g7.py` requires a pushed G6 acceptance record, an exact pre-unlock audit, current gate `G7`, clean frozen source, and `actual_unlock_count: 0`; every condition is false during G5 tests, so mutation and sealed reads must be rejected.

- [ ] **Step 1: Write failing ledger tests for legal transitions, leases, duplicate workers, identical retry, stale drift, and append-only recovery**
- [ ] **Step 2: Write failing schema/validator tests using valid and corrupted hand-written JSONL fixtures**
- [ ] **Step 3: Write parameterized denial tests covering every public G5 CLI/function with IDs `30000`, `30099`, sealed paths, and truthy access flags**
- [ ] **Step 4: Run focused suites and confirm missing implementations**
- [ ] **Step 5: Implement orchestration, schema upgrades, artifact hashing, quarantine, recovery, and fail-closed lock guards**
- [ ] **Step 6: Implement thin G6/G7 CLI entry points and run focused tests plus G1-G4 regression, every CLI `--help`, G6 preflight failure fixtures, and G7 pre-unlock/unlock denial fixtures**
- [ ] **Step 7: Commit `feat: add g5 orchestration and evidence validation`, push, and persist the verified hash**

### Task 9: Implement convergence, paired statistics, Holm correction, equivalence, and mechanism summaries

**Files:**
- Create: `src/problem2/statistics/__init__.py`
- Create: `src/problem2/statistics/convergence.py`
- Create: `src/problem2/statistics/paired.py`
- Create: `src/problem2/statistics/multiplicity.py`
- Create: `src/problem2/statistics/equivalence.py`
- Create: `src/problem2/statistics/mechanism.py`
- Create: `src/problem2/statistics/diagnosis.py`
- Create: `tests/g5/test_statistics.py`
- Create: `scripts/analyze_g5_paired.py`
- Create: `scripts/analyze_g7.py`

**Interfaces:**
- `summarize_convergence(rows, budget, threshold=0.85)` uses the frozen checkpoint grid, trapezoidal normalized AUC, no interpolation, right-censored time-to-threshold, last-20-percent final window, and `0.10` catastrophic-regression threshold.
- `hierarchical_paired_bootstrap(rows, metric, B=10000, seed=20260822) -> PairedEstimate` resamples matched training seeds then shared scenarios.
- The unadjusted two-sided bootstrap tail probability uses the frozen plus-one formula; `holm_adjust(records)` operates separately per registered confirmatory family.
- `classify_equivalence(interval, margin)` returns only `equivalent`, `directional_positive`, `directional_negative`, or `inconclusive` using complete-interval rules.
- Mechanism summaries preserve road rendezvous, waiting, disabled time, effective spray time, reduction, and success as distinct directly logged measures.
- `diagnose_result_bundle(validated_rows, audit_records) -> DiagnosisReport` follows the frozen order: data/state correctness, mechanism activation, physical/engineering consistency, learnability, training/checkpoint behavior, comparator fairness, then genuine boundary/absence of effect. It never filters a seed, scenario, method, or metric.

- [ ] **Step 1: Write failing hand-computable fixtures for paired means, seed-level replication, scenario pairing, percentile intervals, plus-one tails, Holm ordering, and equivalence boundaries**
- [ ] **Step 2: Write failing convergence fixtures for AUC, observed threshold, censoring, final window, and regression count**
- [ ] **Step 3: Run `.venv-g5/Scripts/python.exe -m pytest tests/g5/test_statistics.py -q` and confirm missing-module failures**
- [ ] **Step 4: Implement pure deterministic statistics and negative-result diagnosis functions without reading raw unvalidated logs**
- [ ] **Step 5: Run the focused suite twice and assert byte-identical results for the fixed bootstrap seed**
- [ ] **Step 6: Commit `feat: freeze g5 paired statistics`, push, and persist the verified hash**

### Task 10: Run shared CPU/CUDA smoke acceptance for every method and condition type

**Files:**
- Create: `src/problem2/training/runner.py`
- Create: `src/problem2/training/preflight.py`
- Create: `tests/g5/test_end_to_end_smoke.py`
- Create: `scripts/run_g5_smoke.py`
- Generate: `outputs/problem2_sr_mappo_v1/g5/smoke/**`
- Generate: `outputs/problem2_sr_mappo_v1/g5/audits/smoke-audit.json`

**Interfaces:**
- `run_training_job(job, device, max_interactions, output_root)` uses the same collection/update/checkpoint/logging path intended for G6.
- CPU smoke runs every learning method and fixed/A*/nearest/urgency/two-stage/ablation/sensitivity condition type with bounded development IDs.
- CUDA preflight records device visibility, Torch/CUDA versions, GPU name, VRAM, deterministic flags, and rejects silent scientific config changes.
- GPU smoke runs one bounded job per learning family on the available RTX 4060 Laptop GPU and records peak allocated/reserved memory.

- [ ] **Step 1: Write failing end-to-end tests for finite updates, exact role shapes/masks, checkpoint reload, deterministic evaluation freeze, interruption/resume equivalence, and artifact validation for all five learning methods**
- [ ] **Step 2: Run the focused CPU suite and repair implementation defects without changing frozen scientific contracts**
- [ ] **Step 3: Run `.venv-g5/Scripts/python.exe scripts/run_g5_smoke.py --device cpu --interactions 128 --all-methods --all-condition-types` and validate every output**
- [ ] **Step 4: Run CUDA preflight and `.venv-g5/Scripts/python.exe scripts/run_g5_smoke.py --device cuda --interactions 128 --all-methods` one method at a time**
- [ ] **Step 5: If CUDA is unavailable or a method OOMs under the frozen smoke configuration, record a failed preflight/smoke and stop G5; do not reduce network, batch, replay, or horizon silently**
- [ ] **Step 6: Run all G5 tests, all prior-gate tests, compileall, and diff hygiene**
- [ ] **Step 7: Commit `test: record g5 algorithm smoke acceptance`, push, and persist the verified hash**

### Task 11: Run development pilots and freeze the validation candidate manifest

**Files:**
- Create: `src/problem2/training/pilot.py`
- Create: `src/problem2/training/budget.py`
- Create: `tests/g5/test_pilot_freeze.py`
- Create: `scripts/run_g5_pilots.py`
- Generate: `outputs/problem2_sr_mappo_v1/g5/pilots/**`
- Generate: `outputs/problem2_sr_mappo_v1/g5/validated/pilot-episodes.jsonl`
- Generate: `outputs/problem2_sr_mappo_v1/g5/audits/pilot-audit.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/manifests/validation-candidates.json`
- Modify: `configs/problem2/g5/protocol.yaml`
- Modify: `docs/evidence/g5/checkpoint_selection.yaml`

**Interfaces:**
- Development pilots cover `g20x20_d2` and `g30x50_d4`, seeds `51001-51003`, scenarios `10000-10019`, every learning method, and every condition type required to prove executable coverage.
- Runtime measurements are aggregated conservatively by method/scale; the frozen Task-2 budget rule emits one exact formal interaction budget and checkpoint interval before validation begins.
- `freeze_validation_candidates` writes four candidates per learning algorithm with content hashes, common validation scenarios, equal interactions, and the exact tie-break chain.

- [ ] **Step 1: Write failing tests that reject incomplete small/large scale coverage, missing seeds/scenarios, unequal interactions, mutable candidate files, and a budget decision outside the frozen rule**
- [ ] **Step 2: Run the focused tests and confirm the pilot/freezer APIs are absent**
- [ ] **Step 3: Implement pilot orchestration and budget-rule evaluation**
- [ ] **Step 4: Run the full development pilot matrix, preserving failed/negative runs and stopping at the first contract or data-integrity failure**
- [ ] **Step 5: Validate raw artifacts, generate the pilot long table and audit, and run descriptive summaries only; do not claim formal ranking**
- [ ] **Step 6: Freeze and hash the exact budget, checkpoint interval, four candidates per algorithm, validation scenario panel, and selection rule before any validation access**
- [ ] **Step 7: Commit `docs: freeze g5 validation candidates`, push, verify the remote hash, and record the freeze in project state**

### Task 12: Run equal-budget validation tuning, refit development pilots, and freeze G6/G7 manifests

**Files:**
- Create: `src/problem2/training/tuning.py`
- Create: `src/problem2/training/selection.py`
- Create: `tests/g5/test_validation_tuning.py`
- Create: `scripts/run_g5_validation_tuning.py`
- Create: `scripts/freeze_g5.py`
- Generate: `outputs/problem2_sr_mappo_v1/g5/validation/**`
- Generate: `outputs/problem2_sr_mappo_v1/g5/validated/validation-episodes.jsonl`
- Generate: `outputs/problem2_sr_mappo_v1/g5/manifests/g6-training-jobs.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/manifests/g6-validation-evaluations.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/manifests/g7-sealed-evaluations.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/manifests/g7-analysis.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/freeze-manifest.json`
- Generate: `outputs/problem2_sr_mappo_v1/g5/audits/negative-result-diagnosis.json`
- Create: `docs/audits/g5-pilot-freeze-compliance.md`
- Modify: `HANDOFFG5.md`
- Modify: `docs/PROJECT_STATE.md`

**Interfaces:**
- Validation tuning evaluates only the pre-hashed candidates on `20000-20049` with equal interactions and selects by the frozen rule; candidate generation and edits are disabled after the first validation row.
- Selected configurations rerun on the same complete development pilot matrix before final freeze.
- The G6 manifest has exactly `150` base and `375` total unique training jobs.
- The G7 sealed manifest contains scenario identities/hashes and exactly `42,500` expected evaluation identities but no scenario content and no evaluation result.
- `freeze_g5` verifies source cleanliness, remote commit parity, all contract/artifact hashes, full matrix coverage, statistics contract, sealed lock `maximum=1/actual=0`, and protected-asset preservation.

- [ ] **Step 1: Write failing tests for candidate immutability after first validation access, equal budgets, selection tie-breaks, exact G6/G7 counts, missing hash rejection, and zero sealed access**
- [ ] **Step 2: Run the focused tests and confirm missing tuning/freeze APIs**
- [ ] **Step 3: Implement validation-only tuning and selected-configuration recording**
- [ ] **Step 4: Run all frozen candidates on validation scenarios, select each algorithm configuration mechanically, and retain all candidate results including unfavorable ones**
- [ ] **Step 5: Rerun selected configurations on the full development pilot matrix and validate the complete evidence chain**
- [ ] **Step 6: Generate and audit the G6/G7 manifests, exact counts, hashes, dependency graph, checkpoint-selection records, exclusions, and statistical contracts without opening sealed scenarios**
- [ ] **Step 7: Run fresh final verification**

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5 -q
.venv-g5/Scripts/python.exe -m pytest -q
.venv-g5/Scripts/python.exe -m compileall -q src scripts
.venv-g5/Scripts/python.exe scripts/audit_g5_contracts.py
.venv-g5/Scripts/python.exe scripts/validate_g5_artifacts.py --output-root outputs/problem2_sr_mappo_v1/g5
.venv-g5/Scripts/python.exe scripts/freeze_g5.py --check-only
git diff --check
```

- [ ] **Step 8: Write the G5 compliance report and update `HANDOFFG5.md` and `docs/PROJECT_STATE.md` with the highest maturity actually supported, exact tests, pilot boundaries, hashes, unresolved external evidence, and permitted claims**
- [ ] **Step 9: Commit and push the G5 content freeze**

```powershell
git add src/problem2 configs/problem2/g5 docs/evidence/g5 tests/g5 scripts outputs/problem2_sr_mappo_v1/g5 docs/audits/g5-pilot-freeze-compliance.md HANDOFFG5.md docs/PROJECT_STATE.md
git commit -m "feat: freeze g5 fair-pilot experiment system"
git push origin codex/problem2-g5-pilot-freeze
```

- [ ] **Step 10: Rerun final verification on the content commit, record its pushed hash in `docs/PROJECT_STATE.md`, commit `docs: record g5 freeze persistence`, push, and verify local HEAD, upstream HEAD, and remote branch head agree**
- [ ] **Step 11: Mark G5 passed only if every acceptance item is satisfied; otherwise record the first failed gate and keep G6 unauthorized**

## Plan Self-Review Checklist

- [x] Every G5 design requirement maps to a task above.
- [x] G6 training, resume, validation, and checkpoint-selection executables are implemented and tested in G5 but never run as formal jobs in G5.
- [x] G7 lock, evaluation, validation, bootstrap, Holm, mechanism, ablation, and sensitivity executables are implemented and tested in G5 but sealed data remain unread.
- [x] The five learning algorithms explicitly implement UAV and vehicle roles.
- [x] The required Problem-2 family, three heuristic controllers, five remove-one groups, and both sensitivity classes are covered.
- [x] The `375` training-job and `42,500` sealed-row design counts are generated and fail-closed audited.
- [x] All formula notation, units, paths, names, seeds, hashes, and maturity wording remain consistent.
- [x] No task authorizes protected external writes, formal conclusions, or sealed access.
