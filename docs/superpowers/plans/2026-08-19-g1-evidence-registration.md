# G1 Evidence Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish and verify the G1 evidence registries, independently audit the existing candidate code branch, and persist the G1 result without advancing beyond M1.

**Architecture:** Store the frozen G1 contracts as small YAML registries under `docs/evidence/g1/`. A fail-closed Python validator will parse those files, enforce cross-registry invariants, construct immutable job identities, and emit a JSON report. A separate read-only Git audit script will inventory the candidate branch and generate a Markdown classification report; project-state updates will record only the verified current branch result.

**Tech Stack:** Python 3.11+, PyYAML 6.x, pytest, Git command-line object inspection, YAML/Markdown/JSON evidence files.

**Spec:** `docs/superpowers/specs/2026-08-19-g1-evidence-registration-design.md`

## Global Constraints

- Public algorithm name remains `SR-MAPPO`.
- Problem 2 remains an air-ground heterogeneous extension of SR-MAPPO.
- HAPPO and `AG-SR-MAPPO` are forbidden identifiers.
- The replenished resource is pesticide only; battery replenishment remains inactive.
- OSM inputs are simulation inputs, not field-deployment evidence.
- Current maturity remains M1.
- Sealed-test scenario seeds `30000-30099` remain locked and unavailable for tuning.
- No training, deterministic G2 validation, formal evaluation, or sealed-test execution is allowed in G1.
- All second-problem outputs remain below `outputs/problem2_sr_mappo_v1`.
- Protected first-problem files and external OSM source files remain untouched.
- Every important phase requires fresh verification, a non-rewriting commit, a push, and a `docs/PROJECT_STATE.md` record.

---

### Task 1: Add the machine-readable G1 registries

**Files:**
- Create: `docs/evidence/g1/parameter_registry.yaml`
- Create: `docs/evidence/g1/literature_source_ledger.yaml`
- Create: `docs/evidence/g1/experiment_matrix.yaml`
- Create: `docs/evidence/g1/scenario_seed_manifest.yaml`
- Create: `docs/evidence/g1/job_identity_contract.yaml`
- Create: `docs/evidence/g1/raw_episode_schema.yaml`
- Create: `docs/evidence/g1/validated_long_table_schema.yaml`
- Create: `docs/evidence/g1/artifact_manifest_schema.yaml`
- Create: `docs/evidence/g1/sealed_test_lock.yaml`
- Create: `docs/evidence/g1/output_root_contract.yaml`
- Test: `tests/test_g1_registries.py`

**Interfaces:**
- Produces YAML documents consumed by `scripts/audit_g1_registries.py`.
- Every registry has a top-level `schema_version`, `registry_id`, and
  `status: design_frozen`.
- The parameter registry exposes `parameters`; the source ledger exposes
  `sources`; the experiment matrix exposes `methods`, `scales`, and
  `evaluation`; the scenario manifest exposes `partitions`.
- The job contract exposes `identity_fields` in this exact order:
  `method`, `scale`, `training_seed`, `config_hash`, `git_commit`.
- The sealed lock exposes `status: locked`, `unlock_gate: G7`, and
  `unlock_count: 1`.

- [ ] **Step 1: Write the failing registry-structure tests**

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = ROOT / "docs" / "evidence" / "g1"
REGISTRY_NAMES = (
    "parameter_registry.yaml",
    "literature_source_ledger.yaml",
    "experiment_matrix.yaml",
    "scenario_seed_manifest.yaml",
    "job_identity_contract.yaml",
    "raw_episode_schema.yaml",
    "validated_long_table_schema.yaml",
    "artifact_manifest_schema.yaml",
    "sealed_test_lock.yaml",
    "output_root_contract.yaml",
)


def load(name: str) -> dict:
    with (REGISTRY_ROOT / name).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    assert isinstance(value, dict)
    return value


def test_all_g1_registries_exist_and_are_frozen() -> None:
    for name in REGISTRY_NAMES:
        registry = load(name)
        assert registry["schema_version"] == "g1.v1"
        assert registry["registry_id"].startswith("G1-")
        assert registry["status"] == "design_frozen"


def test_primary_method_family_and_scale_protocol_are_complete() -> None:
    matrix = load("experiment_matrix.yaml")
    assert matrix["methods"] == [
        "sr_mappo_mobile",
        "sr_mappo_fixed",
        "sr_mappo_astar",
        "mappo_mobile",
        "sr_mappo_two_stage",
    ]
    assert matrix["scales"]["g30x50_d4"]["max_physical_decision_steps"] == 350


