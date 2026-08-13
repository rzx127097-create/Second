# Section 4.2 Road-Constrained Heterogeneous Environment Integration Plan

## Goal

Integrate the existing pesticide domain, road graph, request/service state
machine, role observations/masks and SR-MAPPO rollout interfaces into a tested
road-constrained air-ground environment adapter.

## Scope

- Add a metric road vehicle executor with residual-distance carry-over.
- Add fixed role/action/observation adapters for joint air-ground transitions.
- Add deterministic consistency audits for road membership, one-to-one service,
  action-mask legality, pesticide conservation and seeded event replay.
- Preserve existing low-level modules and the provisional configuration gate.

## Non-goals

- No formal training or experimental results.
- No OSM download during tests or training.
- No battery charging/exchange model.
- No changes to thesis Word files.

## Test-first increments

1. Road executor tests: metric speed, residual distance, graph membership,
   unreachable target and deterministic route progression.
2. Joint adapter tests: stable role slots, action mapping, locked-service mask,
   request/rendezvous mapping and event ordering.
3. Consistency audit tests: conservation, one vehicle/one UAV service lock,
   legal sampled actions, reproducible event signatures.
4. Full regression, compile check, diff check and branch push.

All numeric parameters are supplied by constructor/configuration; no formal
engineering value is introduced in prose or code defaults beyond interface
tests.
