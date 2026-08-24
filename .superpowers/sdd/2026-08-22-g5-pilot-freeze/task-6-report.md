# G5 Task 6 Implementation Report

Date: 2026-08-25
Branch: `codex/problem2-g5-pilot-freeze`
Starting commit: `02b4b0fa2a842645bf7007596a19644b9664c193`
Maturity boundary: M2 implementation and test evidence only

## Authorized Scope

Task 6 implemented the physical G2-to-G3 training/evaluation adapter, direct
formal episode metrics, fail-closed evaluation partitions, deterministic
observable-only support controllers, and the exact two-stage budget ancestry
contract. No pilot, validation tuning, formal job, sealed evaluation, frozen
registry edit, external asset write, Word-file edit, or project-state edit was
performed.

The protected untracked `_tmp_docx_assets/` directory was not inspected,
staged, modified, deleted, or cleaned.

## Implementation

- `Problem2CooperativeEnv` consumes the exact behavior-time `ActionResult`,
  rejects stored-mask drift, preserves a selected vehicle slot and request
  mapping throughout an active dispatch, and derives the current G2 road
  direction only for physical execution.
- The adapter reuses G2 UAV/vehicle motion, request reservation, service
  start/advance/completion, terminal cancellation, pesticide transfer/spray,
  and conservation checks. It reuses G3 observation and mask ordering.
- Adapter-owned `dispatch_reserved` events record request identity, selected
  service road node, origin node/target/edge progress, sampled slot, and the
  shortest feasible road-route length. Separate execution events retain both
  sampled slot and physical road direction. Direct service-motion events
  record realized travel including route turns/detours.
- Active reservations wait without action substitution when the UAV is not
  yet within the rendezvous radius. The original slot remains the only legal
  vehicle continuation action.
- `EpisodeMetrics` derives waiting from elapsed decision intervals, including
  unresolved requests through the terminal boundary; separates started-request
  wait; counts direct route/travel, disabled/return/effective-spray UAV time,
  explicit partial and zero transfer outcomes, transfer/inventory totals,
  conservation residual, and decision-only runtime.
- Primary reduction and `0.85` success are computed only when both finite
  initial and final pest totals are explicitly supplied at the environment
  outcome boundary. Both outcomes remain `None` when totals are unavailable;
  one-sided/incomplete totals fail closed.
- `evaluate_episode` permits only frozen development scenario IDs in Task 6,
  denies validation, sealed, out-of-range, and undeclared pairs, forces policy
  evaluation mode, times only `act`, and returns canonical before/after state
  SHA-256 identities. A mutation fails the evaluation and restores the
  original policy state.
- A*, nearest, urgency, and fixed controllers accept one current observable
  dispatch state only. They enforce transfer/service feasibility, reject
  unreachable options, use deterministic ties, and preserve an active slot.
  A* exposes a deterministic path/distance implementation checked against
  Dijkstra. The rolling controller stores the frozen positive replan interval;
  the static-road adapter preserves the selected service node and derives
  shortest physical directions at road nodes.
- `TwoStageSchedule` requires positive integer stage budgets that sum exactly
  to the joint interaction budget and emits both budgets, schedule version,
  method ID, parent hash, and UAV-stage checkpoint hash in ancestry.

## Changed Files

Created exactly the planned Task 6 production and test files, plus this
required report:

```text
src/problem2/training/cooperative_env.py
src/problem2/evaluation/metrics.py
src/problem2/evaluation/runner.py
src/problem2/evaluation/partitions.py
src/problem2/heuristics/__init__.py
src/problem2/heuristics/fixed.py
src/problem2/heuristics/astar.py
src/problem2/heuristics/nearest.py
src/problem2/heuristics/urgency.py
src/problem2/heuristics/two_stage.py
tests/g5/test_environment_metrics.py
tests/g5/test_heuristics.py
.superpowers/sdd/2026-08-22-g5-pilot-freeze/task-6-report.md
```

No shared existing source file required modification. Frozen registries,
candidate values, algorithm mathematics, G2 inputs, external assets, outputs,
and `docs/PROJECT_STATE.md` are unchanged.

