# G4 Lineage Reconciliation

Date: 2026-08-29

## Result

The accepted G4 bundle is reconciled to the lineage emitted after the dynamic
ecology evidence-contract hardening and passes the fail-closed lineage audit.
The canonical artifacts are preserved with their regenerated audit hashes.

- Status: `pass`
- Canonical evidence content commit: `189e22744579001915919af24ed2bdfd099ff2f2`
- Generator commit: `af0c0b1641f1da3ac8bc2fae5faccae47c1ca14e`
- Generator tree: `c35d1977b910944eba50ea3456bdb6c830aba575`
- Source bundle SHA-256: `d2a8a4a4dced015a8f77483d30077b5a24948a97ac1f82b979d6ba968f9df3ed`
- G4 contract SHA-256: `2847f32a64b3d8b80a1e8ec8c5ff56b407ba3abc05cfb1d5780c8a31e18f11ea`
- Artifact manifest SHA-256: `e5c7f158320c4000c27ebb3fe9f973c8685cd11d1b4cb2bbecf03c0e10925523`
- Artifact manifest bytes: `1718`
- Canonical artifact count: `10`

## Decision

The prior narrative identifiers `4e81567aef9eaf7eca676471370bd4b7f3a1a4e5`
and `ee0d3fafdbb8714ed84eb8ede26d5dc82ebbf0bb` are not used as the current G4
generator record. The embedded lineage resolves to
`af0c0b1641f1da3ac8bc2fae5faccae47c1ca14e`, whose tree, ten source file
hashes, source-bundle hash, contract hash, and artifact manifest reproduce
exactly.

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
| `activation-summary.json` | `26a7551cf648924c582b1573fe97db70b0052843db59ce0b58363bdc5f7f7f0a` |
| `counterfactual-summary.json` | `ce77e1720d0818edc7a213f719529209aacc22887262e6b9845c2994c8e9180b` |
| `fixed/activation-summary.json` | `da4b13758a9a13ba4e888fe4ed0b569167b9225b6807c2c979f82d1286360c8c` |
| `fixed/provenance.json` | `0ef50e2fa0df05bc80326d7458bb739abe05a5aaabca7092c02dd39c19d9e00e` |
| `fixed/raw-probe.jsonl` | `5ccd4f2499f30f04022eddc1c76120d21f3b4eca73ffe25fd7616c7a150fd92a` |
| `mobile/activation-summary.json` | `b07f5f067d3c80dd30b67c799c7064bec4bd80f96153d11f6a58e3f84d3d635b` |
| `mobile/provenance.json` | `0ef50e2fa0df05bc80326d7458bb739abe05a5aaabca7092c02dd39c19d9e00e` |
| `mobile/raw-probe.jsonl` | `cf79e8e81f3dc642a804d0fc0824bc25c96f4839440b8d93488107098b96e49b` |
| `probe-matrix-summary.json` | `a1e83795b7456be2e859c2eaaf0d08bb12204af73683a8f7cc589b8462e479b4` |
| `provenance.json` | `0ef50e2fa0df05bc80326d7458bb739abe05a5aaabca7092c02dd39c19d9e00e` |

## Claim Boundary

This reconciliation only establishes provenance consistency for accepted G4
diagnostic support-probe evidence. It does not add treatment-efficacy,
algorithm-superiority, formal-experiment, deployment, or sealed-test claims.
