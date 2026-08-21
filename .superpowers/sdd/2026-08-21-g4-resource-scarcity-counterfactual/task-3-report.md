# Task 3 Report: G4 Counterfactual Summary and Audit

Date: 2026-08-21
Branch: `codex/problem2-g4-resource-scarcity`

## Scope

Task 3 adds a fixed-versus-mobile SR-MAPPO counterfactual summary and a
fail-closed G4 mechanism audit. It consumes the existing fixed/mobile G4
activation summaries and does not modify the activation probe machinery.
The `config_path` audit argument is the frozen G4 contract YAML path; the
probe manifest is loaded from the repository path used by Tasks 1 and 2.

The implementation remains descriptive. It records same-input paired deltas,
activation counts, waiting-time reduction, rendezvous-distance change, and
conservation error. It does not calculate p-values, confidence intervals,
significance labels, superiority claims, treatment-effect claims, or formal
endpoint results.

## Implemented Files

- `src/problem2/experiments/g4_counterfactual.py`
  - Implements `run_counterfactual_probe(...)`.
  - Requires identical `(scale_id, seed, scarcity_level_l)` keys and identical
    `input_fingerprint` values for fixed and mobile arms.
  - Emits descriptive `paired_deltas`, activation counts, aggregate waiting
    reduction, rendezvous-distance change, and maximum conservation error.
- `src/problem2/experiments/g4_audit.py`
  - Implements `build_g4_artifact_manifest(...)` and
    `audit_g4_mechanism(...)`.
  - Verifies recorded SHA-256 hashes, rejects missing or unrecorded artifacts,
    rejects path traversal and G3 endpoint paths, and checks raw/JSON evidence
    for validation, sealed-test, and battery activation flags.
  - Produces a report with the frozen contract hash, activation band, paired
    deltas, output artifact hashes, and an explicit hard boundary.
- `scripts/audit_g4_mechanism.py`
  - Provides the command-line audit entry point.
- `tests/g4/test_g4_audit.py`
  - Covers identical-input pairing, G3 rejection, validation rejection, and
    recorded hash drift.
- `src/problem2/experiments/g4_contract.py`
  - Adds integer-ID schema validation for all probe partitions.
- `tests/g4/test_g4_contract.py`
  - Covers rejection of non-integer partition IDs.

## Verification

TDD red phase:

`python -m pytest tests/g4/test_g4_audit.py -q` initially failed during
collection with the expected missing-module error for
`problem2.experiments.g4_audit`.

Green and regression verification:

- `python -m pytest tests/g4 -q`: `25 passed`
- `python -m compileall -q src scripts`: passed
- `git diff --check`: passed; only normal Git LF/CRLF warnings were emitted

The real audit command also passed:

`python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`

Result: `status=pass`, `artifacts=18`.

## Generated Evidence

The audit generated or verified:

- `outputs/problem2_sr_mappo_v1/g4/counterfactual-summary.json`
- `outputs/problem2_sr_mappo_v1/g4/artifact-manifest.json`
- `outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json`

The current counterfactual contains 27 fixed/mobile pairs and equal activation
counts of 27 per arm. These values are descriptive G4 probe outputs only; they
are not formal evaluation results.

## Boundary and Concerns

- Validation access is false.
- Sealed-test access is false.
- Battery replenishment is false.
- G3 smoke artifacts are rejected as endpoint evidence.
- No G5 pilot, formal training, validation tuning, sealed evaluation, paired
  significance analysis, or deployment claim was made.
- The existing `pytest-activation` directory remains under the G4 output root
  as previously generated probe evidence and is included in the artifact
  manifest; it is not treated as G3 endpoint evidence.

This task does not by itself close G4 or authorize G5. The next task must
perform the final G4 documentation, handoff, project-state synchronization,
and persistence checks.

## Fix Round 1

Review findings were addressed as follows:

1. The audit now recomputes the descriptive counterfactual from the fixed and
   mobile activation summaries and requires the stored JSON object to match the
   recomputed object exactly. Updating the artifact hash cannot mask content
   tampering.
2. `output_root` and `report_path` are resolved and required to remain under
   the canonical `outputs/problem2_sr_mappo_v1/g4` root.
3. Both arms require a non-empty string `input_fingerprint`.
4. Counts must be non-negative integers; all continuous mechanism metrics must
   be finite and non-negative. NaN and infinity are rejected.
5. JSON and JSONL evidence is parsed structurally. Malformed JSONL, empty JSONL,
   and non-object JSONL records are rejected. Boundary flags are checked
   recursively in parsed objects rather than by raw-text substring matching.
6. Tests cover the happy path, tampered counterfactual content, activation-band
   mismatch, battery activation, sealed-test activation, unrecorded artifacts,
   malformed JSONL, non-finite metrics, missing fingerprints, invalid counts,
   and both output/report path boundaries.

Exact verification commands and outputs:

```text
python -m pytest tests/g4/test_g4_audit.py -q
...............                                                          [100%]
15 passed in 0.73s

python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json
status=pass artifacts=18

python -m pytest tests/g4 -q
....................................                                     [100%]
36 passed in 27.24s

python -m compileall -q src scripts

git diff --check
warning: normal LF/CRLF working-copy warnings only
```

## Fix Round 2

The audit now rejects every file under the G4 output root whose suffix is not
`.json` or `.jsonl`, so boundary flags cannot be hidden in unsupported textual
or binary artifacts. JSONL parsing also counts non-blank records and rejects a
file containing only blank lines as empty evidence.

Exact verification commands and outputs:

```text
python -m pytest tests/g4/test_g4_audit.py -q
.................                                                        [100%]
17 passed in 0.71s

python -m pytest tests/g4 -q
......................................                                   [100%]
38 passed in 26.70s

python -m compileall -q src scripts

python scripts/audit_g4_mechanism.py --config docs/evidence/g4/g4_contract.yaml --output-root outputs/problem2_sr_mappo_v1/g4 --report outputs/problem2_sr_mappo_v1/g4/g4-mechanism-audit.json
status=pass artifacts=18
```
