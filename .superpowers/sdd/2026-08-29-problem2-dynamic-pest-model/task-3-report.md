# Task 3 Report: Persistent Pesticide Effect And Dynamic Wind

Date: 2026-08-29
Branch: `codex/problem2-dynamic-pest-model`
Scope: Task 3 only

## Outcome

Task 3 implements the persistent Problem-1-lineage pesticide effect field and
scenario-owned dynamic wind types. The implementation is limited to:

- `src/problem2/ecology/pesticide.py`
- `src/problem2/ecology/scenario.py`
- `tests/ecology/test_pesticide.py`
- `tests/ecology/test_wind.py`

No Task 1/2 source files, plan files, `docs/PROJECT_STATE.md`, outputs, or
protected historical/debug directories were modified.

## Contract Implemented

`AcceptedSpray` is an immutable event carrying an ecology-grid center and a
positive finite physical `delta_l`. `PesticideEffectField.deposit` validates
the center, spray amount, and positive finite reference volume before applying
the approved radial profile:

```text
amount = 0.85 * delta_l / reference_volume_l
weight(distance) = 1 - distance / 5, for distance <= 4
```

The profile uses Euclidean distance, clips the support at the grid boundary,
adds overlapping concentration with a cap of `1.0`, takes the maximum duration
of `15`, and increments only the center spray-count cell. Ecological
concentration, duration, and spray count are separate from physical litre
ledger state; no litre field is accepted into or emitted by the ecological
snapshot.

Mortality returns detached prey and predator arrays using the exact approved
rates:

```text
prey kill = min(concentration * 2.0, 0.98)
predator kill = min(concentration * 0.1, 0.3)
```

Decay decrements duration first, multiplies concentration by `0.92`, clears
expired cells, and clears concentrations below `1e-6`. Snapshots preserve exact
array values and dtypes (`float32`, `float32`, and `int32`) and restore through
detached copies.

`WindState` is immutable and exposes `(strength*cos(direction),
strength*sin(direction))`. `DynamicWind.initialize` samples direction
uniformly on `[0, 2*pi)` and strength uniformly on `[0, 0.5]` from the supplied
`numpy.random.Generator`. Each update applies the independent normal noises,
slow sinusoidal direction term, modulo wrapping, strength clipping, and step
increment from the brief. `state_dict` records the bit-generator name and a
deep copy of its state; `from_state_dict` restores the stream exactly.

## TDD Evidence

### RED

Tests were written before either production module existed. The required
commands failed during collection because the modules were absent:

- `python -m pytest tests/ecology/test_pesticide.py -q`: exit `1`,
  `ModuleNotFoundError: No module named 'problem2.ecology.pesticide'`.
- `python -m pytest tests/ecology/test_wind.py -q`: exit `1`,
  `ModuleNotFoundError: No module named 'problem2.ecology.scenario'`.

After the first implementation, the pesticide suite exposed an error in the
gold test expectation: concentration `1.0` gives predator survival `0.9`, not
`0.7`, because the `0.3` cap is not reached until concentration `3.0`. The
independent test was corrected to use concentration `4.0` for the cap case.

### GREEN

Fresh verification results:

- `python -m pytest tests/ecology/test_pesticide.py tests/ecology/test_wind.py -q`:
  `21 passed`.
- `python -m pytest tests/ecology -q`: `50 passed`.
- `python -m compileall -q src/problem2/ecology`: exit `0`.
- `git diff --check`: exit `0`.

The gold tests cover radial deposition, full and partial physical-volume
scaling, overlap capping, mortality caps, duration order, decay, expiration,
invalid inputs, out-of-bounds centers, state/dtype round trip, immutable wind
state, independent-generator replay, the exact update equation, deep-copy
serialization, and exact post-restore replay.

## Concerns And Deliberate Boundaries

1. `delta_l` is required to be positive and finite, but is not independently
   upper-bounded by `reference_volume_l`; the brief specifies validation of
   positivity/finiteness and defines scaling by their ratio. Physical wrappers
   in later tasks must continue to filter accepted events from the physical
   ledger before calling `deposit`.
2. Ecological snapshots intentionally omit physical pesticide litres,
   replenishment, battery, and ledger residuals. Those remain owned by the
   physical environment and resource-ledger layers.
3. This task creates wind types only. Scenario generation, ecology integration,
   environment wiring, observations, rewards, experiment defaults, and gate
   revalidation remain later plan tasks.
4. The implementation uses the Problem-1 lineage dtypes for the effect arrays;
   no Problem-1 runtime import or output/result import was introduced.
5. No formal, validation, sealed-test, efficacy, superiority, deployment, or
   maturity claim is supported by this task. The project remains at the
   documented M2 boundary.

## Persistence

Implementation commit: `1f046b8` (`feat: add pesticide effect and dynamic wind`).
The report is committed separately after the implementation commit so this
implementation hash is available for the report record.

The task explicitly does not push. The pre-existing untracked directories and
historical G5 files remain protected and untouched.
