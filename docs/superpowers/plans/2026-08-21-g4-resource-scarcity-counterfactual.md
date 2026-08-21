# G4 Resource-Scarcity Activation and Counterfactual Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze and verify the G4 scarcity band, run fixed-versus-mobile counterfactual probes on the frozen G2 physical foundation with the frozen G3 learning interface, and persist a fail-closed G4 evidence bundle without reusing G3 smoke as endpoint evidence.

**Architecture:** Add a small `src/problem2/experiments/` package that owns the G4 contract, probe manifest, support-policy wrappers, activation runner, paired counterfactual summaries, and audit report generation. Reuse the frozen G2 simulation engine, G2 service/resource semantics, and G3 observation/mask interfaces rather than forking new environment logic. G4 records descriptive paired deltas only; it does not freeze formal pilot statistics or sealed-test evidence.

**Tech Stack:** Python 3.11, NumPy, PyYAML, PyTorch `2.13.0+cpu`, pytest, existing `problem2` G2/G3 modules, existing `scripts/` CLI pattern, JSONL/JSON/YAML artifacts.

**Spec:** `docs/superpowers/specs/2026-08-21-g4-resource-scarcity-counterfactual-design.md`

## Global Constraints

- Public algorithm name is `SR-MAPPO`; do not introduce HAPPO or `AG-SR-MAPPO`.
- Problem 2 remains the air-ground heterogeneous extension of `SR-MAPPO`.
- Pesticide is the only replenished resource; battery replenishment stays inactive.
- G2 physical motion, service, and conservation semantics remain frozen.
- G3 learning-interface dimensions, masks, and replay contracts remain frozen.
- G4 must begin with resource-scarcity activation and counterfactual probes.
- The recommended implementation branch is `codex/problem2-g4-resource-scarcity` or an equivalent dedicated worktree created from the current clean head.
- Validation tuning, sealed-test access, and formal paired claims remain unauthorized.
- G3 smoke outputs may be read only as lineage inputs; they may not appear as G4 endpoint evidence.
- All G4 outputs must live under `outputs/problem2_sr_mappo_v1/g4`.
- The G4 activation band must be fail-closed; no open-ended sweep or hidden tuning is allowed after the band is frozen.

---

### Task 1: Freeze the G4 contract, probe manifest, and guardrails

**Files:**
- Create: `docs/superpowers/specs/2026-08-21-g4-resource-scarcity-counterfactual-design.md`
- Create: `docs/evidence/g4/g4_contract.yaml`
- Create: `docs/evidence/g4/g4_probe_manifest.yaml`
- Create: `src/problem2/experiments/__init__.py`
- Create: `src/problem2/experiments/g4_contract.py`
- Create: `tests/g4/test_g4_contract.py`

**Interfaces:**
- `load_g4_contract(path) -> G4Contract`
- `load_g4_probe_manifest(path) -> G4ProbeManifest`
- `G4Contract` exposes the scarcity axis, admissible band, frozen probe scales, frozen probe seeds, comparator pair, output root, and permitted-claim boundary.
- `G4ProbeManifest` exposes the exact probe scale/seed subset and the no-validation/no-sealed flags.

- [ ] **Step 1: Write failing tests that reject the three most likely failures**

```python
def test_g4_contract_rejects_g3_endpoint_evidence_paths() -> None:
    ...

def test_g4_contract_rejects_unbounded_scarcity_ranges() -> None:
    ...

def test_g4_contract_rejects_validation_and_sealed_probe_ids() -> None:
    ...
```

- [ ] **Step 2: Run the contract tests and confirm they fail because the loader does not exist yet**

Run: `python -m pytest tests/g4/test_g4_contract.py -q`

Expected: import or attribute failures for the new G4 contract loader.

- [ ] **Step 3: Implement the frozen contract and manifest with explicit fail-closed checks**

The contract must bind the scarcity axis, the active band, the probe scale
subset, the probe seed subset, the fixed-versus-mobile comparator pair, and the
canonical output root. The loader must reject any reference to validation or
sealed seeds, any battery activation truthy value, any G3 output-root path as
endpoint evidence, and any scarcity band with missing lower/upper bounds.

- [ ] **Step 4: Re-run the contract tests**

Run: `python -m pytest tests/g4/test_g4_contract.py -q`

Expected: all focused contract tests pass.

