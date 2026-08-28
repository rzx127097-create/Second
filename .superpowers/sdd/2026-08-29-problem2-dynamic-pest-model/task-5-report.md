# Task 5 Report: Ordered Ecology System And Complete State Round Trip

## Scope

Implemented only the Task 5 ecology system and focused tests:

- `src/problem2/ecology/system.py`
- `tests/ecology/test_system.py`

The system consumes `DynamicPestScenario`, `AcceptedSpray`, the pure dynamics
operators, `PesticideEffectField`, and `DynamicWind`. It does not consume
physical actions, resource ledgers, or policy objects. Scenario state is never
deep-copied as an object and no pickle path is used. The live generator is
reconstructed from explicit state and shared with `DynamicWind`.

## TDD Evidence

### RED: missing system module

After the first failing tests were written:

```text
$ python -m pytest tests/ecology/test_system.py -q
ImportError during collection
ModuleNotFoundError: No module named 'problem2.ecology.system'
exit_code=1
```

This failure was caused by the missing production module, as required by the
Task 5 brief.

### RED: cumulative deposited effect

After the first implementation, the additional cumulative-effect regression
test failed:

```text
1 failed, 13 passed
Obtained: 0.425
Expected: 1.275
```

The failure identified that the transition was returning only the current
step's effect. The implementation was then changed to return the cumulative
center-equivalent effect.

### GREEN

The final focused command passed:

```text
$ python -m pytest tests/ecology/test_system.py -q
14 passed in 0.46s
exit_code=0
```

Additional scoped verification passed:

```text
$ python -m compileall -q src/problem2/ecology/system.py tests/ecology/test_system.py
exit_code=0
$ git diff --check -- src/problem2/ecology/system.py tests/ecology/test_system.py
exit_code=0
```

No broad test suite was run.

## Implemented Contract

Each transition executes exactly:

```text
deposit -> wind -> mortality -> substep-1 -> substep-2 -> substep-3 -> decay
```

The system returns direct prey and predator totals, cumulative deposited
center effect, the updated wind vector, and the step count. No-spray steps
still execute wind, mortality, reaction, diffusion, advection, and decay.

`global_summary()` returns 17 values: eight prey/effect field values and nine
predator/wind context values. `local_context(row, col)` returns six reflected
edge-safe local values.

Snapshots contain prey, predator, pesticide arrays, wind state, the shared
current RNG state, counters, reference volume, scenario/config/version
identities, and a canonical SHA-256 state digest. Restoration validates exact
keys, hashes, shape, little-endian dtype, finite/nonnegative domains,
concentration and duration bounds, bit-generator compatibility, matching wind
and top-level RNG state, counters, and the digest before mutating live state.

## Commit

The Task 5 code/test commit is created with the required message:

```text
feat: add ordered dynamic ecology system
```

Per the task instruction, no push was performed and no broad tests were run.

## Fix Round 1

Review findings were verified against the committed Task 5 implementation and
addressed with TDD.

### RED

New tests were added for nested pesticide shape drift, noncanonical
`substeps=4`, an independently hand-derived 17-value summary, reflected local
gradient/neighborhood values, and multiple accepted sprays in the ordering
spy. The first focused run after these tests reported:

```text
6 failed, 14 passed
```

The two intended production failures were:

```text
test_state_restore_rejects_pesticide_shape_drift_even_with_matching_nested_arrays
Failed: DID NOT RAISE ValueError

test_constructor_rejects_noncanonical_substep_count
Failed: DID NOT RAISE ValueError
```

The other four failures were corrected test-fixture expectations: the
float32 concentration mean differs from its decimal hand value by about
`2.6e-8`, and the reflected 2x3 corner neighborhood mean is `0.2`.
After that fixture correction, the clean RED run was `16 passed, 2 failed`,
with only the two review findings failing.

### GREEN

The fix adds an explicit canonical three-substep constant and rejects any
configuration whose substep count is not exactly three. The restore path now
requires a tuple pesticide shape equal to the top-level ecology shape before
constructing the pesticide field. The canonical digest includes the nested
pesticide shape, so shape metadata cannot drift independently of the digest.

The final focused system run passed:

```text
$ python -m pytest tests/ecology/test_system.py -q
18 passed in 0.47s
exit_code=0
```

The ordering spy now submits two sprays and requires both `deposit` calls to
precede `wind`. The summary and local-context tests independently assert
normalization, predator statistics, strict high-density thresholds, reflected
gradients, and the reflected 3x3 corner neighborhood.

## Fix Round 2

### RED

A restore regression was added with a digest-valid snapshot carrying a
`substeps=4` configuration. Before the fix, `load_state_dict(config=...)`
accepted that noncanonical configuration, producing:

```text
1 failed, 19 passed
Failed: DID NOT RAISE ValueError
```

The local-context test set also gained an independent 3x3 hand-derived
interior fixture. At its center, reflected centered differences are
`gradient_x=0.1` and `gradient_y=0.3`, with neighborhood mean `0.4`; the
existing corner neighborhood assertion remains in place.

### GREEN

`load_state_dict` now rejects any supplied configuration whose substep count
is not exactly the canonical value of three before reconstructing or assigning
any live state. The restore test verifies atomicity by comparing the complete
state before and after rejection.

Final focused system verification:

```text
$ python -m pytest tests/ecology/test_system.py -q
20 passed in 0.49s
exit_code=0
```

The full focused ecology suite was then run:

```text
$ python -m pytest tests/ecology -q
95 passed in 1.60s
exit_code=0
```

## Fix Round 3

### RED

A restore regression was added using an alternate `DynamicEcologyConfig` with
`beta=1.4` and the unchanged canonical three-substep count. The candidate
state's `config_hash` and `state_sha256` were both recomputed, so digest
verification alone could not reject it. Before the fix:

```text
1 failed, 20 passed
Failed: DID NOT RAISE ValueError
```

### GREEN

`load_state_dict` now requires the supplied configuration's canonical hash to
equal the immutable `scenario.config_hash`, before any state reconstruction or
assignment. The regression also compares the complete pre-restore state after
rejection, preserving atomicity.

Final focused system verification:

```text
$ python -m pytest tests/ecology/test_system.py -q
21 passed in 0.48s
exit_code=0
```

The complete focused ecology suite also passed after the fix:

```text
$ python -m pytest tests/ecology -q
96 passed in 1.55s
exit_code=0
```
