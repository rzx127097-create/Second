# G5 Task9 Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Implement deterministic, contract-bound convergence summaries, hierarchical paired bootstrap estimates, Holm correction, practical-equivalence classification, mechanism summaries, and ordered negative-result diagnosis for G5 without reading unvalidated raw logs or executing experiments.

**Architecture:** Keep each statistical concern in a small pure-Python module under `src/problem2/statistics/`. Inputs are validated row mappings or typed summary records; outputs are frozen dataclasses or plain mappings with finite numeric fields. The package never opens files, accesses sealed partitions, filters seeds/scenarios, or mutates manifests. Scripts are thin JSON stdin/file adapters that call the pure functions only.

**Tech Stack:** Python 3.11 standard library, `dataclasses`, `math`, `statistics`, `random`/`numpy` only if already available; pytest fixtures with hand-computable rows. No new scientific dependency or RNG behavior outside the frozen seed `20260822`.

**Spec:** `docs/superpowers/plans/2026-08-22-g5-pilot-freeze.md` Task 9 and `docs/superpowers/specs/2026-08-22-g7-sealed-analysis-design.md` sections on paired estimation, convergence, mechanism audit, and negative-result diagnosis.

## Global Constraints

- Current maturity remains `M2`; no pilot, formal training, validation tuning, or sealed evaluation may run.
- The public algorithm identity remains `SR-MAPPO`; pesticide is the only replenished resource.
- Training seed is the independent replication unit; scenarios are paired within seed and are not independent training replications.
- The frozen bootstrap contract is hierarchical paired, `B=10000`, RNG seed `20260822`, percentile 95% interval, plus-one two-sided tail probability.
- Holm adjustment operates separately by registered confirmatory family.
- Equivalence requires the complete interval to lie inside the symmetric practical margin; a nonsignificant p-value is not equivalence.
- Mechanism metrics remain direct logged measures: road rendezvous, realized service travel, waiting, pesticide-disabled time, effective spray steps, reduction, and success.
- Functions reject non-finite numbers, missing grouping keys, duplicate pairing cells, malformed intervals, and unsupported metrics instead of silently dropping rows.

### Task 1: Pure Statistics Package

**Files:**
- Create: `src/problem2/statistics/__init__.py`
- Create: `src/problem2/statistics/convergence.py`
- Create: `src/problem2/statistics/paired.py`
- Create: `src/problem2/statistics/multiplicity.py`
- Create: `src/problem2/statistics/equivalence.py`
- Create: `src/problem2/statistics/mechanism.py`
- Create: `src/problem2/statistics/diagnosis.py`
- Create: `tests/g5/test_statistics.py`
- Create: `scripts/analyze_g5_paired.py`
- Create: `scripts/analyze_g7.py`
- Modify: `.superpowers/sdd/2026-08-22-g5-pilot-freeze/progress.md`

**Interfaces:**
- `summarize_convergence(rows: Iterable[Mapping[str, object]], budget: int, threshold: float = 0.85) -> ConvergenceSummary` consumes checkpoint rows containing `training_seed`, `scale`, `interaction_count`, `reduction_rate`, optional `valid_update`, `finite`, `clipped`, and `regression`; it reports normalized trapezoidal AUC over `[0,budget]`, observed/right-censored threshold interactions, restricted mean threshold time, final-window standard deviation over the last 20% budget, across-seed checkpoint dispersion, and diagnostic counts.
- `hierarchical_paired_bootstrap(rows: Iterable[Mapping[str, object]], metric: str, B: int = 10000, seed: int = 20260822) -> PairedEstimate` consumes one row per `(training_seed, scenario_id, method, condition_id, scale)` with `value_a`/`value_b` or `method`/`value` pair fields, resamples matched seeds then shared scenarios, and returns observed mean paired difference, percentile interval, plus-one two-sided tail probability, and per-seed summaries.
- `holm_adjust(records: Iterable[Mapping[str, object]]) -> list[AdjustedRecord]` consumes `family`, `hypothesis_id`, and finite raw `p_value`; it adjusts each family independently, preserves deterministic tie ordering, and rejects duplicate IDs within a family.
- `classify_equivalence(interval: tuple[float, float], margin: float) -> str` returns only `equivalent`, `directional_positive`, `directional_negative`, or `inconclusive` using complete-interval rules.
- `summarize_mechanism(rows) -> MechanismSummary` preserves direct metric means, paired deltas, sign coherence at scenario/seed/aggregate levels, and explicit endpoint/mechanism interpretation without causal-mediation language.
- `diagnose_result_bundle(validated_rows, audit_records) -> DiagnosisReport` checks the frozen ordered stages: data/state correctness, mechanism activation, physical/engineering consistency, learnability, training/checkpoint behavior, comparator fairness, and genuine boundary/absence of effect; it never filters observations.
- CLI scripts accept `--help`, optional JSON input/output paths, and fail closed on malformed/unvalidated rows; they do not access sealed files or mutate locks.

- [ ] **Step 1: Add hand-computable failing tests** for paired means, seed/scenario pairing, percentile intervals, plus-one tails, Holm family ordering, equivalence boundaries, convergence AUC/threshold/censoring/final window/regression counts, mechanism sign coherence, and ordered diagnosis.
- [ ] **Step 2: Run the focused test file** and confirm failures are due to missing statistics modules/interfaces.
- [ ] **Step 3: Implement the pure deterministic functions** with explicit validation, stable ordering, and no raw-file access.
- [ ] **Step 4: Run the focused tests twice** with the frozen bootstrap seed and compare serialized outputs byte-for-byte.
- [ ] **Step 5: Run all G3/G5 and G2/G4 regression tests, compileall, CLI help, contract audit, and diff check.**
- [ ] **Step 6: Request independent review, address Critical/Important findings, then commit `feat: freeze g5 paired statistics`.**
- [ ] **Step 7: Push content, update `docs/PROJECT_STATE.md` with the content hash and Task10 next step, commit/push the persistence record, and verify three-way parity.**
