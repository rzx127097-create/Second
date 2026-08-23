# G4 Lineage Reconciliation

Date: 2026-08-23

## Result

The accepted G4 bundle is reconciled and passes the fail-closed lineage audit.
The canonical artifacts are preserved; regeneration was not required because
the recorded source commit reproduces every source-file and source-bundle hash.

- Status: `pass`
- Canonical evidence content commit: `189e22744579001915919af24ed2bdfd099ff2f2`
- Generator commit: `09d361994100741a9ae834b63ba07c9b5db953e7`
- Generator tree: `5a61825001e92fae112579ae05f5c778deedcab3`
- Source bundle SHA-256: `d2a8a4a4dced015a8f77483d30077b5a24948a97ac1f82b979d6ba968f9df3ed`
- G4 contract SHA-256: `2847f32a64b3d8b80a1e8ec8c5ff56b407ba3abc05cfb1d5780c8a31e18f11ea`
- Artifact manifest SHA-256: `7ec50bd98dedf948cca03179decb09f89071df3cb8d64b699726bc7434a6f56c`
- Artifact manifest bytes: `1718`
- Canonical artifact count: `10`

## Decision

The prior narrative identifiers `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5`
and `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` are not used as the current G4
generator record. The bundle remains unchanged because its embedded lineage
resolves to `09d361994100741a9ae834b63ba07c9b5db953e7`, whose tree, ten source
file hashes, source-bundle hash, contract hash, and artifact manifest all
reproduce exactly.

## Verification Contract

`scripts/audit_g4_lineage.py` checks every JSON/JSONL lineage in the canonical
bundle, resolves each recorded Git object, recomputes the source tree and
source-file hashes, rebuilds the deterministic source-bundle hash, verifies the
G4 contract hash, and checks every registered artifact's SHA-256 and byte count.
It also requires the current G4 handoff, compliance audit, and project-state
acceptance section to reference one exact generator commit/tree/bundle tuple.

The canonical artifact hashes are:

| Path | SHA-256 |
|---|---|
| `activation-summary.json` | `c69a6e342e65b3f565159eb8c1db286e5cf42159f0ffc06619f4c7c5fee2e07f` |
| `counterfactual-summary.json` | `ce77e1720d0818edc7a213f719529209aacc22887262e6b9845c2994c8e9180b` |
| `fixed/activation-summary.json` | `f2b388b4722c16bdd683675b003fbaff9bcebcfd4e5bac6537949f91666d70f5` |
| `fixed/provenance.json` | `a11e3a31d9c108b9f62f4151bc9941b79bd766c466685bb4f689b8e3d3492bef` |
| `fixed/raw-probe.jsonl` | `994bc578554096bdd426eeb982ef67737ba45ff8855a04c6dea6ae977b52e91d` |
| `mobile/activation-summary.json` | `257abed9c273f914b426832bca7498ca653a47aedd56c512d70266066e838b8e` |
| `mobile/provenance.json` | `a11e3a31d9c108b9f62f4151bc9941b79bd766c466685bb4f689b8e3d3492bef` |
| `mobile/raw-probe.jsonl` | `4d5705ab4463d252d4a6f8e52f6298e6ccab805f0d441484b7f118ff6dec510a` |
| `probe-matrix-summary.json` | `b5562c9ca0b72275b784c38e702cbc4bbac8c6071dbd6da2ba1dae79fe226a00` |
| `provenance.json` | `a11e3a31d9c108b9f62f4151bc9941b79bd766c466685bb4f689b8e3d3492bef` |

## Claim Boundary

This reconciliation only establishes provenance consistency for accepted G4
diagnostic support-probe evidence. It does not add treatment-efficacy,
algorithm-superiority, formal-experiment, deployment, or sealed-test claims.
