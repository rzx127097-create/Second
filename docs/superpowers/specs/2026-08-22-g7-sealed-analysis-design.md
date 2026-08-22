# G7 Sealed Evaluation and Paired-Analysis Design

## Status

The G5-G7 architecture was approved in chat on 2026-08-22. This document is
the written G7 specification submitted for user review. G7 may begin only after
G6 has completed, passed all audits, been pushed, and been recorded in
`docs/PROJECT_STATE.md`.

## Purpose and Irreversible Boundary

G7 performs the one allowed sealed-test unlock, evaluates frozen checkpoints
on paired sealed scenarios, validates the evidence, runs the pre-registered
statistics and mechanism audit, and locks the summaries that G8 will use.

G7 does not train, update normalization, tune a parameter, choose a new
checkpoint, edit a scientific estimator, change an exclusion, add a favorable
metric, or repair code in place. Once a sealed scenario is read, the actual
unlock count becomes `1` permanently. A defect discovered after that point is
reported and diagnosed; it cannot be concealed by treating the sealed set as a
new validation set.

Formal conclusions remain limited to the simulated, frozen scenarios and
declared uncertainty. No result is evidence of real field deployment or
universal optimality.

## Pre-Unlock Completeness Audit

Before changing the lock, G7 verifies:

- G5 and G6 content and persistence commits exist on the remote and match the
  project state;
- the repository is clean and source/config/protocol/statistics hashes match
  the G5 freeze;
- all G6 expected cells, raw logs, validation tables, selected checkpoints,
  manifests, retries, and recovery records are complete and valid;
- every selected checkpoint was chosen using validation scenarios only;
- all algorithms load in deterministic evaluation mode with byte-identical
  frozen normalization and exploration state before/after a dry run;
- the sealed-evaluation manifest has exact methods, conditions, scales,
  training seeds, checkpoint hashes, scenario-panel hash, metrics, and
  expected row counts;
- the statistical contract has exact estimands, bootstrap seed/replicates,
  practical margins, multiplicity families, and exclusion rules;
- the lock records maximum unlock count `1`, actual count `0`, and no prior
  access event;
- the sealed scenario range is exactly `30000-30099` and disjoint from all
  development, training, and validation identities.

The audit computes the expected number of unique evaluation episodes after
checkpoint and condition deduplication. Any missing field, mismatched hash, or
unresolved G6 failure blocks the unlock.

## One-Time Unlock Protocol

Unlocking is an explicit, append-only state transition:

```text
locked(maximum=1, actual=0)
-> authorized and recorded
-> unlocked(maximum=1, actual=1)
```

The transition record contains UTC time, operator, reason, G5/G6 freeze
commits, evaluator commit/hash, sealed-manifest hash, statistics-contract hash,
previous lock hash, and new lock hash. The `actual_unlock_count: 1` record is
committed and pushed before the first sealed scenario is executed. Console and
audit output must state that the only unlock has been consumed.

Any attempt to unlock when actual count is already `1`, when source is dirty,
or when a required hash differs fails closed. There is no relock-to-zero path
and no second sealed panel.

## Frozen Evaluation Protocol

Every G6-selected checkpoint is evaluated deterministically on scenario seeds
`30000-30099`. For paired inference, all comparable methods use the exact same
scenario IDs, scale, physical horizon, environment parameters, pesticide
budget, service capability, initial-state generator, and information
conditions.

Evaluation enforces:

- model parameters, target networks, optimizers, schedulers, replay buffers,
  and curriculum state are read only;
- observation and return-normalization counts, means, and variances are frozen
  and byte-identical before and after evaluation;
- PPO/MAPPO action selection is deterministic masked argmax;
- MADDPG uses deterministic masked actor argmax with no Gumbel noise;
- IQL uses masked greedy actions with $\varepsilon=0$;
- heuristics use frozen deterministic tie-breaking and no future state;
- environment and scenario RNG streams are checkpoint-independent and bound to
  scenario IDs;
- every episode emits the complete raw schema and direct mechanism metrics.

The primary base matrix alone produces:

```text
5 methods x 6 scales x 5 training seeds x 100 scenarios
= 15,000 sealed episode rows
```

Additional required, heuristic, ablation, and mechanism-sensitivity rows are
calculated from the frozen G7 manifest. The `375` unique trained
method/condition/scale/seed cells produce `37,500` nominal sealed rows.
Mechanism sensitivity at `g30x30_d3` adds ten noncenter environment conditions
for each of five nominal SR-MAPPO checkpoints, or `5,000` rows. The exact total
is therefore `42,500` unique sealed episode rows. Identical
checkpoint/condition/scenario evaluation identities are executed once and
referenced by all applicable families.

## Validation of Sealed Evidence

Raw records are append-only. Each row contains:

