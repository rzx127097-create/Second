# G4 Resource-Scarcity Activation and Counterfactual Mechanism Design

## Purpose

G4 is the mechanism gate that follows the frozen G3 interface. It verifies
that the pesticide-scarcity mechanism can be activated on the G2 physical
foundation and that fixed versus mobile support produce reproducible
counterfactual differences under identical non-sealed conditions.

G4 is engineering evidence only. It does not authorize formal experiments,
validation tuning, sealed evaluation, or deployment claims.

## Gate Boundary

- Public algorithm name remains `SR-MAPPO`.
- Problem 2 remains the air-ground heterogeneous extension of `SR-MAPPO`.
- The replenished resource remains pesticide only.
- Battery replenishment remains inactive.
- G2 physical motion, service, and conservation semantics remain frozen.
- G3 learning-interface dimensions, masks, and replay contracts remain frozen.
- G4 may read the G3 interface as lineage input, but G3 smoke outputs are not
  endpoint evidence.
- Validation and sealed-test scenarios remain locked.

## Activation Contract

The G4 contract must freeze:

- the scarcity axis and its admissible engineering range;
- the probe scale subset and probe seed subset;
- the fixed-versus-mobile support pair;
- the metrics to record;
- the fail-closed rule for out-of-band probes.

Scarcity is considered active only when the G2 request trigger and service
logic produce a real request/reservation/service cycle caused by limited
onboard pesticide. The activation band is the smallest recorded parameter
interval in which that condition is met for the frozen probe set.

## Counterfactual Comparison

Each paired probe must use identical frozen inputs:

- same scale;
- same probe seed;
- same horizon;
- same resource budget;
- same vehicle/service capability;
- same observation and mask contract;
- same support-policy boundary.

The primary pair is `sr_mappo_mobile` versus `sr_mappo_fixed`. `sr_mappo_astar`
may be included only if the G4 contract freezes it as an auxiliary comparator.

## Required Outputs

G4 writes only below:

```text
outputs/problem2_sr_mappo_v1/g4
```

Required artifacts:

- raw probe log JSONL;
- activation summary JSON;
- counterfactual summary JSON;
- provenance JSON;
- audit report JSON;
- artifact manifest JSON.

Each artifact must bind the probe manifest, configuration hash, source-tree
commit and hash, and output SHA-256.

## Acceptance

G4 passes only if:

1. the activation band is recorded and fail-closed;
2. the paired counterfactual runs complete with finite outputs;
3. no validation or sealed-test scenario is accessed;
4. no G3 smoke artifact is used as endpoint evidence;
5. `docs/PROJECT_STATE.md` and `HANDOFFG4.md` record the pushed content hash
   and the next gate boundary.

The permitted G4 wording is limited to mechanism activation and paired
counterfactual deltas. It must not claim superiority or deployment evidence.
