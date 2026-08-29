# G6 Readiness Phase 3 Audit

Date: 2026-08-29

## Scope

Phase 3 has begun after the Phase 2 readiness contracts were pushed. This
record covers executable controller wiring, bounded dynamic G3-G5
revalidation, and the first controlled physical development pilot. It remains
an `M2` engineering milestone; it is not formal G6 execution or G7 evaluation.

## Verification

```text
python -m pytest tests/ecology tests/g3 tests/g4 tests/g5/test_environment_metrics.py tests/g5/test_physical_candidate_training.py tests/g5/test_validation_tuning.py -q --tb=short
361 passed in 371.33s

python scripts/audit_dynamic_pest.py --root . --output outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation-phase3.json
status=pass

python scripts/run_g5_smoke.py --device cpu --interactions 128 --method sr_mappo_mobile --ecology-mode dynamic
status=pass jobs=1

physical pilot completion validation
completion_validated=true episode_rows=1 dynamic_rows=true ecology_version=problem2-dynamic-pest-v1
validation_accessed=false sealed_accessed=false battery_replenishment_enabled=false
```

The focused controller TDD cycle is recorded in the SDD ledger. The controller
fix enforces slot/request identity before reservation, keeps
`sr_mappo_mobile` sampled vehicle actions, and fails closed for unknown
condition IDs. The scoped review found no Critical or Important issue.

## First Controlled Pilot

The first pilot is the physical dynamic development identity:

```text
method=sr_mappo_mobile
condition_id=sr_mappo_mobile
vehicle_controller=learned
training_mode=joint
candidate_id=c01
scale=g20x20_d2
training_seed=51001
scenario_id=10000
interactions=128
```

The pilot produced one dynamic ecology episode with 128 ecology steps, 25
accepted spray actions, and 0.4875 L sprayed pesticide. The raw episode log,
summary, checkpoint, manifest, and descriptive audit are under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-first/`.
The completion manifest was revalidated after writing and all artifact paths
and identity fields matched.

## Boundary And Limitations

- New evidence is confined to `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/`.
- Historical static G5 outputs, protected external assets, OSM inputs,
  validation payloads, and sealed payloads were not modified or accessed.
- Validation and sealed access flags remain false; the G7 actual unlock count
  remains `0`; battery replenishment remains disabled.
- The pilot is `noncanonical_test_only` and descriptive. It is not a formal
  result and supports no efficacy, superiority, significance, deployment, or
  optimality claim.
- The dynamic replacement candidate/budget freeze has not yet been regenerated
  from a complete Phase 3 pilot matrix. The first pilot consumed the existing
  frozen candidate/budget inputs read-only; no validation selection occurred.

## Persistence

- Controller wiring commit `913d573239a713e6af4c455e8ded32caaa9de95f` was
  pushed to `origin/codex/problem2-dynamic-pest-model`.
- Dynamic revalidation commit `5d5b9fdea3f0cea8cf18d5761280d10aecd03df7` was
  pushed to the same branch.
- First-pilot evidence commit `61f552b4f93250d72ab0aa3a9770f6a5f7c7baf1` was
  pushed to the same branch.
- Raw pilot artifact commit `acd71c396637e1523eb3e6e4b94e0bffc8b93112` was
  pushed to the same branch; it contains the checkpoint, summary, manifest,
  and physical episode log referenced above.

Phase 3 is intentionally paused after the first pilot. The next authorized
action is another controlled dynamic development pilot, one at a time, after
the completed result has been reviewed. Replacement G5 freeze generation and
Phase 4 preflight remain blocked until the required pilot/refit evidence is
complete.

## Phase 3 Continuation: Controller Remediation And Revalidation

After the initial pilot, scoped review identified and closed three development
correctness gaps before further pilot execution:

- physical refit provenance is bound to the learning method even when the
  outer condition is fixed, A*, nearest, urgency, or two-stage;
- fixed support starts at the frozen support node and injected decisions are
  checked for request/slot identity, allowed primary-component node,
  reachability, and exact current A* distance;
- non-learned conditions route observations through the vehicle-isolation
  boundary, keep vehicle replay/optimizer state unchanged while UAV updates
  continue, and bind the executed controller slot into the physical envelope;
- rolling A* reports the current route distance between replans, while active
  reservations retain their locked service node after UAV movement.

The controller task reached a clean scoped review after five fix rounds. The
source-level review artifacts and reports remain in the SDD workspace; the
production commits are listed under Persistence below.

## Post-Fix Verification

```text
python -m pytest tests/g6 -q --tb=short
50 passed in 28.15s

