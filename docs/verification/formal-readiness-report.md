# Formal Experiment Readiness Report

Date: 2026-08-15  
Repository branch: `feature/problem2-code-framework`

## Decision

The repository is ready for deterministic checks and controlled-simulation
training pilots after the tested source is committed and the identity-bound
preflight is regenerated. The highest supported maturity remains **M2**:
multi-seed validation pilots and the sealed-test evaluation have not yet been
run. Field calibration is outside the declared controlled-simulation scope and
limits claim strength; it is not a software gate for starting simulation jobs.

## Evidence completed

### Parameter evidence ledger

`docs/evidence/parameter-source-ledger.yaml` records the source URL, metadata
status, claim scope and applicability limit for each source. The DJI T40 official
specification page supports a 40 L tank, a maximum pump flow of 12 L/min
(0.2 L/s), a 10 m/s maximum operation speed and a 7 m/s example operating
speed. The registry records the current normalized simulation values together
with explicit scale conversions; they are not presented as the aircraft's
literal tank or flow values.

Six engineering parameters remain explicit controlled-simulation assumptions:
usable capacity fraction, setup time, request safety margin, rendezvous radius,
support-vehicle road speed and decision interval. They are frozen with units,
ranges and sensitivity levels. Equipment or field evidence would be required
only to reinterpret them as device- or site-specific constants.

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
controlled-simulation profile freezes the coefficients for reproducible
comparison; local meteorological, residue and bioassay data would still be
required for field-effectiveness interpretation.

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

The former 160-step pilot is retired because it truncated the first complete
service cycle. Regenerate the controlled-simulation service probe on the small,
medium and largest scales:

```powershell
python scripts/run_resource_pilot.py `
  --config-dir configs `
  --output runs/resource-pilot/raw.jsonl `
  --report runs/resource-pilot/activation.json `
  --scale s1 --scale s3 --scale s6 --episodes 3
```

The pilot uses common prepositioned road-serviceable work sites and a
deterministic high-demand policy. It is accepted only when all three scales
show requests, actual mobile transfer, resource conservation and finite event
metrics. Its endpoint comparison is deliberately marked invalid; formal
algorithm conclusions require trained policies and paired validation scenes.

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
  --resource-report runs/resource-pilot/activation.json `
  --report runs/readiness/formal-readiness.json
```

Before formal matrix execution, the remaining tasks are:

1. commit the verified source and regenerate identity-bound pilot/preflight
   reports from that commit;
2. freeze scenario, algorithm and protocol registries after validation pilots;
3. approve the practical-equivalence margin before sealed-test unlock;
4. complete multi-seed validation pilots before expanding to the full matrix.

`SR-MAPPO` remains the only flagship algorithm name. HAPPO and
`AG-SR-MAPPO` are neither implemented nor registered.

## Claims currently permitted

- “implementation tests verify the field-model invariants and road/service
  interfaces”;
- “the service probe activates requests and completes mobile pesticide
  transfer while preserving resource conservation”;
- “the current coefficients and normalized engineering values are frozen
  controlled-simulation settings, not field-calibrated constants.”

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
