# Step 4 Shared Validation and Sealed-Test Audit

## Scope

This report records the Step 4 execution against Git commit
`571da1c8ff6503b728d222654fa5f14c9d789652`. It is a controlled-simulation
workflow audit, not a formal performance result and not field validation.

## Shared-validation checks completed

- Five-method CPU smoke: 5 completed checkpoint identities covering
  `sr_mappo_mobile`, `sr_mappo_fixed`, `sr_mappo_astar`, `mappo_mobile`, and
  `sr_mappo_two_stage`.
- Smoke validation: 10 strict-valid rows covering both registered s1
  validation scenarios for all five methods.
- Recovery check: a second batch-evaluation call reused all 10 existing rows;
  no evaluation was rerun.
- Controlled-simulation pilot validation: 4 strict-valid rows covering both
  registered validation scenarios for s1 and s6.
- All 14 validation rows have unique run IDs and finite reduction-rate values.
- Deterministic validation records exclude opt-in wall-clock timing, so
  repeated evidence remains byte-stable.

Local evidence roots (intentionally ignored by Git):

```text
runs/chapter45-smoke-step3-rerun
runs/chapter45-pilot-step3-rerun
```

## Sealed-test fail-closed check

The simulation freeze command was deliberately exercised with the currently
available two pilot jobs and four pilot validation rows. It failed with:

```text
validation freeze formal job set is incomplete or contains extras;
missing=570, extra=2
```

No `validation-freeze-step4.json` file was created. A subsequent unlock call
also failed and did not create a sealed-test ledger. Therefore no sealed-test
scenario has been exposed or consumed.

The two pilot jobs use the direct, two-update diagnostic identity and are not
members of the canonical 570-job Chapter 4.5 matrix. They cannot be promoted
to formal jobs.

## Formal Step 4 completion conditions

Before creating a validation freeze, the controlled-simulation matrix must
contain all canonical identities and shared validation rows:

| Family | Required jobs | Required validation rows |
|---|---:|---:|
| Main comparison | 150 | 300 |
| Mechanism | 90 | 180 |
| Sensitivity | 150 | 300 |
| Adaptation | 120 | 240 |
| Ablation | 60 | 120 |
| Total | 570 | 1140 |

Each job must be completed at its registered final update, use the frozen
configuration/protocol/source identity, and be evaluated on both validation
scenarios registered for its physical scale. The provisional 0.02 practical
equivalence margin and its agronomic basis must also be confirmed before the
one-time sealed-test unlock.

## Current gate

The implementation and Step 4 guardrails remain at M2. Permitted wording is
"shared-validation and sealed-test interfaces verified." Formal efficacy,
method ranking, and sealed-test claims are not permitted.