## TDD Evidence

### Required initial RED

Command:

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5/test_environment_metrics.py tests/g5/test_heuristics.py -q
```

Authentic output before any production adapter existed:

```text
ERROR tests/g5/test_environment_metrics.py
ModuleNotFoundError: No module named 'problem2.evaluation'
ERROR tests/g5/test_heuristics.py
ModuleNotFoundError: No module named 'problem2.heuristics'
2 errors in 0.56s
```

Exit code: `1`. The RED was caused only by the missing Task 6 adapters.

### First implementation cycle

The same focused command produced:

```text
1 failed, 15 passed in 1.34s
```

The single failure showed that the detour fixture continued requesting the
completed slot for two idle intervals. The test horizon was corrected to the
hand-derived four-step service-completion boundary; production behavior was
not weakened. The next run returned:

```text
16 passed in 0.94s
```

### Self-review RED/GREEN cycles

Three new behavior tests were added before their fixes: out-of-radius reserved
wait, evaluation mutation restoration, and executable fixed support. The
focused command returned:

```text
3 failed, 16 passed in 1.27s
```

After minimal fixes it returned:

```text
19 passed in 0.82s
```

A canonical-identity test then deliberately reordered an otherwise identical
state mapping. Before canonical serialization:

```text
1 failed in 1.19s
```

After canonical mapping/array/tensor serialization, the complete focused suite
returned:

```text
20 passed in 0.81s
```

### Fresh final focused GREEN

Command:

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g5/test_environment_metrics.py tests/g5/test_heuristics.py -q
```

Output:

```text
20 passed in 0.82s
```

Exit code: `0`.

## Fresh Verification

Host Python retained G2 subprocess import behavior and ran G2/G4:

```powershell
python -m pytest tests/g2 tests/g4 -q
```

```text
178 passed in 88.00s (0:01:27)
```

The known-good G5 environment ran G3 and the complete G5 suite:

```powershell
.venv-g5/Scripts/python.exe -m pytest tests/g3 tests/g5 -q
```

```text
272 passed in 30.87s
```

Compilation:

```powershell
.venv-g5/Scripts/python.exe -m compileall -q src scripts
```

Output: none; exit code `0`.

Staged whitespace verification:

```powershell
git diff --cached --check
```

Output: none; exit code `0`.

Committed-diff verification is rerun after the report-only commit amendment:

```powershell
git diff HEAD^ HEAD --check
```

Output: none; exit code `0`.

## Self-Review

- Confirmed no sampled vehicle slot is converted into a different semantic
  action. Direction translation is separately evented physical execution.
- Confirmed illegal action/mask drift fails before state or metric mutation.
- Confirmed direct reservation distance is shortest road distance and realized
  service travel is accumulated independently from motion events.
- Confirmed wait arithmetic uses `service_start_step - created_step` and the
  terminal boundary for unresolved requests.
- Confirmed spray volume never enters reduction-rate calculation.
- Confirmed unavailable primary outcomes remain explicit rather than becoming
  zero efficacy.
- Confirmed controller public decisions accept no future pest/demand input.
- Confirmed validation and sealed IDs are denied before reset/read.
- Confirmed the fixed comparison validates exact inventory, cap, transfer rate,
  and setup-time matching.
- Confirmed no existing shared source edit was necessary.

No Critical or Important self-review issue remains open. Independent subagent
review was not dispatched because the Task 6 controller explicitly prohibited
subagents.

## Concerns And Boundaries

- Rolling A* records a frozen replan interval, but the accepted road graph is
  static during an episode. Active dispatch therefore preserves the original
  selected service node while the adapter deterministically derives the
  shortest feasible direction at road nodes; no dynamic road-closure semantics
  were introduced.
- This is M2 implementation evidence. No claim about treatment improvement,
  algorithm superiority, statistical significance, formal experiments, or
  deployment is supported.
- Validation remains inaccessible and sealed-test access remains forbidden.
  Task 7, pilots, formal jobs, and project-state persistence were not started.
