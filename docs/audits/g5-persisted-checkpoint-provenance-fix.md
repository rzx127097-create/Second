# Persisted Physical Checkpoint Provenance Fix

Date: 2026-08-29

## Scope

After the second controlled Phase 3 pilot was committed, strict checkpoint
reload rejected the persisted artifact because the validator regenerated
provenance with the current `HEAD`. The artifact was generated at
`eafff2fa259e57a358f03135277611ef32d86bf8`, while the evidence and state
commits advanced the branch to
`d487d0ef482a004e652cd4a913ff6eb520393e92`.

The generation commit is an ancestor of the current commit. All three recorded
physical execution source hashes matched both the generation-commit Git blobs
and the current working files. The failure was therefore caused only by exact
`source_commit` equality, not by checkpoint, source, contract, or artifact
drift.

## Remediation

`validate_physical_training_completion` now accepts a recorded generation
commit only when:

- the recorded and current provenance schemas are identical;
- every provenance field other than `source_commit` is identical;
- the generation and current commits are valid 40-character Git hashes; and
- `git merge-base --is-ancestor` proves that the generation commit is an
  ancestor of the current commit.

The strict checkpoint loader receives the validated generation provenance.
Non-ancestor commits, source-bundle changes, contract changes, artifact hash or
byte drift, extra/missing artifacts, forged summaries, and non-finite states
remain rejected.

## Verification

```text
RED
python -m pytest tests/g5/test_physical_candidate_training.py::test_completion_validator_accepts_ancestor_generation_commit_when_sources_unchanged -q --tb=short
1 failed in 25.43s
failure: physical training checkpoint provenance drifted from current source

GREEN
same command
1 passed in 18.96s

tamper rejection
python -m pytest tests/g5/test_physical_candidate_training.py::test_completion_validator_rejects_torn_tampered_or_nonfinite_identity -q --tb=short
5 passed in 42.36s

full physical training tests
python -m pytest tests/g5/test_physical_candidate_training.py -q --tb=short
52 passed in 147.79s

python -m compileall -q src scripts
exit 0

git diff --check
pass
```

This is an M2 provenance/revalidation correction. It does not authorize a new
matrix identity, replacement G5 freeze, validation selection, formal G6, or G7.
Because `physical_training.py` is itself inside the recorded execution source
scope, the matrix-index-1 pilot must be rerun under the pushed fix commit in a
new attempt directory before it can represent the current Phase 3 source.