python -m pytest tests/ecology tests/g3 tests/g4 tests/g5/test_heuristics.py tests/g5/test_physical_candidate_training.py tests/g5/test_environment_metrics.py tests/g5/test_end_to_end_smoke.py tests/g5/test_experiment_matrix.py -q --tb=short
381 passed in 450.53s

python scripts/audit_dynamic_pest.py --root . --output outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation-phase3-post-controller.json
status=pass

python -m compileall -q src scripts
exit 0

git diff --check
pass
```

Focused controller/heuristic/isolation checks returned `28 passed`. The
independent A* review found no Critical or Important issue, and the active
service-node regression retained rejection of unrelated nodes.

## Condition Path Revalidation

Each path used method `sr_mappo_mobile`, candidate `c01`, scale
`g20x20_d2`, training seed `51001`, and only development scenario panel
`10000-10019`; each was bounded to 8 physical interactions:

| condition | controller | training mode | vehicle trainable | result |
|---|---|---|---:|---|
| `sr_mappo_fixed` | `fixed_support` | `uav_only` | false | completion validated |
| `sr_mappo_astar` | `rolling_astar` | `uav_only` | false | completion validated after route fix |
| `sr_mappo_nearest` | `nearest_feasible` | `uav_only` | false | completion validated after active-node fix |
| `sr_mappo_urgency` | `urgency_priority` | `uav_only` | false | completion validated |
| `sr_mappo_two_stage` | `learned_two_stage` | `two_stage` | true | completion validated |

Artifacts are under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-controller-checks/`.
The first A* and nearest attempts failed before artifact writes and their
directories remain as preserved attempt markers; they were not overwritten or
silently retried.

## Revalidated First Pilot Identity

Because the controller and environment sources changed after the original
pilot, the same first-pilot identity was rerun in a new directory without
altering the original `phase3-first` artifacts:

```text
method=sr_mappo_mobile
condition_id=sr_mappo_mobile
vehicle_controller=learned
training_mode=joint
candidate_id=c01
scale=g20x20_d2
training_seed=51001
scenario_id=10000
interactions=128
dynamic episodes=1
dynamic ecology steps=128
accepted spray actions=25
sprayed pesticide=0.48750000000000016 L
completion_validated=true
validation_accessed=false
sealed_accessed=false
battery_replenishment_enabled=false
```

