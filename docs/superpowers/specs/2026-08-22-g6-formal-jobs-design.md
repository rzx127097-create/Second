# G6 Immutable Formal-Jobs Design

## Status

The G5-G7 architecture was approved in chat on 2026-08-22. This document is
the written G6 specification submitted for user review. G6 may begin only after
the reviewed G5 specification has been implemented, verified, frozen, pushed,
and recorded as passed in `docs/PROJECT_STATE.md`.

## Purpose and Gate Boundary

G6 executes the frozen training and validation-evaluation manifests. It does
not design algorithms, tune methods, change statistics, or access the sealed
test. Its purpose is to turn the G5 protocol into complete, immutable,
recoverable, and auditable job evidence.

All scientific and orchestration code required by G6 is written and tested in
G5. If G6 reveals a code, configuration, estimator, logging, schema, or
checkpoint-selection defect, execution stops. The repair occurs by reopening
G5, rerunning affected pilots, creating new hashes, and freezing a replacement
manifest. A patched job must never be hidden under its old identity.

G6 can report job completion, validation behavior, resource consumption, and
data-quality status. It cannot claim that a method formally outperforms another
method because sealed-test evaluation and locked paired inference occur only in
G7.

## Entry Contract

G6 preflight must verify all of the following against the pushed G5 freeze:

- repository source is clean, on the recorded `codex/` branch, and at the
  exact frozen Git commit;
- local HEAD, upstream HEAD, and remote branch head match;
- method, experiment, seed, scale, budget, checkpoint-selection, exclusion,
  and statistics manifests match their registered SHA-256 hashes;
- the G4 evidence lineage reconciliation passed;
- the complete G5 test/audit suite passed on the frozen source;
- road caches match source GraphML, CRS/bbox, grid shape, topology checksum,
  and source-code version;
- the output root resolves below `outputs/problem2_sr_mappo_v1`;
- sufficient disk space exists for all checkpoints, raw logs, validation rows,
  and temporary atomic writes;
- the visible CUDA device, PyTorch/CUDA versions, GPU model, VRAM, CPU, RAM,
  operating system, and Python environment are recorded;
- the sealed lock reports maximum unlock count `1`, actual count `0`, and no
  G6 path or manifest contains a sealed scenario ID.

A failed preflight creates an audit record and starts no training process.

## Frozen Workload

### Base Algorithm Matrix

The mandatory five-algorithm, six-scale matrix is:

```text
5 methods x 6 scales x 5 training seeds = 150 training jobs
```

Methods are `sr_mappo_mobile`, `mappo_mobile`, `ippo_mobile`,
`maddpg_mobile`, and `iql_mobile`. Scales and maximum physical decision steps
remain:

| Scale | Maximum physical decision steps |
|---|---:|
| `g20x20_d2` | 150 |
| `g20x30_d3` | 180 |
| `g20x40_d3` | 220 |
| `g30x30_d3` | 220 |
| `g30x40_d4` | 280 |
| `g30x50_d4` | 350 |

Training seeds are `42`, `123`, `2024`, `3407`, and `7919`.

### Additional Families

The G5 frozen manifest also includes the nonduplicate jobs needed by:

- `sr_mappo_fixed`, `sr_mappo_astar`, and `sr_mappo_two_stage` in the required
  Problem-2 family;
- `sr_mappo_nearest` and `sr_mappo_urgency` in the heuristic family;
- five SR-MAPPO remove-one conditions at `g30x30_d3`;
- ten noncenter algorithmic-sensitivity configurations at `g30x30_d3`.

The center point, SR-MAPPO mobile, MAPPO mobile, and A* jobs already present in
another family are referenced rather than rerun when their full canonical job
identity and selection protocol match. Mechanism-sensitivity conditions are
evaluation jobs over frozen nominal checkpoints, not new training jobs.

Nearest and urgency heuristic jobs run at all six scales. The exact formal
training workload after deduplication is:

```text
150 base five-algorithm jobs
+ 90 fixed/A*/two-stage Problem-2 jobs
+ 60 nearest/urgency heuristic jobs
+ 25 remove-one ablation jobs
+ 50 noncenter algorithmic-sensitivity jobs
= 375 unique training jobs
```