- evaluation/run identity and experiment family references;
- method, condition, scale, training seed, scenario ID, and partition;
- source, config, protocol, checkpoint, evaluator, and scenario-panel hashes;
- termination reason and physical interaction count;
- reduction rate and success at 0.85;
- request, completion, rendezvous, waiting, disabled, return, effective-spray,
  transfer, inventory, actual service-travel, idle, and decision-only runtime
  metrics;
- conservation residual, deterministic-policy flag, normalization-frozen
  proof, and battery-replenishment flag.

The validator rejects duplicate evaluation identities, missing expected rows,
non-finite values, stale hashes, wrong scenarios, impossible success flags,
illegal actions, resource mismatch, inconsistent units, incomplete episodes,
or mutation of evaluation state. Rejected rows and original bytes remain in a
quarantine ledger.

A technically interrupted evaluation may resume only at missing immutable
identities with the same source, checkpoint, config, and scenario. It is not a
second unlock because the access count has already been consumed. A scientific
defect cannot be repaired and rerun as if the sealed set were unseen.

## Estimands and Paired Inference

The two primary outcomes are:

$$
\mathrm{reduction\_rate}
= 1 - \frac{P_{\mathrm{final}}}{P_{\mathrm{initial}} + \varepsilon},
\qquad
\mathrm{success}_{0.85}
= \mathbb{I}\!\left(\mathrm{reduction\_rate} \ge 0.85\right),
$$

where $P_{\mathrm{initial}}$ and $P_{\mathrm{final}}$ are total pest amounts
at the start and end of the episode, respectively, and $\varepsilon$ is the
frozen numerical stabilizer from the evaluation contract.

The primary estimand for each registered pair and scale is the mean paired
difference $A-B$, first paired by training seed and scenario.
The training seed is the independent replication level; 100 scenarios from
one trained checkpoint are not treated as 100 independent training
replications.

Hierarchical paired bootstrap is run exactly as frozen in G5:

1. use RNG seed `20260822`;
2. generate `10,000` replicates;
3. resample the five matched training seeds with replacement;
4. within each selected seed, resample shared sealed scenarios with
   replacement;
5. calculate the paired mean difference for each replicate;
6. report the observed difference and percentile 95% interval.

For each result, report effect direction, magnitude, interval, raw per-seed
summary, and practical interpretation. Design-level equivalence margins remain
`0.02` for reduction rate and `0.05` for success probability. An interval
crossing zero is reported directly. Equivalence is not claimed merely because
a null difference is not detected.

Holm adjustment follows the exact confirmatory families frozen in G5. A
comparison appearing in two conceptual discussions is tested once and
referenced twice. Unregistered subgroup, trajectory, runtime, or mediator
analyses are exploratory and cannot replace the primary results.

Unadjusted values use the frozen two-sided hierarchical-bootstrap tail formula
with the plus-one correction before Holm adjustment. Practical equivalence is
declared only when the complete 95% interval lies inside the symmetric G5
margin; a nonsignificant adjusted value alone is not equivalence.

## Convergence and Stability Analysis

G7 does not derive convergence from sealed test trajectories. It locks the G6
validation learning-curve summaries and connects them to the sealed endpoint
results.

For each of the five algorithms and six scales, report:

- normalized validation area under the learning curve;
- observed or right-censored interaction count to the 0.85 threshold;
- restricted mean time to threshold;
- final-window within-run standard deviation;
- across-seed checkpoint dispersion;
- non-finite, invalid-update, clipping, and regression diagnostics;
- sealed reduction and success endpoints from the selected checkpoint.

This separation prevents the sealed set from becoming a checkpoint selector.
A method may converge quickly but finish at a worse sealed endpoint, or appear
stable while having poor efficacy; both facts must be retained.

## Mechanism Audit

The pre-registered mechanism chain is:

```text
mobile support
-> shorter rendezvous distance
-> less waiting and pesticide-disabled time
-> more effective spraying time
-> higher reduction rate and 0.85 success probability
```

G7 evaluates the chain with paired `sr_mappo_mobile` versus
`sr_mappo_fixed` rows. Each mediator is calculated from direct event logs, not
reconstructed from reward. The audit checks sign coherence at scenario,
training-seed, scale, and aggregate levels.

Formal `rendezvous_distance_m` is road-network route length at reservation,
whereas `vehicle_service_travel_m` is realized travel. Waiting is accumulated
request exposure and includes unresolved requests through termination. These
definitions are taken from the frozen G5 schema and must not be replaced by
G4's Euclidean service-start diagnostic metric.

This is called mechanism evidence, not identified causal mediation, unless a
separate valid mediation design exists. Interpretation follows these rules:

- endpoint and intermediate chain improve: mechanism is supported in the
  tested simulation regime;
- endpoint improves without the intermediate chain: endpoint evidence is
  retained but the proposed mechanism is unresolved;
- intermediate chain improves without the endpoint: operational continuity
  improves without demonstrated treatment benefit;
- neither improves: H1 is unsupported in that regime;
- fixed support wins: preserve the result and examine road detour, service,
  policy, and resource-boundary diagnostics.