The revalidated raw artifact set is under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-first-revalidated/`
and is `noncanonical_test_only` descriptive evidence. It is not a formal
result and supports no efficacy, superiority, significance, deployment, or
optimality claim.

## Continuation Boundary

The dynamic implementation audit, all condition paths, and the revalidated
pilot remain bounded engineering evidence at `M2`. No validation scenario
payload (`20000-20049`) or sealed payload (`30000-30099`) was accessed, the
G7 unlock count remains `0`, and pesticide is the only replenished resource.
Replacement dynamic G5 freeze generation, Phase 4 preflight, formal G6 jobs,
validation selection, and G7 remain blocked. The next authorized action is
still controlled development work toward a complete replacement G5 pilot
matrix, one job at a time.

## Additional Persistence

- `50a053a` routes the physical observation loop through the vehicle-isolation
  boundary; `c4eff19` records its round-5 report.
- `d10d30e` fixes rolling A* current-route validation; `dc21895` records that
  remediation in project state.
- `48e771f` preserves active locked service nodes for heuristic controllers
  and adds nearest/urgency regressions and audit evidence.
- The successful post-fix condition artifacts, revalidated first-pilot
  artifacts, and post-controller dynamic audit are to be recorded in the
  following phase persistence commit.

## Phase 3 Continuation: Matrix Identity 002

The next frozen development identity after the revalidated matrix index `0`
was resolved mechanically from `build_pilot_matrix`: zero-based index `1`.
The historical dynamic audit recorded the label
`05202683b9a9add68cc7e72c8ae6e9adf7fb44dd7d0e47be9ba121ae7c9acb4b`.
Independent recomputation from the frozen `PilotJob.identity` serialization
gives the canonical identity
`05202683b9a9dd60c693b1ab0eb3662ff3dd3731baba7ca45596508273f005b1`.
It keeps method `sr_mappo_mobile`, candidate `c01`, scale `g20x20_d2`, seed
`51001`, and development scenarios `10000-10019`, while executing condition
`sr_mappo_fixed` for 128 physical interactions.

The first invocation failed before any training artifact write because the
manual job mapping omitted the explicit Phase 2 condition-semantics fields.
The failure is preserved as
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-002-fixed/attempt-000001-failed.json`.
The identical identity was then rerun with the frozen execution tuple
`fixed_support`, `vehicle_trainable=false`, and `uav_only`; no method,
candidate, seed, scale, scenario panel, interaction count, or budget changed.

The completed attempt produced one episode and 128 dynamic ecology steps, 22
accepted spray actions, and `0.4275000000000001 L` sprayed pesticide. The
terminal checkpoint round trip passed, all three manifest artifact hashes and
byte counts matched, finite metrics and frozen evaluation were confirmed, and
the physical path completed without a resource-conservation invariant error.
The focused resource/controller regression returned `19 passed in 42.98s`.
An attribute RED/GREEN check also fixed dynamic evidence JSON/JSONL to LF and
checkpoint files to binary so Git checkout conversion cannot invalidate the
recorded byte hashes.

Boundary flags remain `validation_accessed=false`, `sealed_accessed=false`,
and `battery_replenishment_enabled=false`; the sealed unlock count remains
`0`. This is `noncanonical_test_only` M2 engineering evidence. The negative
team reward and increased terminal pest total are retained as descriptive
development observations and support no efficacy or ranking claim.