The final generated manifest records the raw count, the exact `375` unique
jobs, dependency graph, estimated storage, and expected GPU time. G6 rejects
any manifest whose base matrix is not exactly `150`, whose total is not exactly
`375`, or whose deduplication merges nonidentical configurations.

## Immutable Identity and State Machine

The canonical training identity is the SHA-256 of:

```text
method|scale|training_seed|config_hash|git_commit
```

The full run record also contains:

```text
experiment_family|condition_id|protocol_hash|canonical_training_identity
```

Evaluation identity additionally binds checkpoint hash, partition, scenario
panel hash, deterministic-policy flag, and evaluator hash. Human-readable run
IDs are labels only; the hash identity is authoritative.

Each job follows:

```text
pending -> running -> completed
                 |-> failed -> pending (same identity retry only)
                 |-> stale  (hash/input drift; never resumed)
```

State transitions are append-only events with UTC time, host/process identity,
attempt number, prior state, new state, reason, and artifact hashes. A lease
prevents duplicate workers from running the same identity. Orphaned `running`
jobs become recoverable only after the recorded process/lease check fails.

## Scheduler and Hardware Policy

The default hardware is the 8 GB RTX 4060 Laptop GPU. Exactly one GPU training
job runs at a time. CPU road-cache checks, log validation, and statistics may
run concurrently only when they do not contend for a file being written and do
not materially change GPU thermals or training timing.

The scheduler order is deterministic and frozen in the manifest. It
interleaves methods across seed/scale blocks so that a long hardware drift does
not affect one method exclusively. CUDA device, driver, temperatures if
available, peak allocated/reserved memory, runtime, and energy proxy if
available are logged per attempt.

An OOM does not authorize a smaller network, batch, replay buffer, or horizon.
The job fails with diagnostics. Any scientific change returns to G5. Pure
process controls such as restarting the same identity after releasing leaked
memory are allowed and recorded.

## Atomic Checkpoints and Exact Resume

Every checkpoint must contain the method-specific complete state defined in
G5, including:

- online policy/value/Q networks for both roles;
- optimizers and schedulers;
- target networks and target-update counters for MADDPG/IQL;
- role observation and return normalization state;
- replay content/index or on-policy rollout position;
- exploration, Gumbel-temperature, curriculum, and sampling state;
- environment episode/interaction/update counters;
- Python, NumPy, CPU Torch, CUDA, and environment RNG states;
- method/config/protocol/source/scenario hashes.

The writer serializes to a same-filesystem temporary path, flushes and closes
it, verifies reload and SHA-256, then atomically renames it. A manifest update
is atomic and occurs only after checkpoint validation. The previous valid
checkpoint is retained until the new one is committed.

Resume must reproduce the uninterrupted next action, next sampled batch, loss,
network update, counter progression, and emitted identity within declared
numeric tolerance. If replay content is too large for every periodic
checkpoint, the frozen G5 contract must use deterministic replay snapshots or
an append-only replay journal; G6 cannot invent a recovery shortcut.

## Training and Periodic Validation Flow

For each canonical training job:

1. verify job inputs and acquire the lease;
2. initialize or load the latest verified checkpoint;
3. execute the next frozen interaction block;
4. validate finite actions, rewards, losses, gradients, resource accounting,
   and monotonic counters;
5. atomically write checkpoint and training-event records;
6. at frozen checkpoints, run deterministic evaluation on the frozen
   validation panel `20000-20049` with learning and normalization updates off;
7. validate raw validation records and append their manifest entries;
8. mark complete only after all expected blocks and validation rows exist.

Periodic validation uses exactly the same scenario IDs and checkpoint schedule
for all comparable methods. Validation may select checkpoints through the
already frozen G5 rule; it cannot generate new candidate configurations.

After a training job completes, its selected checkpoint is determined by mean
validation reduction rate, then validation success probability, then earlier
interaction count, then lexicographically smaller checkpoint hash. The
selection record contains all candidate rows, not only the winner.

