# HANDOFF PLANG4

Date: 2026-08-21
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g3-heterogeneous-marl`

## What We Are Doing

We are preparing G4 for the second thesis problem: resource-scarcity activation
and counterfactual mechanism probes for the air-ground heterogeneous SR-MAPPO
system with pesticide-only replenishment.

G4 is a mechanism gate, not a formal experiment gate. It must verify that the
scarcity mechanism is actually active on the frozen G2 physical foundation and
that fixed versus mobile support produce comparable, reproducible differences
under identical non-sealed conditions.

## Current Progress

- G0 through G3 are complete.
- G3 passed at `M2` and its evidence and persistence records are already
  recorded in `docs/PROJECT_STATE.md`.
- G4 is the next authorized gate.
- The G4 design spec has been drafted at
  `docs/superpowers/specs/2026-08-21-g4-resource-scarcity-counterfactual-design.md`.
- The G4 execution plan has been drafted at
  `docs/superpowers/plans/2026-08-21-g4-resource-scarcity-counterfactual.md`.
- No G4 code, tests, or output artifacts have been implemented yet.
- The working tree is still in the planning stage, not the implementation stage.

## What G4 Must Do

1. Freeze a fail-closed scarcity band and probe manifest.
2. Run resource-scarcity activation probes on the frozen G2 engine.
3. Run fixed-versus-mobile counterfactual probes with identical inputs.
4. Write all G4 evidence under `outputs/problem2_sr_mappo_v1/g4`.
5. Keep validation and sealed-test access blocked.
6. Preserve the frozen G3 learning interface as lineage only, not endpoint
   evidence.

## Biggest Failure Modes

- Reusing G3 smoke as endpoint evidence.
- Letting the scarcity band drift open-endedly instead of freezing it fail-closed.
- Allowing validation or sealed-test seeds, outputs, or claims to leak into G4.

## Next Step

Start Task 1 from the G4 plan:

- create `docs/evidence/g4/g4_contract.yaml`;
- create `docs/evidence/g4/g4_probe_manifest.yaml`;
- implement `src/problem2/experiments/g4_contract.py`;
- add the first contract tests under `tests/g4/`.

After Task 1, continue with the activation probe, then the counterfactual
summary and audit, and finally the G4 handoff/persistence step.

## Guardrails

- Keep the public algorithm name `SR-MAPPO`.
- Keep pesticide as the only replenished resource.
- Keep battery replenishment inactive.
- Do not touch first-problem assets or thesis Word files.
- Do not claim superiority, deployment evidence, or formal experiment results
  at G4.