Artifacts and the per-pilot audit are confined to
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-002-fixed/`.
The replacement dynamic G5 matrix remains incomplete, so replacement freeze,
Phase 4 preflight, formal G6, validation selection, and G7 remain blocked. The
next authorized action remains one new controlled development identity after
review and persistence of this result.

## Matrix Identity 002: Persisted-Provenance Remediation

The first post-persistence strict reload of attempt `2` correctly exposed that
the validator required the generation `source_commit` to equal the current
`HEAD`. Evidence and state commits had advanced `HEAD` even though every
recorded physical execution source hash remained identical. The generation
commit was verified as an ancestor and all three recorded source hashes matched
both its Git blobs and the current working files.

The TDD remediation is recorded in
`docs/audits/g5-persisted-checkpoint-provenance-fix.md`. It permits an ancestor
generation commit only when every other provenance field is unchanged; source
scope drift and non-ancestor commits remain rejected. The fix commit
`0e887e3f41d2c8a18bcd6eb4863c95f0d67ca4bd` was pushed before any rerun.

Because `physical_training.py` belongs to the execution source bundle, the same
matrix identity was rerun as attempt `3` under that exact pushed commit. Its
checkpoint, summary, physical log, and manifest are under
`phase3-matrix-002-fixed/attempt-000003/`. The runner returned
`completion_validated=true`; all identity, controller, dynamic ecology, and
access fields matched the frozen job. Attempt `3` exactly reproduced attempt
`2` for interaction count, team reward, initial/final pest totals, accepted
spray count, sprayed pesticide, dynamic step count, and ecology scenario hash.

Attempt `2` remains byte-preserved historical development evidence but is
superseded for current-source revalidation by attempt `3`. No new matrix
identity, validation scenario, sealed scenario, battery replenishment, formal
job, or replacement freeze was introduced.

## Phase 3 Continuation: Matrix Identity 003

The next uncovered frozen development identity was resolved mechanically from
`build_pilot_matrix`: zero-based index `2` of `510`, identity
`5e48578dcbc0bd88d4fb6391c8fad51c9f8566335964068a96bb8f525b3ff260`.
The exact execution tuple was:

```text
method=sr_mappo_mobile
condition_id=sr_mappo_astar
vehicle_controller=rolling_astar
vehicle_trainable=false
training_mode=uav_only
candidate_id=c01
scale=g20x20_d2
training_seed=51001
scenario_ids=10000-10019
interactions=128
```

One attempt completed under source commit
`3b69fd15566e89707d721e8e12d7912572d3164e`. Strict checkpoint reload,
the three-entry manifest, all artifact SHA-256 values and byte counts, exact
identity and controller semantics, finite metrics, frozen evaluation state,
and development-only access flags were independently revalidated. The focused
heuristic/environment/controller/resource regression returned `43 passed in
40.67s`.

The completed episode contains `128` dynamic ecology steps, `30` accepted
spray actions, and `0.5750000000000003 L` sprayed pesticide. The observed team
reward was `-0.009897712772544845`; total pest changed from
`9.088605068072038` to `9.178561470538911`. These values are retained as
descriptive M2 observations without selection or suppression. They do not
support an efficacy or method-ranking claim.

Artifacts and the machine-readable audit are confined to
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-matrix-003-astar/`.
The audit records `validation_accessed=false`, `sealed_accessed=false`,
`battery_replenishment_enabled=false`, and sealed unlock count `0`. Pesticide
remains the only replenished resource.

The replacement matrix remains incomplete. Replacement G5 freeze generation,
Phase 4 preflight, formal G6, validation selection, and G7 remain blocked. This
pilot is `noncanonical_test_only` development evidence at maturity `M2`.

## Pilot Identity Reconciliation And Executable Matrix Repair

The historical `phase3-matrix-002-fixed/pilot-audit.json` retains the
manually recorded identity label
`05202683b9a9add68cc7e72c8ae6e9adf7fb44dd7d0e47be9ba121ae7c9acb4b` as
byte-preserved evidence. That label does not hash to the identity payload in
the historical or current `PilotJob.identity` implementation. The canonical
identity for its exact tuple is
`05202683b9a9dd60c693b1ab0eb3662ff3dd3731baba7ca45596508273f005b1`, which
also matches the old static pilot artifact for the same method, condition,
scale, seed, partition, and scenario panel. The discrepancy is therefore
classified as a historical audit-label typo, not an execution or checkpoint
identity change. No historical output was modified, relabeled, or used as a
replacement canonical artifact.

The executable replacement pilot matrix is now an explicit condition-to-method
mapping: each condition is paired only with the method and controller path that
can execute it. It contains 20 conditions, five learning methods, two scales,
three development training seeds, and one scenario-reference job per tuple,
for `120` jobs and `2,400` descriptive scenario-reference rows. The first
three canonical identities remain stable for the historical mobile, fixed,
and rolling-A* tuples; subsequent indices are recomputed from this 120-job
matrix and must not be inferred from the obsolete 510-job Cartesian product.

The old static `outputs/problem2_sr_mappo_v1/g5/` pilot/refit artifacts remain
read-only historical diagnostics and cannot satisfy the replacement freeze
counts. The replacement dynamic freeze, Phase 4 preflight, formal G6,
validation selection, and G7 remain blocked until the complete dynamic pilot
matrix and its refit are freshly generated and audited.
