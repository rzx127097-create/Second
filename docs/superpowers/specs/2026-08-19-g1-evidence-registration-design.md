# G1 Evidence Registration Design

## Status

Approved in chat on 2026-08-19. This document defines the G1 registration and
existing-code audit deliverable for the second research problem. It does not
authorize deterministic-model validation, MARL training, formal experiments,
or sealed-test access.

## Goal

Establish a machine-checkable evidence registry and an independent audit record
for the existing `origin/feature/problem2-code-framework` branch. The result
must make every later parameter, run, summary, and thesis artifact traceable
without treating candidate-branch maturity claims as verified evidence.

## Research Boundary

- Public algorithm name remains `SR-MAPPO`.
- Problem 2 remains an air-ground heterogeneous extension of SR-MAPPO.
- HAPPO and `AG-SR-MAPPO` are forbidden identifiers.
- The replenished resource is pesticide only. Battery replenishment remains
  inactive.
- OSM inputs are road-constrained simulation inputs, not field-deployment
  evidence.
- Current maturity remains M1: design/specification evidence.
- The sealed-test scenario range `30000-30099` remains locked and cannot be
  used for tuning, registry completion, or branch audit claims.
- G1 must not start training, formal evaluation, or large experiments.

## Scope

### Included

1. Read-only audit of `origin/feature/problem2-code-framework` against
   `origin/main`, including source, configuration, tests, verification reports,
   hashes, and maturity wording.
2. Evidence registries for:
   - engineering parameters and source records;
   - literature and external sources;
   - methods, scales, seeds, scenarios, and evaluation protocol;
   - immutable job identity and configuration hashes;
   - raw episode and validated long-table schemas;
   - figures, tables, text blocks, and source hashes;
   - sealed-test lock status;
   - the frozen output-root contract.
3. Machine-readable validation for registry structure, cross-references,
   forbidden claims, seed/scenario separation, and sealed-test locking.
4. Project-state update, verification record, commit, push, and pushed-hash
   registration.

### Excluded

- Integrating or merging candidate-branch source code.
- Copying unverified candidate outputs into the formal evidence root.
- Editing source Word thesis files.
- Resolving missing external engineering or literature evidence by invention.
- Running RL training, resource activation pilots, deterministic G2 tests, or
  formal/sealed evaluation.

## Repository Layout

G1 deliverables use these paths:

```text
docs/
  evidence/
    g1/
      parameter_registry.yaml
      literature_source_ledger.yaml
      experiment_matrix.yaml
      scenario_seed_manifest.yaml
      job_identity_contract.yaml
      raw_episode_schema.yaml
      validated_long_table_schema.yaml
      artifact_manifest_schema.yaml
      sealed_test_lock.yaml
      output_root_contract.yaml
  audits/
    g1-feature-branch-audit.md
scripts/
  audit_g1_registries.py
tests/
  test_g1_registries.py
```

The design permits a later implementation to choose JSON instead of YAML for a
specific machine-readable file only if the schema and cross-reference rules
remain equivalent and the change is recorded in the project state. The default
format above is YAML because the candidate branch already uses YAML for
configuration and parameter evidence.

## Registry Contracts

### Parameter Registry

Each parameter record must contain:

```yaml
id: uav.pesticide_capacity
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
conversion: "identity"
status: provisional
scope: development_and_pilot
```

Required parameter coverage includes onboard pesticide capacity and usable
fraction, spray flow, UAV speed, vehicle inventory and speed, transfer rate,
setup/service time, rendezvous radius, and physical decision-step duration.
Each critical value must state whether it is verified or provisional. A source
record cannot be omitted merely because the value is an assumption.

### Literature and Source Ledger

Each source record must distinguish metadata verification from claim support:

```yaml
id: SRC-ASSUMPTION-001
source_type: assumption
title: Internal development assumption
authors: []
venue: internal
year: 2026
locator: docs/evidence/g1/parameter_registry.yaml
authority: internal_design_record
access_status: read
full_text_status: not_applicable
supports:
  - parameter_id: uav.pesticide_capacity
    claim: Development value selected for specification and later sensitivity audit
    applicability_limit: Not empirical equipment evidence
```

External records must include authors, title, venue, year, database or
authoritative page, access status, full-text versus metadata status, supported
claim, and applicability limit. Inaccessible or conflicting records remain
pending rather than being silently promoted to verified.

### Experiment, Scenario, and Seed Manifests

The experiment matrix records the five primary methods, six scales, physical
step limits, resource/information matching rules, outcome metrics, and
development/validation/sealed split. The scenario manifest records:

- training seeds: `42`, `123`, `2024`, `3407`, `7919`;
- validation scenario seeds: `20000-20049`;
- sealed-test scenario seeds: `30000-30099`;
- the fact that sealed IDs are locked and excluded from tuning.

Every primary method uses the same environment, pesticide budget, service
capability, horizon, scenario IDs, and information conditions unless a
documented pre-evaluation exception is recorded.

### Job Identity and Configuration Hash Contract

The immutable job identity is:

```text
method + scale + training_seed + config_hash + git_commit
```

The registry defines canonical serialization, SHA-256 hashing, allowed job
states (`pending`, `running`, `completed`, `failed`, `stale`), and the fields
required for later atomic recovery. A sealed-test job cannot be created until
method, configuration, statistics, and primary metrics are frozen in a later
gate.

### Raw and Validated Table Schemas

The raw episode schema requires run identity, method, scale, training seed,
scenario ID, configuration hash, Git commit, termination reason, primary
outcomes, resource metrics, and mechanism metrics. The validated long-table
schema preserves those keys and adds validation status and source-row
reference. Validation must reject duplicate run IDs, missing identities,
mixed sealed/development sets, missing metric units, stale config hashes, or
non-finite values.

### Artifact Manifest Schema

Every future figure, table, or thesis text block must record:

```yaml
artifact_id: FIG-G8-001
artifact_type: figure
source_paths: []
source_hashes: []
generator: scripts/figures/example.py
generator_commit: null
output_path: outputs/problem2_sr_mappo_v1/artifacts/example.png
created_at: null
data_status: design_only
```

G1 registers the schema only. It does not create formal result artifacts.

### Sealed-Test Lock and Output-Root Contracts

The sealed-test lock records the exact scenario range, lock status, allowed
unlock gate (`G7`), one-time unlock rule, and prohibition on tuning. The
output-root contract fixes all second-problem evidence under
`outputs/problem2_sr_mappo_v1` or a documented descendant. It records that
first-problem roots and source OSM files are read-only and that derived road
caches must carry source hash, CRS/bbox, grid shape, topology checksum, and
code version.

## Candidate-Branch Audit

The audit is read-only and reproducible from Git objects. It will:

1. Record both source commit IDs and the comparison base.
2. Inventory changed paths and classify them as source, configuration, test,
   report, output, or thesis/document asset.
3. Inspect candidate parameter, scenario, experiment, artifact, and sealed-test
   records for field completeness and cross-reference consistency.
4. Run only bounded static and smoke checks that do not train or access sealed
   scenarios.
5. Compare maturity wording in reports and docs against the M1 boundary.
6. Record hashes or Git object IDs for relied-upon candidate files.
7. Classify each candidate asset as:
   - `admissible_design_input`;
   - `requires_independent_reverification`;
   - `not_admissible_as_evidence`;
   - `protected_or_out_of_scope`.

The audit report must state unresolved issues and must not describe candidate
M3/M4 reports as passed gates in the current branch.

## Data Flow and Failure Handling

```text
frozen project decisions
-> G1 registry files
-> machine validator
-> candidate-branch read-only audit
-> project-state update
-> commit and pushed hash
```

The validator fails closed. It must report every missing required field,
unknown cross-reference, duplicate identity, forbidden algorithm name,
forbidden maturity claim, sealed-test violation, output-root violation, and
invalid seed partition. A failed validation blocks the G1 completion record.

No registry is considered frozen if it contains an unresolved placeholder,
unbounded range, absent unit for a physical value, missing source status, or a
sealed-test record that is not explicitly locked.

## Verification and Acceptance

G1 acceptance requires all of the following:

1. `scripts/audit_g1_registries.py` validates every G1 registry and returns
   success on the committed files.
2. `tests/test_g1_registries.py` covers required fields, cross-references,
   identity construction, seed separation, forbidden names/claims, and sealed
   lock behavior.
3. The candidate-branch audit report records source commits, inspected assets,
   commands, results, classifications, and unresolved issues.
4. Existing G0 tests still pass and `git diff --check` is clean.
5. No first-problem repository file changes.
6. No training, formal experiment, or sealed-test result is present in the G1
   completion record.
7. `docs/PROJECT_STATE.md` records the G1 verification commands, result,
   commit, pushed branch/hash, and next gate conditions.

Passing G1 establishes evidence registration and audit readiness only. It does
not pass G2, G3, G4, G5, G6, G7, or G8 and does not change the highest maturity
above M1.

## Planned Commit Boundary

The design document is committed before implementation. The implementation
phase will use focused commits for registry schemas/fixtures, validator/tests,
candidate-branch audit, and project-state persistence. Every phase commit is
pushed to the current `codex/` branch before the next gate begins.
