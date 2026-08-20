# HANDOFF G2

Date: 2026-08-20
Repository: `C:/Users/RZX/Documents/ChatGPT/Second`
Branch: `codex/problem2-g2-deterministic-validation`
Base: `aadde5dae026f4737f34cb20927a5a882f71dc81`

## Gate Result

The deterministic G2 implementation and its registered verification suite pass
at maturity `M2`. The content is ready for the required non-rewriting commit and
push, followed by a separate persistence-record commit. Until those two remote
records are verified, this handoff is a pre-persistence record rather than the
authoritative final state.

Permitted claim after persistence:

> The G2 deterministic road, physical-motion, service-state, and pesticide-
> conservation implementation passed its registered verification suite.

This is not evidence that mobile support improves treatment, that SR-MAPPO
outperforms a comparator, that formal experiments exist, or that the OSM input
represents real deployment.

## Implementation And Evidence

Code and tests are in `src/problem2/`, `scripts/`, and `tests/g2/`. The clean
generator commit is `d4dc97d02ede579cb6e8aedf4df65f4d5a47c107`; its generator
tree SHA-256 is
`e43c84d592e55d0925e747d6edcf1c713eb0a93174bfb2bb510a2908831c16f6`.

Generated evidence is under `outputs/problem2_sr_mappo_v1/g2/`:

- six scale directories, each with `road_graph.npz` and `metadata.json`;
- `deterministic-event-trace.jsonl` with 183 canonical events;
- `g2-deterministic-audit.json` with six scale reports;
- `artifact-manifest.json` with 14 hashed artifacts.

The six caches bind source SHA-256
`B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`, source
CRS `EPSG:4326`, target CRS `EPSG:32643`, and the clean generator provenance.
The audit reports zero A*/Dijkstra difference on 120 sampled pairs, zero illegal
masked-action probability, and maximum conservation error
`2.220446049250313e-16 L` against `1e-9 L` tolerance.

## Fresh Verification

- `python -m pytest tests/g2 -q`: `102 passed`.
- `python -m pytest -q`: `158 passed`.
- `python -m compileall -q src scripts`: exit 0.
- `python scripts/preprocess_g2_roads.py --config configs/problem2/g2_deterministic.yaml`: six scales, status pass.
- `python scripts/audit_g2_deterministic.py --config configs/problem2/g2_deterministic.yaml --report outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json`: six scales, replay match, status pass.
- Manifest verification: 14 entries, zero hash/byte mismatches.
- `git diff --check`: exit 0 before documentation edits.

The independent fix-round review marked the original output-root, reservation,
road-state, motion-payload, cache-publication, and cache-provenance findings
addressed, with no new Critical/Important breakage.

## Protected And Locked Boundaries

The read-only GraphML and all Problem 1 repositories, Word files, and external
planning assets were not modified. Pesticide is the only replenished resource;
battery replenishment is inactive. Training seed 42 was used only for the
deterministic replay audit. Validation seeds `20000-20049` and sealed seeds
`30000-30099` were not accessed. Sealed-test unlock count remains zero.

No RL training, G4 activation probe, G5 pilot, formal job, paired statistic, or
sealed evaluation was run. G3 is the next authorized gate. G3 must independently
verify role-local actors, the structured critic, GAE, masks, normalization,
gradient isolation, and checkpoint round trip before any RL training is allowed.
Formal experiments remain prohibited until G5/G6 authorization, and sealed tests
remain prohibited until G7.

## Next Persistence Actions

1. Commit the corrected design note, completed plan, checklist, handoff, and
   regenerated G2 outputs as the content commit.
2. Push `codex/problem2-g2-deterministic-validation` and verify local HEAD,
   upstream HEAD, and `git ls-remote` agree.
3. Record that content hash and the exact fresh verification in
   `docs/PROJECT_STATE.md`, commit the persistence record, push again, and
   recheck all three hashes plus a clean worktree.
