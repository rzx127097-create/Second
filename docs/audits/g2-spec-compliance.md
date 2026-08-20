# G2 Specification Compliance Checklist

Date: 2026-08-20
Branch: `codex/problem2-g2-deterministic-validation`
Code/provenance commit: `d4dc97d02ede579cb6e8aedf4df65f4d5a47c107`
Generator tree SHA-256: `e43c84d592e55d0925e747d6edcf1c713eb0a93174bfb2bb510a2908831c16f6`

| Spec section | Implementation and tests | Evidence/check |
|---|---|---|
| 3 End-to-end architecture | `src/problem2/config.py`, `domain.py`, `road/`, `dynamics/`, `service/`, `resources/`, `simulation/`; `tests/g2` | Full G2 suite and full repository suite pass. |
| 4 GIS source, projection, AOI | `src/problem2/road/source.py`; `tests/g2/test_road_source.py` | Source hash `B3AF...A9462`, source `EPSG:4326`, target `EPSG:32643`, 500 m x 300 m AOI in audit report. |
| 5 Six-scale raster topology | `src/problem2/road/raster.py`; `tests/g2/test_road_raster.py` | Six scale records, four-connected caches, component and repair fields. |
| 6 Cache contract | `src/problem2/road/cache.py`, `src/problem2/audit.py`; `tests/g2/test_road_cache.py`, `test_g2_cli.py` | 12 cache files plus manifest; source CRS, generator commit/tree hash and content checksums verified. |
| 7 Metric movement | `src/problem2/dynamics/motion.py`; `tests/g2/test_motion.py` | Literal UAV/vehicle payload tests; 5 m/s UAV and 8 m/s vehicle audit values. |
| 8 Request/service state machines | `src/problem2/service/state_machine.py`; `tests/g2/test_service_state_machine.py`, `test_simulation_engine.py` | Explicit `PENDING -> RESERVED -> SERVING`, node/primary-component validation, locks, completion and cancellation tests. |
| 9 Pesticide conservation | `src/problem2/resources/ledger.py`; `tests/g2/test_resource_ledger.py` | Max absolute replay error `2.220446049250313e-16 L`, tolerance `1e-9 L`. |
| 10 Frozen step order | `src/problem2/simulation/engine.py`; `tests/g2/test_simulation_engine.py` | Phase-order and final-service-boundary tests; 183-event trace. |
| 11 Determinism/audit artifacts | `src/problem2/simulation/replay.py`, `src/problem2/audit.py`; `tests/g2/test_reproducibility.py`, `test_g2_cli.py` | Hash seeds 1/98765 byte-identical; trace SHA `9a47...a3f0`; manifest has 14 entries. |
| 12 Failure policy | Public validators and CLI boundaries across `src/problem2/` and `scripts/` | Corrupt-cache, rollback, forged-CLI, nonfinite, and config-drift tests fail closed. |
| 13 Required verification | All `tests/g2` modules and audit CLIs | `102 passed`; `158 passed`; compileall; preprocess pass; audit pass; diff check pass. |
| 14 Persistence/claims | `HANDOFFG2.md`, `docs/PROJECT_STATE.md`, output manifest | Content `c47f157` and persistence `ab31744` are pushed and all final hashes agree; no efficacy claim. |

## Review Outcome

The independent fix-round review marked all six original Critical/Important
findings addressed and found no new Critical/Important breakage. A non-blocking
observation remains that direct service APIs accept a UAV with no pre-existing
active request, while the transactional engine always creates and attaches the
request before reservation. This does not alter the registered engine path.

## Evidence Boundary

This checklist establishes deterministic implementation verification at M2 only.
No RL training, validation-scene tuning, formal experiment, paired treatment
result, sealed-test access, deployment claim, or superiority claim is present.