def test_seed_partitions_do_not_overlap() -> None:
    manifest = load("scenario_seed_manifest.yaml")
    partitions = manifest["partitions"]
    training = set(partitions["training"]["seeds"])
    validation = set(range(partitions["validation"]["start"], partitions["validation"]["end"] + 1))
    sealed = set(range(partitions["sealed_test"]["start"], partitions["sealed_test"]["end"] + 1))
    assert not training & validation
    assert not training & sealed
    assert not validation & sealed


def test_sealed_test_is_locked_once_at_g7() -> None:
    lock = load("sealed_test_lock.yaml")
    assert lock["status"] == "locked"
    assert lock["unlock_gate"] == "G7"
    assert lock["unlock_count"] == 1
    assert lock["tuning_allowed_before_unlock"] is False
```

- [ ] **Step 2: Run the focused tests and verify they fail for missing registries**

Run:

```powershell
python -m pytest tests/test_g1_registries.py -q
```

Expected: FAIL because the ten registry files do not yet exist.

- [ ] **Step 3: Add the parameter and source ledgers**

`parameter_registry.yaml` must include at least these IDs:

```yaml
schema_version: g1.v1
registry_id: G1-PARAMETERS
status: design_frozen
parameters:
  - id: uav.pesticide_capacity
    name: onboard_pesticide_capacity
    symbol: C_uav
    meaning: Nominal onboard pesticide capacity
    value: 1.2
    unit: L
    min: 0.8
    max: 1.6
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 1.2
    source_unit: L
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: uav.usable_fraction
    name: usable_pesticide_fraction
    symbol: f_uav
    meaning: Fraction of nominal onboard pesticide available to the policy
    value: 0.9
    unit: "1"
    min: 0.7
    max: 1.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 0.9
    source_unit: "1"
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: uav.spray_flow
    name: spray_flow
    symbol: q_spray
    meaning: Pesticide spray flow
    value: 1.2
    unit: L/min
    min: 0.6
    max: 2.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 1.2
    source_unit: L/min
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: uav.speed
    name: uav_speed
    symbol: v_uav
    meaning: UAV translational speed
    value: 5.0
    unit: m/s
    min: 3.0
    max: 8.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 5.0
    source_unit: m/s
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: vehicle.inventory
    name: vehicle_pesticide_inventory
    symbol: C_vehicle
    meaning: Initial mobile support pesticide inventory
    value: 20.0
    unit: L
    min: 10.0
    max: 40.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 20.0
    source_unit: L
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: vehicle.speed
    name: vehicle_speed
    symbol: v_vehicle
    meaning: Road-constrained vehicle speed
    value: 8.0
    unit: m/s
    min: 4.0
    max: 12.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 8.0
    source_unit: m/s
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: vehicle.transfer_rate
    name: pesticide_transfer_rate
    symbol: q_transfer
    meaning: Transfer flow during a service event
    value: 4.0
    unit: L/min
    min: 2.0
    max: 8.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 4.0
    source_unit: L/min
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: service.setup_time
    name: service_setup_time
    symbol: t_setup
    meaning: Fixed setup time before transfer
    value: 10.0
    unit: s
    min: 5.0
    max: 30.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 10.0
    source_unit: s
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: service.rendezvous_radius
    name: rendezvous_radius
    symbol: r_service
    meaning: Maximum air-ground service rendezvous distance
    value: 15.0
    unit: m
    min: 5.0
    max: 30.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 15.0
    source_unit: m
    conversion: identity
    status: provisional
    scope: development_and_pilot
  - id: simulation.dt
    name: physical_decision_step
    symbol: Delta_t
    meaning: Physical duration represented by one decision step
    value: 1.0
    unit: s
    min: 0.5
    max: 2.0
    source_type: assumption
    source_id: SRC-ASSUMPTION-001
    source_value: 1.0
    source_unit: s
    conversion: identity
    status: provisional
    scope: all_simulation
```

`literature_source_ledger.yaml` must define `SRC-ASSUMPTION-001` as an internal
design record and include pending records for each source family not verified
in G1. No pending record may be used as a verified parameter source.

- [ ] **Step 4: Add experiment and seed manifests**

The matrix must encode the six scales and horizons exactly:

```yaml
scales:
  g20x20_d2: {max_physical_decision_steps: 150}
  g20x30_d3: {max_physical_decision_steps: 180}
  g20x40_d3: {max_physical_decision_steps: 220}
  g30x30_d3: {max_physical_decision_steps: 220}
  g30x40_d4: {max_physical_decision_steps: 280}
  g30x50_d4: {max_physical_decision_steps: 350}