Joint-learning value uses `sr_mappo_mobile` versus `sr_mappo_astar` and the
other frozen heuristics. SR stability uses `sr_mappo_mobile` versus
`mappo_mobile`. Training-organization value uses `sr_mappo_mobile` versus
`sr_mappo_two_stage`. These comparisons must not be conflated with the causal
mobile-versus-fixed contrast.

## Ablation Analysis

At `g30x30_d3`, full SR-MAPPO is paired with each of the five remove-one
conditions on identical training seeds and sealed scenarios. The audit first
verifies that each condition differs only in its declared stability group.

For each ablation, report both primary outcomes, convergence/stability
summaries, direct training diagnostics, and the Holm-adjusted confirmatory
result. A component is not called necessary solely because the point estimate
falls; uncertainty and the pre-registered practical margin are reported.
Unexpected improvement after removal is retained and discussed as a possible
interaction or over-regularization effect.

## Sensitivity and Boundary Analysis

Algorithmic sensitivity uses the separately trained frozen configurations at
`g30x30_d3`. Mechanism sensitivity applies the frozen nominal checkpoints to
the registered pesticide, vehicle-speed, transfer-rate, setup-time, and
rendezvous-radius levels. Road-detour strata are computed from immutable
scenario geometry.

Analysis reports per-level estimates, paired deltas from the center, monotonic
or nonmonotonic trend diagnostics, scale/seed dispersion, and boundary
conditions. It does not choose a new center, discard inconvenient levels, or
retrain after seeing sealed outcomes. The low onboard-pesticide axis is
described as a simulation scarcity probe rather than an empirical equipment
specification.

## Negative Results and Failure Diagnosis

Negative or mixed results are evidence, not failed storytelling. Diagnosis
uses the frozen order:

1. raw-log, state-machine, mask, resource, and metric correctness;
2. scarcity and service-mechanism activation;
3. physical scale and engineering-range consistency;
4. observation and reward learnability;
5. training stability and validation checkpoint selection;
6. baseline information and budget fairness;
7. genuine absence or boundary of mobile-support or SR-MAPPO value.

No method is weakened, seed removed, metric replaced, or scenario excluded to
improve a ranking. If rolling A*, MAPPO, PPO, MADDPG, IQL, fixed support, or an
ablation wins, the locked result says so.

## Locked Summary and Evidence Chain

Validated sealed rows flow in one direction:

```text
raw sealed episodes
-> validated sealed long table
-> paired statistical and mechanism summaries
-> locked summary manifest
-> G8 figures, tables, and thesis prose
```

G7 writes below:

```text
outputs/problem2_sr_mappo_v1/g7/
  unlock/
  raw/
  validated/
  statistics/
  mechanisms/
  ablation/
  sensitivity/
  audits/
  locked/
```

Every summary records input paths/hashes, evaluator and analyzer commits and
hashes, statistical protocol hash, row count, method/scale/seed/scenario
coverage, creation time, and output SHA-256. Summary files become immutable
after the locked manifest is pushed. G8 may only consume artifacts named by
that manifest.

## G7 Deliverables

G7 produces:

- pre-unlock completeness report;
- pushed one-time unlock transition and access-event ledger;
- complete raw sealed episode logs and artifact manifests;
- validated sealed long-format table and validation report;
- paired estimates, 95% intervals, practical-margin interpretation, and Holm
  adjustment tables;
- five-algorithm convergence/stability and six-scale endpoint summaries;
- required Problem-2 and heuristic comparison summaries;
- mobility-mechanism chain audit;
- full-versus-remove-one ablation summary;
- algorithmic and mechanism sensitivity/boundary summaries;
- negative-result and unresolved-mechanism report;
- locked-summary and provenance manifests;
- `HANDOFFG7.md` and a pushed project-state record.

## Acceptance and Transition to G8

G7 passes only when:

1. the pre-unlock audit passed before access and the single unlock transition
   was committed and pushed;
2. actual unlock count is exactly `1` and cannot be reset;
3. every expected paired sealed evaluation identity is present exactly once or
   has a documented identical-identity technical resume;
4. all learning, normalization updates, tuning, and checkpoint reselection
   remained disabled;
5. raw and validated tables pass identity, hash, schema, conservation,
   partition, completeness, and pairing audits;
6. bootstrap, Holm, mechanism, ablation, and sensitivity outputs reproduce
   exactly from the validated table and frozen contracts;
7. negative and null results remain in the locked summaries;
8. the locked manifest, content commit, persistence commit, and remote hashes
   are recorded in `docs/PROJECT_STATE.md`.

Passing G7 may establish M4 formal simulation evidence for the exact frozen
scope. It does not authorize claims of universal optimality, field deployment,
or agronomic effectiveness beyond the simulated parameter/scenario domain.
G8 may begin only from the locked G7 summaries; no raw result may be manually
transcribed into a thesis figure, table, or conclusion.
