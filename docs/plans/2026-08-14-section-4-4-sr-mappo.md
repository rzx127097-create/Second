# Section 4.4 SR-MAPPO implementation record

## Scope

This increment completes the heterogeneous SR-MAPPO algorithm layer used by
the road-constrained air-ground spraying model. It does not run pilot or formal
experiments and does not support a superiority claim.

## Frozen architecture

- One actor is shared by homogeneous UAV slots.
- A separate actor is used by mobile replenishment vehicles.
- A structured global state is consumed only by the central team critic.
- One team reward and one team GAE sequence are computed per joint transition.
- Vehicle candidate mapping and the exact sampling masks are stored in rollout
  data; PPO replay never reconstructs them from later environment state.
- Forced single-action samples remain in critic/GAE data but are excluded from
  the corresponding actor policy and entropy losses.

## SR-MAPPO stability groups

The implementation exposes configuration switches for observation and return
normalization, orthogonal initialization, layer normalization, value clipping,
Huber regression and progress-based learning-rate decay. UAV and vehicle
observation statistics are independent. Deterministic evaluation freezes all
normalization statistics.

## Rollout and recovery contract

Each joint transition preserves raw and behavior-policy observations, agent
identifiers, action masks, sampled actions, masked log-probabilities, value,
team reward and reward components, termination and truncation flags, role-valid
actor samples, candidate mapping and normalization counters. Checkpoints are
written atomically and restore actor/critic parameters, three optimizers,
learning-rate schedulers, normalization states, Python/NumPy/PyTorch RNG states
and CUDA RNG states when available.

## Verification boundary

The MARL tests cover role-gradient isolation, exact zero invalid-action
probability, saved-mask log-probability replay, a hand-computed GAE case,
time-limit bootstrap, valid-sample advantage normalization, multi-UAV role
updates, deterministic evaluation freeze, pessimistic clipped Huber value loss,
component ablation and full checkpoint round-trip. This establishes M2 code and
test evidence only. Parameter activation, multi-seed pilots and sealed tests are
separate later gates.