- [ ] **Step 5: Commit the frozen G4 contract**

```powershell
git add docs/superpowers/specs/2026-08-21-g4-resource-scarcity-counterfactual-design.md docs/evidence/g4/g4_contract.yaml docs/evidence/g4/g4_probe_manifest.yaml src/problem2/experiments/__init__.py src/problem2/experiments/g4_contract.py tests/g4/test_g4_contract.py
git commit -m "feat: freeze g4 scarcity contract and probe manifest"
```

### Task 2: Implement the resource-scarcity activation probe on the frozen G2 engine

**Files:**
- Create: `src/problem2/experiments/g4_support.py`
- Create: `src/problem2/experiments/g4_activation.py`
- Create: `scripts/run_g4_mechanism_probe.py`
- Create: `tests/g4/test_g4_activation.py`

**Interfaces:**
- `FixedSupportPolicy.choose_vehicle_action(...) -> Action`
- `MobileSupportPolicy.choose_vehicle_action(...) -> Action`
- `run_activation_probe(contract, manifest, *, support_policy, output_root) -> dict[str, Any]`
- `run_probe_matrix(contract, manifest, *, output_root) -> dict[str, Any]`
- Activation records must include `scarcity_active`, `activation_window`, `request_count`, `reservation_count`, `service_count`, `waiting_time_s`, `rendezvous_distance_m`, `pesticide_disabled_time_s`, `sprayed_volume_l`, `conservation_error_l`, and lineage fields.

- [ ] **Step 1: Write failing tests for activation behavior on the frozen probe set**

```python
def test_activation_probe_records_a_fail_closed_scarcity_band() -> None:
    ...

def test_activation_probe_rejects_validation_and_sealed_access() -> None:
    ...

def test_activation_probe_uses_the_same_inputs_for_each_counterfactual_arm() -> None:
    ...
```

- [ ] **Step 2: Run the activation tests and verify they fail because the probe runner does not exist yet**

Run: `python -m pytest tests/g4/test_g4_activation.py -q`

Expected: missing-module or missing-function failures.

- [ ] **Step 3: Implement the probe runner on top of `problem2.simulation.engine`**

Reuse `build_action_masks`, `estimate_service_delay_s`, and `step_episode` so
the G4 probe is built on the frozen G2 transactional physics rather than a
parallel simulation path. The runner must keep the same scenario/seed inputs
for the fixed and mobile arms and must stop immediately if a probe would touch
validation or sealed data.

- [ ] **Step 4: Add the support-policy wrappers and raw JSONL probe log**

The fixed policy must keep the vehicle stationary at the contract-defined
support location. The mobile policy must follow the road-constrained support
logic frozen in the probe manifest. Both arms must write a raw JSONL probe log
and a provenance file under the G4 output root.

- [ ] **Step 5: Re-run the activation tests**

Run: `python -m pytest tests/g4/test_g4_activation.py -q`

Expected: the activation probe passes, the band is recorded, and the guardrail
tests remain fail-closed for invalid inputs.

- [ ] **Step 6: Commit the activation probe implementation**

```powershell
git add src/problem2/experiments/g4_support.py src/problem2/experiments/g4_activation.py scripts/run_g4_mechanism_probe.py tests/g4/test_g4_activation.py
git commit -m "feat: add g4 scarcity activation probe"
```

### Task 3: Implement the fixed-versus-mobile counterfactual summary and audit

**Files:**
- Create: `src/problem2/experiments/g4_counterfactual.py`
- Create: `src/problem2/experiments/g4_audit.py`
- Create: `scripts/audit_g4_mechanism.py`
- Create: `tests/g4/test_g4_audit.py`

**Interfaces:**
- `run_counterfactual_probe(...) -> dict[str, Any]`
- `build_g4_artifact_manifest(...) -> dict[str, Any]`
- `audit_g4_mechanism(config_path, output_root, report_path) -> dict[str, Any]`
- The audit report must include the frozen contract hash, activation band, paired deltas, output artifact hashes, and a hard boundary section that keeps validation, sealed-test, and battery activation false.

- [ ] **Step 1: Write failing tests for counterfactual pairing and audit rejection**