```

The evaluation block must identify `reduction_rate` and
`success_at_0_85` as primary outcomes, and must identify rendezvous distance,
waiting/disabled/return steps, effective spray time, transferred pesticide,
vehicle travel/idle time, stranded inventory, and decision runtime as
mechanism or operational metrics.

- [ ] **Step 5: Add job, raw-log, table, and artifact schemas**

The job contract must list the identity fields and state values. The raw-log
schema must list every key required by the evidence chain:
`run_id`, `method`, `scale`, `training_seed`, `scenario_id`,
`config_hash`, `git_commit`, `termination_reason`, `reduction_rate`,
`success_at_0_85`, `request_count`, `request_completed_count`,
`waiting_steps`, `pesticide_disabled_steps`, `return_steps`,
`effective_spray_steps`, `transferred_pesticide_l`, `vehicle_travel_steps`,
`vehicle_idle_steps`, and `vehicle_stranded_inventory_l`.

The validated-table schema must add `validation_status` and
`source_row_reference`. The artifact schema must require artifact ID, type,
source paths/hashes, generator, generator commit, output path, and data status.

- [ ] **Step 6: Add the lock and output-root contracts**

`sealed_test_lock.yaml` must record:

```yaml
schema_version: g1.v1
registry_id: G1-SEALED-TEST
status: locked
scenario_range: {start: 30000, end: 30099}
unlock_gate: G7
unlock_count: 1
tuning_allowed_before_unlock: false
```

`output_root_contract.yaml` must set
`root: outputs/problem2_sr_mappo_v1`, mark first-problem roots as forbidden,
and require source hash, CRS/bbox, grid shape, topology checksum, and code
version for derived road caches.

- [ ] **Step 7: Run the focused tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_g1_registries.py -q
```

Expected: PASS with all registry structure tests green.

- [ ] **Step 8: Commit the registry fixtures**

```powershell
git add docs/evidence/g1 tests/test_g1_registries.py
git commit -m "docs: register g1 evidence contracts"
```

### Task 2: Implement the fail-closed registry validator

**Files:**
- Create: `scripts/audit_g1_registries.py`
- Modify: `tests/test_g1_registries.py`

**Interfaces:**
- `load_yaml(path: Path) -> object`
- `build_job_identity(method: str, scale: str, training_seed: int, config_hash: str, git_commit: str) -> str`
- `validate_registries(registry_root: Path) -> dict`
- `main(argv: Sequence[str] | None = None) -> int`
- CLI: `python scripts/audit_g1_registries.py --root docs/evidence/g1 --report outputs/problem2_sr_mappo_v1/g1/registry-audit.json`

- [ ] **Step 1: Add failing validator tests**

```python
import shutil
from pathlib import Path

import copy
import json
import yaml

from scripts.audit_g1_registries import build_job_identity, validate_registries


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = ROOT / "docs" / "evidence" / "g1"


def copy_registry_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "g1"
    shutil.copytree(REGISTRY_ROOT, destination)
    return destination


def test_job_identity_is_canonical_and_ordered() -> None:
    assert build_job_identity(
        "sr_mappo_mobile", "g20x20_d2", 42, "abc123", "deadbeef"
    ) == "sr_mappo_mobile|g20x20_d2|42|abc123|deadbeef"


def test_validator_accepts_frozen_g1_registries() -> None:
    result = validate_registries(REGISTRY_ROOT)
    assert result["status"] == "pass"
    assert result["errors"] == []


def test_validator_rejects_forbidden_algorithm_name(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "experiment_matrix.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["methods"].append("happpo")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert any("forbidden algorithm" in error for error in result["errors"])


def test_validator_rejects_sealed_test_tuning(tmp_path) -> None:
    candidate = copy_registry_tree(tmp_path)
    path = candidate / "sealed_test_lock.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["tuning_allowed_before_unlock"] = True
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = validate_registries(candidate)
    assert any("sealed-test tuning" in error for error in result["errors"])
```

- [ ] **Step 2: Run the validator tests to verify the interface fails**

Run:

```powershell
python -m pytest tests/test_g1_registries.py -q
```

Expected: FAIL with an import error because
`scripts/audit_g1_registries.py` is not present.

- [ ] **Step 3: Implement YAML loading, identity construction, and validation**

The validator must:

1. Load all ten named registries with `yaml.safe_load`.
2. Reject missing files, non-mapping roots, wrong schema versions, missing
   `design_frozen` status, duplicate parameter/source/method IDs, and missing
   required fields.
