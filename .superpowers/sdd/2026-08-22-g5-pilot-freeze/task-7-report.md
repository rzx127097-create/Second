# G5 Task 7 Report

## Scope

Task 7 generated the frozen experiment identity, family, matrix, ablation,
sensitivity, and manifest layers. No physical model or learning algorithm was
changed. The implementation remains at the M2 design/implementation boundary;
it authorizes later execution planning only and makes no efficacy,
superiority, or deployment claim.

## Changed Files

- `src/problem2/experiments/identity.py`
- `src/problem2/experiments/families.py`
- `src/problem2/experiments/matrix.py`
- `src/problem2/experiments/ablation.py`
- `src/problem2/experiments/sensitivity.py`
- `configs/problem2/g5/families.yaml`
- `configs/problem2/g5/ablations.yaml`
- `configs/problem2/g5/sensitivity.yaml`
- `tests/g5/test_experiment_matrix.py`
- `scripts/generate_g5_manifests.py`
- generated files below `outputs/problem2_sr_mappo_v1/g5/manifests/`

## TDD Evidence

RED command:

```text
python -m pytest tests/g5/test_experiment_matrix.py -q
```

RED output: collection failed with `ModuleNotFoundError: No module named
'problem2.experiments.identity'`, caused by the missing Task 7 APIs.

GREEN command and output:

```text
python -m pytest tests/g5/test_experiment_matrix.py -q
5 passed in 4.31s
```

## Graph and Manifest Evidence

`build_training_graph(load_g5_contract(ROOT))` produced exactly `375` unique
formal jobs: `150 + 90 + 60 + 25 + 50`. The 150 base jobs cover all six frozen
scales, all five formal training seeds, and all five frozen learning methods.
Family references retain the unchanged G1
`method|scale|training_seed|config_hash|git_commit` identity and add family,
condition, and protocol fields only at the reference layer.

Generated manifest files and SHA-256 hashes:

```text
development-smoke.json ff85a34467958ac58567730a537d5877103bb0fbe869e9e50cee9efc3222a210
g6-training-jobs.json 2f4edee486a888666eec1f0210facdefd144113d45f5db5e9abf2be3e62c13a9
g6-validation-evaluations.json 4e57689500337d11f86da351ae65314500a6012286b671988f68b66fd3863936
g7-analysis.json 0e91e59df68046c79d0b274514fd453024f843eb4a314c218c846debae0e7129
g7-sealed-evaluations.json 47ab883d64e932081d82be303b2a49303341ad5b7ea04bce8146a22309e59fe0
manifest-summary.json ce3055801592c82f9304500922ecd8a6282fd81597e68216e2f7c6f1d09ffa92
pilot-manifest.json 52f6fde87712df522d976137d05e7025f5e85243c61566e33895588e40447991
```

The generator was run twice into independent temporary roots. Both runs
produced seven files with byte-identical contents. The manifest scan found no
`30000`, `30099`, or `sealed_scenario` payload. G6/G7 files are unexecuted
skeletons with empty results and sealed access false. Unsafe deduplication is
rejected when any canonical identity field or checkpoint protocol hash differs.

## Verification

- `python -m pytest tests/g5 -q`: `230 passed in 40.37s`.
- `python -m pytest tests/g2 tests/g3 tests/g4 -q`: `243 passed in 138.78s`.
- `python -m compileall -q src scripts`: exit `0`.
- `git diff --check`: exit `0`.
- Generator repeated-output comparison: `files=7 byte_identical=True`.

## Concerns and Boundary

No unresolved implementation blocker remains. Task 8 orchestration, recovery,
validation, sealed locking, and any execution are intentionally out of scope.
No pilot, validation tuning, formal job, or sealed evaluation was run. No
protected external assets, Word files, OSM input, or `_tmp_docx_assets/` were
modified.

Post-review correction: `protocol_hash` is now bound to the exact frozen
`configs/problem2/g5/protocol.yaml` SHA-256, matching the existing partition
adapter contract. The correction was pushed as commit
`6355cc2` without rewriting the earlier implementation commit.

## Fix Round 1

The canonical G1 serialization is retained by
`canonical_training_serialization`; the authoritative training identity is now
the lowercase SHA-256 digest of that exact serialization. All 375 jobs verify
by recomputing the digest from their five identity fields. Deduplication also
recomputes both candidate digests and rejects tampered records.

Task 7 family references are serialized in `g6-training-jobs.json` with the
experiment identity, family, condition, canonical digest, and deterministic
job index. The manifest contains `645` raw references and each pointer resolves
to the indexed job digest. The summary records the exact decomposition
`150 + 90 + 60 + 25 + 50 = 375`, raw family reference counts, source commit,
source-tree hash, protocol hash, registry hashes, and all 25 config hashes.

The families, ablations, and sensitivity registries are now strict-loaded by
`load_g5_contract` and their canonical file hashes are included in every
config hash. Registry drift fails closed. Git provenance fails closed when Git
is unavailable or the tracked source tree is dirty (output-only manifest drift
is permitted during regeneration). The generated source tuple is:

```text
source_commit=b28a1f667b20237fefafb1791f2d3c68509518d3
source_tree_sha256=ff11c425ce25e2fd627e2e8d6967f211fe7226fec804cc57d3358bbab08c14ad
protocol_hash=63b8637ec0cb2d8cccde5e030e6b5d61ca5b812e075f5da3ac7c4f4a4c24bfe4
```

Fix-round verification:

- `python -m pytest tests/g5/test_experiment_matrix.py -q`: `8 passed in 6.26s`.
- `python -m pytest tests/g5 -q`: `233 passed in 45.44s`.
- `python -m pytest tests/g2 tests/g3 tests/g4 -q`: `243 passed in 150.19s`.
- Generator twice into independent roots: `byte_identical=True files=7`.
- Canonical digest audit: `375` jobs, all digest recomputations true.
- Reference resolution audit: `645` references, every job index resolves.
- Registry drift test, strict ablation/sensitivity tests, and malformed identity tests pass.
- `python -m compileall -q src scripts`: exit `0`; `git diff --check`: exit `0`.
- Sealed/result payload scan: clean; no pilot, validation, formal, or sealed execution.

Fix-round content commits pushed without force-push:
`32dedfd` (identity/registry/provenance implementation), `2c9edc7`
(output-only drift provenance guard), `cc245a4` (focused regression test), and
`b28a1f6` (contract-audit registry count regression), and `f499717` (final
regenerated manifests and fix-round report). The final pushed parity commit is
`f499717`.

## Fix Round 2

The provenance source scope now explicitly includes
`src/problem2/experiments/g5_contract.py`, which controls strict registry
loading and configuration-hash inputs. The exact ten-file scope is serialized
as `provenance.source_tree_paths`; the regression suite asserts the contract
loader is included. Regeneration and the final artifact commit follow this
source-scope correction.

Final fix-round artifact tuple (used for the committed manifests) is:

```text
source_commit=a868e6d5d3220aed1e128d052204a4ba74cb5969
source_tree_paths=10
```

The final manifest/summary content was committed and pushed in `04f87fa`.
