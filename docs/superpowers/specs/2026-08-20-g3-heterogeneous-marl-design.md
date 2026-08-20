# G3 Heterogeneous SR-MAPPO Design

## Purpose

This specification defines the implementation and acceptance boundary for G3
of the second thesis problem. G3 validates the heterogeneous MARL interface
that will consume the deterministic G2 environment. It does not claim that
mobile replenishment improves treatment and it does not authorize formal or
sealed evaluation.

The public algorithm name remains `SR-MAPPO`. The implementation is the
air-ground heterogeneous extension of SR-MAPPO:

- one shared UAV actor for homogeneous UAVs;
- one independent vehicle actor;
- one structured centralized team critic;
- role-local execution observations;
- shared team reward and one team GAE per joint transition.

## Frozen G3 Contract

### Roles and dimensions

The primary development contract uses one vehicle and `N=2` UAVs. The actor
dimensions are derived by the observation builder and asserted by tests:

- UAV observation: `43 + 68*N`;
- vehicle observation: `28`;
- structured critic state: `45 + 70*N`;
- UAV action space: `[up, down, left, right, stay, spray]`, six actions;
- vehicle action space: `[hold, slot-0, slot-1, slot-2, slot-3]`, five actions;
- `K_max = 4`.

The dimensions are code-derived contracts, not values copied into prose. A
dimension change must update the G3 configuration, tests, and this document
in the same change.

### Information boundary

Actors receive only their role-local observation and the action mask generated
at the same decision boundary. Actors cannot receive critic-only fields,
future ecological state, future road state, or future service outcomes.

The critic receives a structured vector assembled from ecological, UAV,
vehicle, request/service, and time blocks. The critic outputs one scalar team
value per joint transition.

### Rollout record

Every transition stores:

- role and agent IDs;
- raw role observations;
- normalized policy observations actually passed to actors;
- structured critic state;
- sampled actions;
- exact sampling masks;
- masked old log-probabilities;
- value prediction;
- one shared team reward and reward components;
- `terminated` and `truncated`;
- role-specific `valid_actor_sample`;
- vehicle candidate-slot mapping;
- normalization-statistics versions;
- episode and configuration identities.

PPO replay must use stored policy observations, masks, mappings, and old
log-probabilities. It must never reconstruct them from a later environment
state.

### Optimization

Use team GAE:

```text
delta_t = r_t + gamma * (1 - terminal_t) * V(s_{t+1}) - V(s_t)
A_t = delta_t + gamma * lambda * (1 - trace_done_t) * A_{t+1}
return_t = A_t + V(s_t)
```

Time-limit truncation bootstraps from the terminal observation value; true
termination cuts the bootstrap. Advantages are normalized over exactly the
declared valid population. Forced single-action samples remain in critic and
GAE data but are excluded from the corresponding actor loss using
`valid_actor_sample`.

UAV and vehicle actors have disjoint parameter sets and optimizers. The
critic has its own optimizer. SR-MAPPO stability flags are explicit and
machine-readable:

1. role-separated observation normalization;
2. return/value-target normalization;
3. orthogonal initialization;
4. layer normalization;
5. value clipping;
6. Huber value loss;
7. learning-rate decay tied to declared training progress.

### Checkpoint and evaluation

An atomic checkpoint stores actor, critic, optimizer, scheduler, normalizer,
training progress, configuration/provenance, Python/NumPy/PyTorch RNG states,
and the checkpoint format version. Reloading must reproduce deterministic
actions, critic values, optimizer/scheduler state, normalization statistics,
and the next stochastic sample.

Deterministic evaluation switches modules to evaluation mode and freezes all
normalizer counts, means, variances, and return statistics. It cannot access
sealed scenario IDs.

### Same-source MAPPO

The same-source comparison is represented by the same implementation and
configuration schema with the registered SR-MAPPO stability flags disabled.
The comparison emits a machine-readable configuration diff. It does not
introduce HAPPO or a renamed public algorithm.

## G3 Acceptance Tests

G3 passes only when all of the following are fresh and green:

1. actor parameter and optimizer gradient isolation;
2. exact masked log-prob replay from stored masks and stored policy inputs;
3. zero probability for every invalid action;
4. hand-calculated team GAE;
5. valid-sample-only advantage normalization;
6. configured actor/critic update counts;
7. byte-identical normalizer state before and after deterministic evaluation;
8. checkpoint round trip for policy, value, optimizer, scheduler, normalizers,
   and RNG;
9. actor interfaces cannot access critic-only fields;
10. SR-MAPPO/MAPPO configuration diff contains only declared stability flags;
11. legal G2 environment masks can be converted to role distributions without
    an environment-side action replacement;
12. a controlled non-sealed training smoke runs finite updates and writes a
    provenance-bound checkpoint and raw development log.

The G3 training smoke is engineering evidence only. It does not promote the
project to M3 and does not authorize G4 until the G3 gate report and pushed
state record are complete.

## Boundaries

- No formal matrix jobs.
- No validation or sealed scenario access for tuning during G3.
- No sealed-test unlock.
- No battery replenishment.
- No claim of endpoint improvement or algorithmic superiority.
- G4 remains responsible for resource scarcity activation and counterfactual
  mechanism probes.
