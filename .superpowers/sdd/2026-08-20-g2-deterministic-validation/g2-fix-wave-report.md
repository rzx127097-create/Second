# G2 Final-Review Fix Wave 1

Date: 2026-08-20
Branch: `codex/problem2-g2-deterministic-validation`
Base: `53e8f39d8d83fe3bb9c10972324b1a9eaf6abd3e`

## Scope

This wave implements the approved G2 final-review corrections only. No
outputs, project-state/handoff documents, protected external assets, OSM
sources, validation/sealed seeds, training code, or formal jobs were modified
or run. The staged `.gitattributes` was preserved for the implementation
commit.

## RED/GREEN Evidence

1. **CLI confinement and dirty-generator bypass.** RED: the new CLI tests
   showed `--allow-test-output-root` was accepted, forged
   `PYTEST_CURRENT_TEST` allowed an external output root, and direct tests
   depended on the bypass. GREEN: both production CLIs removed the flag;
   `resolve_output_root` has no environment bypass; generator provenance always
   rejects dirty G2 code/configuration; success tests use in-process
   `preprocess_all`/`run_g2_audit`; subprocess coverage proves the forged
   environment and removed flag are rejected.

2. **Service reservation lifecycle.** RED: `start_service` accepted PENDING
   requests and only emitted a reservation event. GREEN: `reserve_request`
   creates RESERVED with the owning vehicle, `start_service` accepts only
   RESERVED, and `step_episode` applies reserve then start sequentially while
   retaining both events.

3. **Vehicle road-state validation.** RED: invalid current nodes, secondary
   components, stopped coordinates, and transit coordinates reached masks or
   service paths. GREEN: `validate_vehicle_road_state` checks node range,
   primary component, node-coordinate tolerance, edge/target/direction,
   progress, and interpolated transit coordinates before masks, delay,
   selection, start, and engine steps.

4. **Motion event completeness.** RED: literal payload tests found only action,
   distance, and unused distance. GREEN: UAV and vehicle events now record
   intended action, legal mask, available distance, actual distance, edge
   progress, route distance, boundary clipping, final x/y, and unused distance;
   clipped UAV, in-progress vehicle, and branch-stop payloads are asserted
   literally.

5. **Six-cache transaction.** RED: injected validation corruption changed the
   live second cache, publish injection had no directory swap to fail, and a
   stale backup was not recovered. GREEN: all six pairs stage and reload-
   validate under `.roads-staging-*`, publish as one `roads` directory swap,
   restore `.roads-backup` on failure, recover stale backups on startup, and
   clean all transaction debris. Real generation, validation, publish, and
   recovery fault-injection tests preserve the prior byte-for-byte set.

6. **Cache provenance.** RED: expectation did not include source CRS or
   generator commit. GREEN: `RoadCacheExpectation` and metadata validation
   bind source CRS, target CRS, generator commit, and generator tree hash;
   changed-expectation and tampered-metadata tests fail closed.

7. **Same-class fail-open paths.** RED: negative request margin, frozen GIS/audit
   drift, depleted flag with tiny residual inventory, invalid ledger fields,
   and NaN/infinite ledger conservation were accepted or misreported. GREEN:
   config enforces the frozen contract and nonnegative margin; service selection
   checks `inventory_depleted`; ledger construction and use validate every
   finite nonnegative field; conservation rejects non-finite ledger state.

## Verification

- `python -m pytest tests/g2 -q`: **102 passed**.
- `python -m pytest -q`: **158 passed**.
- `python -m compileall -q src scripts`: exit 0.
- `git diff --check`: exit 0.
- `rg` confirms no production/test occurrence of the removed CLI flag,
  `PYTEST_CURRENT_TEST`, `allow_dirty`, or the obsolete `distance_m` payload
  key.

Formal six-cache/audit CLI generation remains intentionally deferred until
this fix wave is committed cleanly, so the provenance resolver can record the
clean generator commit required by the G2 evidence contract.