```python
def test_counterfactual_probe_uses_identical_probe_inputs() -> None:
    ...

def test_g4_audit_rejects_g3_smoke_artifacts_as_endpoint_evidence() -> None:
    ...

def test_g4_audit_rejects_validation_or_sealed_access_flags() -> None:
    ...
```

- [ ] **Step 2: Run the audit tests and confirm they fail before the new audit exists**

Run: `python -m pytest tests/g4/test_g4_audit.py -q`

Expected: missing audit runner failures.

- [ ] **Step 3: Implement the paired counterfactual summary**

Record the same-seed, same-scale, same-budget comparison for
`sr_mappo_mobile` versus `sr_mappo_fixed`. The summary must stay descriptive:
paired deltas, activation counts, waiting-time reduction, rendezvous-distance
change, and conservation error only. Do not add formal significance claims.

- [ ] **Step 4: Implement the fail-closed audit and artifact manifest**

The audit must reject any artifact path under `outputs/problem2_sr_mappo_v1/g3`
as endpoint evidence, reject any validation or sealed access, reject battery
activation, and verify that every G4 output hash matches the recorded manifest.

- [ ] **Step 5: Run the full G4 focused suite**

Run:

```powershell
python -m pytest tests/g4 -q
python -m compileall -q src scripts
git diff --check
```

Expected: all focused G4 tests pass, the code compiles, and the worktree is
clean apart from intended G4 files.

- [ ] **Step 6: Commit the G4 audit bundle**

```powershell
git add src/problem2/experiments/g4_counterfactual.py src/problem2/experiments/g4_audit.py scripts/audit_g4_mechanism.py tests/g4/test_g4_audit.py
git commit -m "feat: add g4 counterfactual audit bundle"
```

### Task 4: Persist the G4 handoff and update project state

**Files:**
- Create: `docs/audits/g4-mechanism-compliance.md`
- Create: `HANDOFFG4.md`
- Modify: `docs/PROJECT_STATE.md`
- Create: `outputs/problem2_sr_mappo_v1/g4/activation-summary.json`
- Create: `outputs/problem2_sr_mappo_v1/g4/counterfactual-summary.json`
- Create: `outputs/problem2_sr_mappo_v1/g4/provenance.json`
- Create: `outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`
- Create: `outputs/problem2_sr_mappo_v1/g4/artifact-manifest.json`

**Interfaces:**
- `HANDOFFG4.md` records the gate result, permitted G4 claim, frozen interface,
  verified evidence, protected boundaries, and the exact G5 entry condition.
- `docs/PROJECT_STATE.md` records the pushed content hash, verification
  commands, result, and next authorized gate.

- [ ] **Step 1: Run the complete fresh verification after the content commit**

Run:

```powershell
python -m pytest tests/g4 -q
python -m pytest -q
python -m compileall -q src scripts
git diff --check
```

- [ ] **Step 2: Push the G4 content branch to `origin`**

Use the repository's standard non-rewriting push flow. Do not force-push.

- [ ] **Step 3: Record the pushed content hash in `docs/PROJECT_STATE.md`**

The project state must name the exact pushed hash, the verification command
set, the fresh result, the output root, and the next gate.

- [ ] **Step 4: Create and push a separate persistence-record commit**

The persistence record must confirm that the remote hash, upstream hash, and
local HEAD match the G4 content commit.

- [ ] **Step 5: Verify local HEAD, upstream HEAD, and `git ls-remote` agree**

Run:

```powershell
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/codex/problem2-g4-resource-scarcity
```

Expected: all three commands resolve to the same pushed content hash.

- [ ] **Step 6: Commit the handoff and state record**

```powershell
git add docs/audits/g4-mechanism-compliance.md HANDOFFG4.md docs/PROJECT_STATE.md outputs/problem2_sr_mappo_v1/g4
git commit -m "docs: record g4 mechanism activation handoff"
```

## Self-Review

- Spec coverage: contract freeze, activation band, counterfactual pair, G4
  outputs, and acceptance are all mapped to tasks.
- Placeholder scan: no `TBD`, `TODO`, or deferred implementation language was
  used.
- Type consistency: the plan uses one naming set throughout -
  `load_g4_contract`, `run_activation_probe`, `run_counterfactual_probe`, and
  `audit_g4_mechanism`.
- Guardrail coverage: the three highest-risk failures are explicitly tested -
  G3 evidence reuse, unbounded scarcity band, and validation/sealed leakage.
