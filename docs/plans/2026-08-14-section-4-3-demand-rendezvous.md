# Section 4.3 Demand and Rendezvous Integration Plan

## Goal

Implement the deterministic Section 4.3 layer that converts finite UAV
pesticide into a replenishment urgency signal, computes road-constrained
vehicle ETA, generates feasible rendezvous candidates and exposes a fixed-slot
vehicle action mask.

## Contract

- Remaining work time is computed from current onboard pesticide and spray flow
  in seconds; no grid-step shortcut is used.
- Urgency is dimensionless and increases when vehicle ETA or service time
  approaches/exceeds the available work time.
- Vehicle ETA uses the shared weighted `RoadGraph` shortest path and explicitly
  reports unreachable targets.
- A rendezvous candidate is attached to a road node, has deterministic IDs,
  records UAV distance, vehicle road distance/ETA and joint-arrival feasibility,
  and is ordered by the frozen urgency/ETA/identifier rule.
- Service feasibility rejects unreachable, out-of-radius, empty-inventory,
  insufficient-capacity and late-arrival candidates.
- Candidate slots are fixed-width, zero-filled through the existing action-mask
  API, and preserve the exact slot-to-candidate mapping for rollout replay.
- Configuration values remain provisional; no formal experimental claim is
  produced by this implementation.

## Test-first increments

1. Remaining endurance and urgency monotonicity/validation.
2. Road ETA and unreachable-path behavior.
3. Candidate generation, deterministic ordering and metric fields.
4. Service feasibility and fixed-slot mask integration.
5. Full regression, compile check, diff check, commit and push.
