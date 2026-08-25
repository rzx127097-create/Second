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
g6-training-jobs.json 2a6811727202fc88bd77775d2484925d00f7104c6d998293b2df9bfbbaa13b75
g6-validation-evaluations.json 6e53997906e11c7df4b7ea0c100fc2db9c9cfe3c4632c12a918ac8f8815b3a4e
g7-analysis.json 0e91e59df68046c79d0b274514fd453024f843eb4a314c218c846debae0e7129
g7-sealed-evaluations.json 6547610978a1d3da302c76625cd370dac52f8ee8d0005be7496c49070f6d3118
manifest-summary.json e57cf33cdaa24305868763c118663237735a5e78a9812be20c85e416725316b1
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