3. Enforce the exact primary method family and six scale horizons.
4. Enforce training/validation/sealed partition disjointness and the exact
   seed ranges.
5. Enforce pesticide-only replenishment and reject battery activation.
6. Reject `HAPPO`, `happpo`, `AG-SR-MAPPO`, and other renamed public algorithms
   in registry text.
7. Reject formal-result or M3/M4 claim wording in G1 registry text.
8. Enforce `outputs/problem2_sr_mappo_v1` as the output root.
9. Enforce the sealed lock fields and one-time G7 unlock policy.
10. Return a JSON-serializable report with `status`, `errors`, `warnings`,
    `checked_files`, and `counts`.

```python
def build_job_identity(
    method: str,
    scale: str,
    training_seed: int,
    config_hash: str,
    git_commit: str,
) -> str:
    values = (method, scale, str(training_seed), config_hash, git_commit)
    if any("|" in value for value in values):
        raise ValueError("job identity fields cannot contain '|'" )
    return "|".join(values)
```

- [ ] **Step 4: Run focused validator tests and inspect the JSON report**

Run:

```powershell
python -m pytest tests/test_g1_registries.py -q
python scripts/audit_g1_registries.py --root docs/evidence/g1 --report outputs/problem2_sr_mappo_v1/g1/registry-audit.json
Get-Content -Raw outputs/problem2_sr_mappo_v1/g1/registry-audit.json
```

Expected: tests PASS and the report has `"status": "pass"` with no errors.

- [ ] **Step 5: Commit the validator**

```powershell
git add scripts/audit_g1_registries.py tests/test_g1_registries.py
git commit -m "test: validate g1 evidence registries"
```

### Task 3: Audit the remote candidate branch and record classifications

**Files:**
- Create: `scripts/audit_g1_feature_branch.py`
- Create: `docs/audits/g1-feature-branch-audit.md`
- Create: `outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json`
- Test: `tests/test_g1_feature_branch_audit.py`

**Interfaces:**
- `run_git(args: Sequence[str]) -> str`
- `classify_path(path: str) -> str`
- `audit_candidate_branch(base: str, candidate: str) -> dict`
- CLI: `python scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown docs/audits/g1-feature-branch-audit.md --json outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json`

- [ ] **Step 1: Write tests for read-only audit output**

```python
from scripts.audit_g1_feature_branch import audit_candidate_branch, classify_path


def test_candidate_path_classes_are_stable() -> None:
    assert classify_path("src/problem2/environment/air_ground_env.py") == "source"
    assert classify_path("configs/formal_matrix.yaml") == "configuration"
    assert classify_path("tests/marl/test_masks_and_gae.py") == "test"
    assert classify_path("docs/verification/formal-readiness-final.json") == "report"
    assert classify_path("artifacts/figures/chapter4/fig4-1_air_ground_system.png") == "artifact"
    assert classify_path("README.md") == "documentation"


def test_audit_does_not_report_a_maturity_gate_as_currently_passed() -> None:
    report = audit_candidate_branch(
        "origin/main", "origin/feature/problem2-code-framework"
    )
    assert report["current_branch_maturity"] == "M1"
    assert report["current_gate"] == "G1"
    assert report["read_only"] is True
```

- [ ] **Step 2: Run the audit tests before implementation**

Run:

```powershell
python -m pytest tests/test_g1_feature_branch_audit.py -q
```

Expected: FAIL because the audit module is not present.

- [ ] **Step 3: Implement Git-object-only inspection**

The script must call `git rev-parse`, `git diff --name-status`, `git ls-tree`,
and bounded `git grep` through `subprocess.run(..., check=True, text=True,
capture_output=True)`. It must not checkout, merge, cherry-pick, write to the
candidate branch, or execute candidate training commands.

The JSON report must record:

- base and candidate refs and resolved commit IDs;
- changed-path counts and class counts;
- candidate directories for configs, source, tests, reports, and outputs;
- detected maturity words and forbidden names;
- commands used and their return status;
- classifications for candidate assets;
- `read_only: true`, `current_branch_maturity: M1`, and `current_gate: G1`.

- [ ] **Step 4: Generate and manually complete the Markdown audit**

Run:

```powershell
python scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown docs/audits/g1-feature-branch-audit.md --json outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json
```

The Markdown report must include the resolved candidate commit
`52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`, the audited base, exact commands,
asset classifications, and the following explicit conclusion:

