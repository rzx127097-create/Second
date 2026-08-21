# G4 Handoff: Resource-Scarcity Counterfactual Mechanism

Date: 2026-08-21
Branch: `codex/problem2-g4-resource-scarcity`

## Gate Result

G4 passes its scoped mechanism-activation acceptance at M2 implementation
evidence. The evidence is descriptive and auditable; it does not promote the
project to formal-pilot, formal-experiment, or deployment evidence.

The frozen public method name remains `SR-MAPPO`, and Problem 2 remains its
air-ground heterogeneous extension. The only replenished resource is
pesticide. Battery replenishment is inactive.

## Permitted Claim

The frozen G4 probe set demonstrates that the pesticide scarcity mechanism is
active across the declared band and provides same-input fixed-versus-mobile
counterfactual deltas for `sr_mappo_fixed` and `sr_mappo_mobile`. These deltas
may be used to document mechanism activation and motivate the next pilot.

No claim of superiority, significant improvement, treatment efficacy, formal
experiment, real deployment, or universal optimality is permitted from G4.

## Frozen Interface

- Contract: `docs/evidence/g4/g4_contract.yaml` (`g4.v1`).
- Probe manifest: `docs/evidence/g4/g4_probe_manifest.yaml`.
- Scarcity axis: initial UAV pesticide, `1.0-12.0 L` inclusive.
- Probe scales: `g20x20_d2`, `g20x30_d3`, `g30x30_d3`.
- Probe seeds: `42`, `123`, `2024`.
- Horizons: `150`, `180`, and `220` physical decision steps respectively.
- Counterfactual arms: `sr_mappo_fixed` and `sr_mappo_mobile`.
- Validation and sealed partitions are empty and inaccessible.

The probes reuse the frozen G2 physical/service/conservation semantics and the
frozen G3 learning-interface lineage. G3 smoke artifacts are lineage inputs
only and are not G4 endpoint evidence.

## Verified Evidence

The canonical bundle is under
`outputs/problem2_sr_mappo_v1/g4`. It contains fixed/mobile activation
summaries and provenance, a paired counterfactual summary, a probe-matrix
summary, a provenance index, an artifact manifest, and the fail-closed audit
report. The audit recomputes the counterfactual, verifies SHA-256 hashes, and
reports `status=pass` with activation band `[1.0, 12.0]`.

The paired summary has 27 fixed/mobile input-matched pairs and equal activation
counts of 27 per arm. Conservation errors remain within the recorded
floating-point residuals. These are mechanism-probe observations, not formal
evaluation results.

## Protected Boundaries

- No validation scenario was accessed or tuned.
- No sealed-test scenario was accessed or unlocked.
- Battery replenishment remains false.
- No G3 smoke output is accepted as G4 endpoint evidence.
- OSM data remains simulation input for road-constrained modeling, not field
  deployment evidence.
- First-problem repositories, outputs, and Word thesis files were not edited.

## Exact G5 Entry Condition

G5 may begin only after this handoff and its persistence record are pushed and
the final local/upstream/remote hash check agrees. G5 must first freeze a fair
pilot protocol using the same environment, pesticide budget, horizon,
scenario/seed identities, observability, and information conditions for every
comparison arm. Any validation tuning must be restricted to the declared
validation partition, and formal or sealed evaluation remains prohibited until
the G5 pilot and method/statistics freeze are independently verified.

