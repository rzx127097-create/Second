# Task 10 Smoke Acceptance Report

Date: 2026-08-25

## Scope

Implemented the bounded development-only runner and fail-closed CPU/CUDA
preflight in `src/problem2/training/`. The runner uses `problem2.algorithms.build_algorithm`, exact heterogeneous role dimensions/masks, shared collection/update/checkpoint paths, deterministic evaluation mode, and checkpoint interruption/resume. Conditions are metadata boundaries and never substitute the requested learning method. Resource semantics remain pesticide-only; battery replenishment is disabled.

## Verification

- `python -m pytest tests/g5/test_end_to_end_smoke.py -q`: 10 passed (focused suite; includes all five methods, role shapes/masks, finite updates, checkpoint reload, evaluation freeze, resume equivalence, condition identity, and partition guard).
- `.venv-g5/Scripts/python.exe scripts/run_g5_smoke.py --device cpu --interactions 128 --all-methods --all-condition-types`: exit 0, status pass, 85 jobs (five methods x seven primary conditions x five ablation/sensitivity condition families).
- `.venv-g5/Scripts/python.exe -c ...run_preflight('cuda')`: status pass; Python 3.11.15, Torch 2.13.0+cu126, CUDA 12.6, NVIDIA GeForce RTX 4060 Laptop GPU, 8,585,216,000 bytes VRAM, deterministic algorithms true, cuDNN deterministic true, benchmark false.
- `.venv-g5/Scripts/python.exe scripts/run_g5_smoke.py --device cuda --interactions 128 --all-methods`: exit 0, status pass, five jobs; each result records peak allocated/reserved CUDA memory.
- Audit artifact SHA-256 at the last CUDA run: `58ccd814eb662608a90ab74d7c81df513badbacbc8ae0e3d50c9803b05aceeb`.

## Boundary and blockers

No validation or sealed scenarios were accessed. No pilot, formal training,
validation tuning, sealed evaluation, or deployment execution occurred. The
runner rejects non-development identities and records `validation_accessed` and
`sealed_accessed` false. The project remains at M2 implementation/scoped
mechanism evidence; no efficacy or superiority claim is made.

The CPU matrix was completed before the final manifest hardening edit; the
focused suite and CUDA smoke were run after the implementation corrections.
The canonical audit root contains only generated smoke/audit artifacts; no
scientific configuration was changed.