> Candidate-branch assets are design or candidate implementation inputs only;
> no M2/M3/M4 claim is accepted in the current G1 branch without fresh,
> branch-local verification.

- [ ] **Step 5: Run audit tests and check the report for protected boundaries**

Run:

```powershell
python -m pytest tests/test_g1_feature_branch_audit.py -q
rg -n "M1|G1|read.only|read-only|52a92c0|HAPPO|AG-SR-MAPPO|sealed|training" docs/audits/g1-feature-branch-audit.md
```

Expected: PASS; the report must state read-only inspection, current M1/G1
status, sealed-test protection, and no training execution.

- [ ] **Step 6: Commit the candidate-branch audit**

```powershell
git add scripts/audit_g1_feature_branch.py tests/test_g1_feature_branch_audit.py docs/audits/g1-feature-branch-audit.md outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json
git commit -m "audit: classify problem2 candidate branch for g1"
```

### Task 4: Run the complete G1 verification and persist project state

**Files:**
- Modify: `docs/PROJECT_STATE.md`
- Create: `outputs/problem2_sr_mappo_v1/g1/registry-audit.json`
- Create: `outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json`

**Interfaces:**
- Consumes the ten registries, validator report, candidate audit report, and
  existing G0 tests.
- Produces the G1 persistence record in `docs/PROJECT_STATE.md`.

- [ ] **Step 1: Run the focused G1 tests**

```powershell
python -m pytest tests/test_g1_registries.py tests/test_g1_feature_branch_audit.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 2: Run the existing G0 verification**

```powershell
python -m pytest tests/test_section_4_2_artifacts.py -q
```

Expected: PASS with `7 passed`.

- [ ] **Step 3: Run validator, audit, and repository hygiene checks**

```powershell
python scripts/audit_g1_registries.py --root docs/evidence/g1 --report outputs/problem2_sr_mappo_v1/g1/registry-audit.json
python scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown docs/audits/g1-feature-branch-audit.md --json outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json
git diff --check
git status --short
```

Expected: both JSON reports have status `pass`, `git diff --check` is clean,
and only G1 paths appear in the working tree.

- [ ] **Step 4: Update `docs/PROJECT_STATE.md`**

Add a G1 section that records:

- current branch and base;
- registry and audit paths;
- candidate commit audited;
- exact commands and results;
- the G1 commit and pushed commit hash after persistence;
- current maturity `M1`;
- G1 passed only if all validation and audit checks pass;
- G2 entry conditions;
- unresolved external parameter/literature evidence;
- explicit statement that no training, formal result, or sealed-test result
  was produced.

- [ ] **Step 5: Commit the G1 persistence record**

```powershell
git add docs/PROJECT_STATE.md outputs/problem2_sr_mappo_v1/g1
git commit -m "docs: record g1 evidence registration and audit"
```

- [ ] **Step 6: Push and record the final pushed hash**

```powershell
git push origin codex/problem2-g0-orchestration
git rev-parse HEAD
git ls-remote origin refs/heads/codex/problem2-g0-orchestration
```

Update `docs/PROJECT_STATE.md` with the final pushed hash and commit that
contains the record, then create the required non-rewriting persistence commit
and push it. Verify the final local and remote hashes match.

### Task 5: Final gate review

**Files:**
- Read: `docs/PROJECT_STATE.md`
- Read: `docs/audits/g1-feature-branch-audit.md`
- Read: all files under `docs/evidence/g1`
- Read: both G1 JSON reports

- [ ] **Step 1: Confirm evidence-chain boundary**

```powershell
rg -n "source|config|run ID|raw|validated|summary|artifact|thesis|M1|G1|G2|sealed|training|formal" docs/PROJECT_STATE.md docs/audits/g1-feature-branch-audit.md docs/evidence/g1
```

Confirm that G1 registers the chain but contains no formal run or thesis
result.

- [ ] **Step 2: Confirm protected repositories were not modified**

Run a read-only status and hash check in
`C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`; do not stage or write
there. Confirm its dirty files remain the same set recorded at G0.

- [ ] **Step 3: Confirm the gate transition wording**

`docs/PROJECT_STATE.md` must say:

```text
G1 passed: evidence registries and candidate-branch audit are recorded and
verified. The highest maturity remains M1. G2 deterministic-model validation
may begin; no training or formal experiment is authorized by G1 alone.
```

- [ ] **Step 4: Report completion precisely**

The final response must state the highest maturity and gate actually passed,
paths of code/tests/registries/audit reports, failed or unverified gates,
external evidence still required, permitted claims, and whether protected
Word or first-problem repository files changed.
