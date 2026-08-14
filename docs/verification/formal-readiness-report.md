# Formal Experiment Readiness Report

Date: 2026-08-15  
Repository branch: `feature/problem2-code-framework`

## Decision

The repository is ready for deterministic interface checks, field-model
checks, frozen-road pilots and resource-mechanism pilots. It is **not yet
unlocked for formal thesis experiments**. The highest supported maturity remains
**M2**, because external parameter calibration and the sealed-test protocol
have not been independently approved. The gate is intentionally fail-closed.

## Evidence completed

### Parameter evidence ledger

`docs/evidence/parameter-source-ledger.yaml` records the source URL, metadata
status, claim scope and applicability limit for each source. The DJI T40 official
specification page supports a 40 L tank, a maximum pump flow of 12 L/min
(0.2 L/s), a 10 m/s maximum operation speed and a 7 m/s example operating
speed. The registry records the current normalized simulation values together
with explicit scale conversions; they are not presented as the aircraft's
literal tank or flow values.

Eight parameters remain pending external evidence: usable capacity fraction,
support-vehicle inventory, transfer rate, one-service capacity, setup time,
rendezvous radius, support-vehicle road speed and decision interval. The ledger
states the exact equipment manual, transfer test, safety protocol or numerical
convergence record still required for each one.

### Mechanistic field model

The former `smoke_local_removal` branch has been removed from the runtime step.
The scenario now advances a deterministic reaction-diffusion-advection and
pesticide exposure field:

```text
spray deposition -> pesticide advection/diffusion/first-order decay
                 -> pest growth + diffusion - exposure mortality + wind advection
```

The implementation is in `src/problem2/field/` and is configured by
`configs/field_dynamics.yaml`. It enforces non-negativity, carrying-capacity
clipping, explicit diffusion stability and an upwind CFL condition. The
configuration is still `status: provisional`: growth, diffusion, wind,
compound decay and exposure-mortality coefficients require local field,
meteorological, residue and bioassay data before formal use.

### Frozen representative road input

The repository now contains the immutable derivative
`data/roads/jodhpur_cropped_metric.graphml`, generated from the local Jodhpur
GraphML source without network access. Its metadata is in
`docs/verification/frozen-road-jodhpur.json`:

- upstream source SHA-256: `b3af36efbfc87fff30bd61d204283dc40c5b8c83a80ba0ee09f3da5ef52a9462`;
- derived GraphML SHA-256: `62bfda5137bb5e29b46084fe00176313febc4c8d45fffca112c3c8ff3c2fab05`;
- derived metadata SHA-256: `82b9c902baf1376e2a1438b3630b956ef9c5a65d92537dbf49ec2bbc330aa24c`;
- 15 nodes, 18 undirected edges and one connected component;
- explicit metric crop, translation and uniform scale are recorded.

The road source gate passes, but the input remains a representative OSM-based
simulation constraint rather than a surveyed farm road network. The thesis
must use that wording unless a target-farm GIS survey is supplied.

### Resource-activation pilot

The frozen-road pilot was rerun with two episodes at scale `s1`:

```powershell
python scripts/run_resource_pilot.py `
  --config-dir configs `
  --output runs/resource-pilot-frozen/raw.jsonl `
  --report runs/resource-pilot-frozen/activation.json `
  --scale s1 --episodes 2 --max-steps 160
```

It reported `activated: true`, activation fraction `0.75`, and diagnosis
`mixed_total_and_spatiotemporal_constraint`. Teleport service transferred
2.56 L in the pilot; no-support and fixed-support conditions accumulated
pesticide-disabled time; mobile support reduced disabled time but did not
complete a transfer within this short horizon. This is mechanism activation
evidence only, not a claim that mobile SR-MAPPO improves endpoint reduction.

### Practical-equivalence protocol

The protocol now contains a provisional absolute reduction-rate margin of
`0.02` and states its basis: a pre-registered two-percentage-point reporting
tolerance. This removes the missing-field ambiguity, but the basis still needs
supervisor or agronomist confirmation before sealed-test unlock. A positive
number alone is not treated as an agronomic minimum important difference.

## Current gate result

Run the current report with:

```powershell
python scripts/audit_readiness.py `
  --config-dir configs `
  --resource-report runs/resource-pilot-frozen/activation.json `
  --report runs/readiness/formal-readiness.json
```

The road-source gate is now ready. The remaining blockers are:

1. eight engineering parameters still need source records, ranges and unit
   conversions;
2. the field-dynamics coefficients need crop-, wind- and compound-specific
   calibration;
3. scenario, algorithm and protocol registries remain provisional;
4. the practical-equivalence margin needs domain approval;
5. multi-seed pilot and sealed-test evidence have not yet been collected.

`SR-MAPPO` remains the only flagship algorithm name. HAPPO and
`AG-SR-MAPPO` are neither implemented nor registered.

## Claims currently permitted

- “implementation tests verify the field-model invariants and road/service
  interfaces”;
- “the frozen-road pilot activates a finite-resource bottleneck”;
- “the pilot exhibits both total-supply and spatial-temporal mismatch effects”;
- “the current coefficients and normalized engineering values are provisional.”

The following are not yet permitted: formal efficacy, universal scalability,
field deployment validation, or a claim that mobile support is superior.

## Verification commands

```powershell
pytest -q
python -m compileall -q src scripts
git diff --check
```

No Word document was modified. Pilot outputs remain under ignored `runs/` and
must not be copied into the thesis as formal results.

## Unlock checklist

Before changing any registry to `verified`, attach the missing equipment,
field, GIS or expert records to the evidence ledger, rerun the deterministic
audits, freeze the configuration hash and run independent training-seed pilots
on train/validation splits. Only after those checks pass may the formal matrix
and sealed-test freezer be unlocked.
