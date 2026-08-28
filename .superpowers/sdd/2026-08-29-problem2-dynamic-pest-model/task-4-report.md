# Task 4 Report: Deterministic Dynamic Scenarios And Canonical Identities

Date: 2026-08-29  
Branch: `codex/problem2-dynamic-pest-model`  
Scope: Task 4 only

## Outcome

Task 4 adds deterministic `DynamicPestScenario` generation and strict
canonical state identity in `src/problem2/ecology/scenario.py`, with focused
coverage in `tests/ecology/test_scenario.py`.

The generator derives a stable seed from partition, scenario identity, scale,
grid shape, ecology configuration hash, and implementation version. It uses one
scenario-owned `numpy.random.Generator` and never calls the legacy global
`np.random` state. It generates one or two Gaussian prey sources and one or two
Gaussian predator sources with integer centers in the configured middle-half
coordinate ranges, using the Problem-1-lineage sigma, peak, clip, and float64
semantics. Empty pesticide arrays are constructed before the same generator
initializes dynamic wind.

The accepted partitions are strict:

- `development`: scenario IDs `10000-10019`
- `validation`: scenario IDs `20000-20049`
- `sealed_test`: scenario IDs `30000-30099`

The scenario identity hashes canonical metadata and little-endian contiguous
bytes for prey, predator, concentration, duration, and spray-count arrays.
Metadata binds partition, scenario ID, scale ID, grid shape, ecology config
hash, initial wind, generator bit-generator name and state, the approved
Problem-1 source commit, and implementation version.

`state_dict()` returns detached arrays and nested RNG data. `from_state_dict()`
requires the exact state schema, validates canonical dtypes/domains and
partition identity, reconstructs the generator state for validation, and
rejects any digest mismatch. Scenario-owned arrays are protected read-only;
restored snapshots do not alias their input arrays.

## TDD Evidence

### RED

The required focused suite was written before the production scenario API was
implemented:

```text
python -m pytest tests/ecology/test_scenario.py -q
```

Result: exit `1` during collection with
`ImportError: cannot import name 'DynamicPestScenario' from
problem2.ecology.scenario`. This was the expected missing-generation failure.

### GREEN

Focused verification after implementation:

- `python -m pytest tests/ecology/test_scenario.py -q`: `13 passed`
- `python -m pytest tests/ecology -q`: `74 passed`
- `python -m compileall -q src/problem2/ecology`: exit `0`
- `git diff --check`: exit `0` (Git emitted only its normal LF-to-CRLF
  working-copy warning)

The focused scenario tests cover repeated paired generation, material config
hash changes, legacy global-RNG isolation, strict partition boundaries,
invalid partition/shape rejection, deep-copy restoration, stale hash and dtype
rejection, array bounds/dtypes, approved source commit, and implementation
version.

A repository-wide check was started but was not used as the Task 4 gate. It
reported `797 passed, 4 failed` before interruption. The four failures are the
pre-existing G5 experiment-matrix provenance tests, which reject the intended
dirty working tree while Task 4 source/test files are uncommitted:

```text
RuntimeError: source tree is dirty; frozen provenance cannot be generated
```

No Task 4 failure was reported by the focused or ecology suites. Broad
verification was stopped after this evidence at the user’s request.

## Concerns And Deliberate Boundaries

1. The scenario stores the raw NumPy generator state, whose own
   `bit_generator` field supplies the algorithm identity. This follows the
   existing `DynamicWind` snapshot convention and avoids an extra wrapper.
2. `source_commit` is the approved Problem-1 lineage commit
   `1ca9e5ccc5f77ed775cd2b607dd70d635720accf`; it is not the mutable current
   Problem-2 worktree commit.
3. `from_state_dict()` validates the recorded configuration hash as a
   canonical SHA-256 identity but does not load external configuration. A
   later ecology system must compare that hash with its active config before
   execution.
4. `sealed_test` identity generation is implemented as a pure constructor
   contract only. No sealed scenario was accessed for tuning or evaluation,
   and no sealed-test result was generated.
5. The four repository-wide failures are caused by the existing G5 dirty-tree
   guard and are not fixed within the Task 4 file boundary.
6. No protected external repository, OSM input, historical G5 output, or
   `docs/PROJECT_STATE.md` was modified. No push was performed.

## Persistence

The Task 4 implementation and focused tests are committed locally with the
brief’s requested message:

```text
feat: add deterministic dynamic pest scenarios
```

The resulting commit hash is recorded in the task handoff response. The branch
was not pushed.

## Fix Round 1: Immutable Live RNG State

### Review Finding

Review identified that `DynamicPestScenario.__post_init__` retained the nested
`normalized_rng_state` mapping directly. A caller could mutate
`scenario.rng_state["state"]["state"]`, changing later `state_dict()` output
without changing the stored `scenario_sha256`.

### RED

Added `test_live_rng_state_is_immutable_and_cannot_change_scenario_identity`.
Before the fix:

```text
python -m pytest tests/ecology/test_scenario.py -q
```

Result: `1 failed, 13 passed`. The regression failed because the nested live
RNG mapping accepted the mutation instead of raising `TypeError`.

### GREEN

The scenario now recursively freezes mappings, sequences, and any NumPy array
payload contained in the generator state. `state_dict()` recursively thaws
into detached ordinary containers, and `from_state_dict()` still receives the
raw NumPy generator-state shape and validates it through the existing
bit-generator restoration path.

Fresh verification:

- `python -m pytest tests/ecology/test_scenario.py -q`: `14 passed`
- `python -m pytest tests/ecology -q`: `75 passed`
- `python -m compileall -q src/problem2/ecology`: exit `0`
- `git diff --check`: exit `0`

The pre-existing round-trip test continues to verify equal scenario identity,
wind state, RNG state, and detached snapshot arrays after
`from_state_dict()`. No broad repository test was run during this fix round;
the prior Task 4 report records its unrelated G5 dirty-tree failures.

### Persistence

Fix Round 1 is committed locally with:

```text
fix: freeze scenario RNG identity state
```

The branch was not pushed. No unrelated files, plan, project state, protected
repository, OSM input, or historical output were modified.
