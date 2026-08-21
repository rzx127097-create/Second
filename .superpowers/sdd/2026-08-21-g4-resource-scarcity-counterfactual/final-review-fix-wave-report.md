# G4 Final Review Fix Wave Report

Date: 2026-08-21  
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`  
Branch: `codex/problem2-g4-resource-scarcity`

## Scope

This wave was limited to the final G4 review findings. G4 remains an M2
diagnostic support-probe acceptance candidate pending controller final review,
non-rewriting push verification, and persistence. The scarcity axis remains
`initial_uav_pesticide_l` at `0.05`, `0.2875`, and `0.525 L`; vehicle inventory
is fixed at `20.0 L`; validation/sealed seeds and battery replenishment remain
inactive.

## TDD RED Evidence

Focused regression tests were added before production changes and then run:

```text
9 failed, 38 deselected in 6.83s
```

The failures were the expected unprotected bypasses: realistic G3 paths,
root-manifest strings, nested manifests, G3 execution flags, reserved IDs in
JSON/JSONL, and dirty source provenance. A tenth direct source-bundle hash
regression was then added. The first implementation run exposed a test-caught
integer handling defect in the recursive seed scanner; it was corrected before
the final green run.

## Changes

- `src/problem2/experiments/g4_audit.py`: recursively scans the root manifest
  and all manifested JSON/JSONL values; rejects realistic G3 endpoint paths,
  nested artifact manifests, truthy G3 actor/checkpoint execution flags, and
  reserved validation/sealed seed IDs; verifies per-source-file and
  deterministic source-bundle hashes from the recorded commit.
- `src/problem2/experiments/g4_activation.py`: rejects dirty or changed
  selected source-provenance paths, binds generation to `HEAD`, and emits
  per-file plus deterministic source-bundle hashes.
- `tests/g4/test_g4_audit.py` and `tests/g4/test_g4_activation.py`: regression
  coverage for every reported bypass and source provenance drift.
- `docs/PROJECT_STATE.md`, `HANDOFFG4.md`, and
  `docs/audits/g4-mechanism-compliance.md`: changed premature final-pass
  wording to acceptance-candidate wording, corrected the superseded historical
  `[1.0, 12.0] L` vehicle-inventory label, and recorded new provenance.
- Canonical G4 outputs under `outputs/problem2_sr_mappo_v1/g4` were regenerated
  and audited from source commit `f53b86b05372a142a9b4796db2e7c3fc9be901a1`.

## Verification

```text
Focused final regressions: 11 passed, 37 deselected in 10.70s
G4 suite: 70 passed in 69.38s
Full suite: 291 passed in 105.23s
python -m compileall -q src scripts: exit 0
git diff --check: exit 0
python scripts/run_g4_mechanism_probe.py: [0.05, 0.525]
python scripts/audit_g4_mechanism.py ...: status=pass artifacts=10
```

The first post-implementation G4 suite returned `68 passed, 2 failed` because
the one-line audit-cache optimization was itself an uncommitted source change;
the failures correctly demonstrated dirty-provenance rejection. After commit
`f53b86b05372a142a9b4796db2e7c3fc9be901a1`, regeneration, and rerun, the suite
was fully green.

## Commits

- `906bfc2549ce31cb3bad054cb8ff080baec65243` - `fix: harden g4 review boundaries`
- `f53b86b05372a142a9b4796db2e7c3fc9be901a1` - `perf: cache g4 source bundle verification`

No push was performed. The regenerated canonical evidence and this report are
committed locally; the controller must perform the final review, non-rewriting
push verification, and final acceptance-state persistence decision.

## Concerns

- Final G4 acceptance, push, and the corresponding final project-state record
  remain controller responsibilities and are intentionally not claimed here.
- Source-bundle verification is cached per commit within an audit process;
  generation still rejects selected-source dirty state before writing evidence.
- No validation or sealed seed was accessed, no battery replenishment was
  activated, and no efficacy, superiority, deployment, vehicle-inventory
  scarcity, or G3 actor/checkpoint execution claim is supported.

## Fix Round 2

### Findings Addressed

- Broadened recursive G3 execution-flag rejection to cover generic
  `g3_execution` and actor/checkpoint variants while preserving false values.
- Added an exact ten-path artifact allowlist to both manifest generation and
  audit verification. Arbitrary extra JSON/JSONL and missing canonical paths
  now fail closed.
- Added recursive rejection for reserved validation/sealed seed IDs encoded as
  strings, including `"20000"` through `"20049"` and `"30000"` through
  `"30099"`.
- Corrected `docs/PROJECT_STATE.md` so its Next Step requires final G4 review,
  non-rewriting push verification, and persistence before G5.

### TDD RED

The new focused regression run before implementation returned:

```text
8 failed, 3 passed, 32 deselected in 12.12s
```

The failures covered generic G3 execution, string seed IDs, arbitrary extra
JSON/JSONL, exact allowlist enforcement, and legacy tests that still expected
arbitrary manifest paths to be accepted.

### Verification

```text
Focused round-2 regressions: 11 passed, 32 deselected in 10.78s
G4 audit test module: 43 passed in 38.15s
G4 suite: 76 passed in 83.09s
Full suite: 297 passed in 122.71s
python -m compileall -q src scripts: exit 0
git diff --check: exit 0
python scripts/run_g4_mechanism_probe.py: [0.05, 0.525]
python scripts/audit_g4_mechanism.py ...: status=pass artifacts=10
Exact canonical manifest paths: 10 required paths, no extras
Canonical provenance source commit: ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb
```

### Commits

- `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` - `fix: close g4 artifact boundary gaps`
- `69b71dd6aaa2489c772cbb7b5571a00c53c34c4a` - `docs: persist g4 round 2 review evidence`

No push was performed. G4 remains an M2 acceptance candidate pending
controller final review, non-rewriting push verification, and final
acceptance-state persistence. G5 remains unauthorized.