## Validation and Artifact Audits

G6 continuously detects and fails closed on:

- NaN/Inf in state, action distribution, Q/value prediction, reward, loss,
  gradient, parameter, or metric;
- OOM or unexpected device fallback;
- missing, duplicate, truncated, or malformed JSONL records;
- nonmonotonic episode, interaction, update, or checkpoint indexes;
- config, source, protocol, scenario-panel, road-cache, or checkpoint hash
  drift;
- wrong role dimensions, masks, illegal actions, or critic-only actor input;
- resource nonconservation, negative pesticide, or battery replenishment;
- inconsistent termination, horizon, success threshold, or metric units;
- incomplete method/scale/seed/condition cells;
- validation or training rows written below the wrong partition;
- any sealed scenario ID or sealed-access flag.

Each raw episode has a stable source-row locator. Validated long tables are
generated mechanically and never hand-edited. Invalid rows remain in a
quarantine report with reason and source hash; they are not silently dropped.

## Retry, Recovery, and Replacement Rules

A transient failure may be retried only with the same full identity and frozen
inputs. Every attempt is retained. The first successful complete attempt
becomes canonical according to the frozen attempt-selection rule; later
duplicate successes are flagged rather than averaged.

A job becomes `stale` instead of `failed` when code, config, protocol, source
data, checkpoint ancestry, or scenario panel differs. Stale jobs cannot be
resumed or reused as evidence.

When a scientific defect is discovered:

1. stop the queue at the first affected job;
2. preserve existing raw artifacts and the failure report;
3. mark all dependent jobs stale;
4. return to G5 for code/config/spec repair and pilot verification;
5. issue new hashes and new job identities;
6. regenerate the complete affected manifest before resuming G6.

No result is manually overwritten. No unfavorable completed job is rerun with
a new seed or altered configuration.

## Output Layout

All G6 outputs remain below:

```text
outputs/problem2_sr_mappo_v1/g6/
  manifests/
  jobs/<canonical-job-id>/
    attempts/
    checkpoints/
    training-events.jsonl
    validation-episodes.jsonl
    selected-checkpoint.json
    provenance.json
    artifact-manifest.json
  validated/
  audits/
  recovery/
```

Large checkpoint/replay artifacts may use a documented Git-external storage
location only if the repository manifest records an immutable locator, bytes,
SHA-256, retention policy, and verified restore test. Raw result identity and
manifests remain in the repository evidence chain.

## G6 Deliverables

G6 produces:

- preflight and hardware/environment reports;
- exact raw and deduplicated job manifests;
- append-only job-state and attempt ledgers;
- atomic checkpoints and checkpoint manifests;
- complete training diagnostics and deterministic validation episode logs;
- selected-checkpoint records with validation justification;
- validated long tables for training/validation evidence;
- matrix-completeness, identity, hash, resource, and partition audits;
- recovery/retry/stale-job reports;
- a G7 sealed-evaluation manifest binding every frozen selected checkpoint but
  containing no sealed result;
- `HANDOFFG6.md` and a pushed project-state record.

## Acceptance and Transition to G7

G6 passes only when:

1. every expected deduplicated training job is completed exactly once or has
   one canonical success after identical-identity retries;
2. the mandatory base matrix contains all 150 method/scale/seed cells;
3. all `375` unique formal training jobs, including every additional
   Problem-2, heuristic, ablation, and algorithm-sensitivity cell, are
   complete;
4. every selected checkpoint is loadable, hashed, and chosen only by the
   frozen validation rule;
5. raw logs, validated long tables, manifests, and recovery ledgers pass all
   fail-closed audits;
6. no scientific code/config/statistics change occurred after the G5 freeze;
7. the sealed lock is still actual count `0`, with zero sealed scenario access;
8. content and persistence commits are pushed and recorded in
   `docs/PROJECT_STATE.md`.

G6 completion does not itself promote a method ranking to formal evidence.
Only after this acceptance may G7 perform the one permitted sealed-test
unlock. Any missing cell, unresolved hash drift, invalid checkpoint, or source
change blocks the transition.
