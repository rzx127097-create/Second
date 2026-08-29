# G6 Readiness Phase 3 Audit

Date: 2026-08-29

## Scope

Phase 3 has begun after the Phase 2 readiness contracts were pushed. This
record covers executable controller wiring, bounded dynamic G3-G5
revalidation, and the first controlled physical development pilot. It remains
an `M2` engineering milestone; it is not formal G6 execution or G7 evaluation.

## Verification

```text
python -m pytest tests/ecology tests/g3 tests/g4 tests/g5/test_environment_metrics.py tests/g5/test_physical_candidate_training.py tests/g5/test_validation_tuning.py -q --tb=short
361 passed in 371.33s

python scripts/audit_dynamic_pest.py --root . --output outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g3/audits/dynamic-pest-implementation-phase3.json
status=pass

python scripts/run_g5_smoke.py --device cpu --interactions 128 --method sr_mappo_mobile --ecology-mode dynamic
status=pass jobs=1

physical pilot completion validation
completion_validated=true episode_rows=1 dynamic_rows=true ecology_version=problem2-dynamic-pest-v1
validation_accessed=false sealed_accessed=false battery_replenishment_enabled=false
```

The focused controller TDD cycle is recorded in the SDD ledger. The controller
fix enforces slot/request identity before reservation, keeps
`sr_mappo_mobile` sampled vehicle actions, and fails closed for unknown
condition IDs. The scoped review found no Critical or Important issue.

## First Controlled Pilot

The first pilot is the physical dynamic development identity:

```text
method=sr_mappo_mobile
condition_id=sr_mappo_mobile
vehicle_controller=learned
training_mode=joint
candidate_id=c01
scale=g20x20_d2
training_seed=51001
scenario_id=10000
interactions=128
```

The pilot produced one dynamic ecology episode with 128 ecology steps, 25
accepted spray actions, and 0.4875 L sprayed pesticide. The raw episode log,
summary, checkpoint, manifest, and descriptive audit are under
`outputs/problem2_sr_mappo_v1/dynamic_pest_v1/g5/pilots/phase3-first/`.
The completion manifest was revalidated after writing and all artifact paths
and identity fields matched.

## Boundary And Limitations

- New evidence is confined to `outputs/problem2_sr_mappo_v1/dynamic_pest_v1/`.
- Historical static G5 outputs, protected external assets, OSM inputs,
  validation payloads, and sealed payloads were not modified or accessed.
- Validation and sealed access flags remain false; the G7 actual unlock count
  remains `0`; battery replenishment remains disabled.
- The pilot is `noncanonical_test_only` and descriptive. It is not a formal
  result and supports no efficacy, superiority, significance, deployment, or
  optimality claim.
- The dynamic replacement candidate/budget freeze has not yet been regenerated
  from a complete Phase 3 pilot matrix. The first pilot consumed the existing
  frozen candidate/budget inputs read-only; no validation selection occurred.

## Persistence

- Controller wiring commit `913d573239a713e6af4c455e8ded32caaa9de95f` was
  pushed to `origin/codex/problem2-dynamic-pest-model`.
- Dynamic revalidation commit `5d5b9fdea3f0cea8cf18d5761280d10aecd03df7` was
  pushed to the same branch.
- First-pilot evidence commit `61f552b4f93250d72ab0aa3a9770f6a5f7c7baf1` was
  pushed to the same branch.

Phase 3 is intentionally paused after the first pilot. The next authorized
action is another controlled dynamic development pilot, one at a time, after
the completed result has been reviewed. Replacement G5 freeze generation and
Phase 4 preflight remain blocked until the required pilot/refit evidence is
complete.
