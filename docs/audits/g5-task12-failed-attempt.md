# G5 Task12 Failed Candidate-Training Attempt Audit

## Disposition

This is an append-only audit of the stopped first Task12 candidate-training
attempt. The attempt was generated under source commit
`374bacbb3bb3a0db25015c88f98340cdfe73cfdc` in
`outputs/problem2_sr_mappo_v1/g5/validation/` before the physical-training
remediation was complete. It is invalid evidence and must never be recovered
as a candidate, validation, refit, formal, or sealed result.

The attempt failed because it used the synthetic Task10 runner rather than the
frozen physical environment, saved pre-update policy state while summaries
described post-update diagnostics, and accumulated full pending/replay state in
large checkpoints. The observed artifacts also lack the canonical validation
long-table identity and were produced before the remediation's strict
completion-manifest contract. `validation_accessed` and `sealed_accessed` were
false in the observed metadata; no validation row or sealed scenario content
was consumed.

Inventory was captured before quarantine on 2026-08-28. The root contained 74
files totalling 23,745,482,266 bytes: 17 checkpoint files, 16 JSONL training
logs, 30 JSON manifests/summaries, 10 text logs, and one zero-byte temporary
checkpoint file. Hashes below are SHA-256 of the exact bytes at capture time.

## File Inventory

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `training-logs/ippo_mobile.err.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/ippo_mobile.out.log` | 444 | `7326301b426aa4a22e4c762ea3674ceb62e9c426a476233c6b907a7ffb20057f` |
| `training-logs/iql_mobile.err.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/iql_mobile.out.log` | 550 | `9b41f78cf6a2cefc18f8a4346c76888c710996e542c7aa0086b9970623d1a668` |
| `training-logs/maddpg_mobile.err.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/maddpg_mobile.out.log` | 678 | `47df49425821ec3420cacd6cc4f70574dd154315aa23482445a22752dfe8f14d` |
| `training-logs/mappo_mobile.err.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/mappo_mobile.out.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/sr_mappo_mobile.err.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training-logs/sr_mappo_mobile.out.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training/ippo_mobile/c01/51001/ippo_mobile__ippo_mobile__51001/checkpoint.pt` | 1640406549 | `26f932e8c07af79175f3438230c327bb06a0a07c22d59c30867b1c4a0f37531f` |
| `training/ippo_mobile/c01/51001/ippo_mobile__ippo_mobile__51001/manifest.json` | 1673 | `acdd358af889b2aaf078b7fa53f287840a5f4489caf86da3237581bad124407b` |
| `training/ippo_mobile/c01/51001/ippo_mobile__ippo_mobile__51001/summary.json` | 2881 | `07c90b809e2436b33925a5b28c74283a64158730252e86d742b79d5d9544c8fe` |
| `training/ippo_mobile/c01/51001/ippo_mobile__ippo_mobile__51001/training.jsonl` | 88488895 | `e8ba4435ca7bd2914b187aed3d0310a9c69f53f8b1ee58899c5a48b6a00c3899` |
| `training/ippo_mobile/c01/51002/ippo_mobile__ippo_mobile__51002/checkpoint.pt` | 1640593749 | `9c8549b3cfc0d13d80da5c4f2e627fbe09572be5ed18a40e55cff74cbe3cdead` |
| `training/ippo_mobile/c01/51002/ippo_mobile__ippo_mobile__51002/manifest.json` | 1673 | `bb5749d7541aa158a457320e81e7eec9c3bfb4a43ad0bc360c4fd1b25cea95eb` |
| `training/ippo_mobile/c01/51002/ippo_mobile__ippo_mobile__51002/summary.json` | 2879 | `759f1cd90c4449132e152878216a2d2cb007edb51192a2f89930022b40ef7b16` |
| `training/ippo_mobile/c01/51002/ippo_mobile__ippo_mobile__51002/training.jsonl` | 88488895 | `e8ba4435ca7bd2914b187aed3d0310a9c69f53f8b1ee58899c5a48b6a00c3899` |
| `training/ippo_mobile/c01/51003/ippo_mobile__ippo_mobile__51003/checkpoint.pt` | 1640106325 | `aa5f669345c1293dfb413241e832700812cc79dca822ea7cf56028b0f5592ef6` |
| `training/ippo_mobile/c01/51003/ippo_mobile__ippo_mobile__51003/manifest.json` | 1673 | `7a048eb037e8383aa7c180ed417c8c980575d4ea616ace79173aff936b0fd345` |
| `training/ippo_mobile/c01/51003/ippo_mobile__ippo_mobile__51003/summary.json` | 2882 | `c05b6c236e9a98141909dfa3920458b1e91e4b7223f1f7497b3e0bb13555695f` |
| `training/ippo_mobile/c01/51003/ippo_mobile__ippo_mobile__51003/training.jsonl` | 88488895 | `e8ba4435ca7bd2914b187aed3d0310a9c69f53f8b1ee58899c5a48b6a00c3899` |
| `training/ippo_mobile/c02/51001/ippo_mobile__ippo_mobile__51001/checkpoint.pt` | 1640406549 | `c25fac1962ce347396e03c4cc5ea94362211b3d2b414e2640c8fcccfd5b2f889` |
| `training/ippo_mobile/c02/51001/ippo_mobile__ippo_mobile__51001/manifest.json` | 1673 | `8089adbbb8ce6c5fde56e4f5939646172a7b9e5f56401c806b47e5a56e10cf3c` |
| `training/ippo_mobile/c02/51001/ippo_mobile__ippo_mobile__51001/summary.json` | 2881 | `2a84bba124460250d57b285a9b2d7f1391f1668776b7ceb224182ac1616c28a9` |
| `training/ippo_mobile/c02/51001/ippo_mobile__ippo_mobile__51001/training.jsonl` | 88488895 | `cc388458cc506ee1c55003980ade94da90e8ca6492cdf3c49e6f032b81bb5d57` |
| `training/iql_mobile/c01/51001/iql_mobile__iql_mobile__51001/checkpoint.pt` | 1630959701 | `97cb2755f34aabd55b28fa3edf1bb91815f28de40f180600641605a8a3e52183` |
| `training/iql_mobile/c01/51001/iql_mobile__iql_mobile__51001/manifest.json` | 1670 | `92985fe6ec3b5e778c2cb4f57a0dfb0a5f69f029e1f96c2f1220435e3f33f353` |
| `training/iql_mobile/c01/51001/iql_mobile__iql_mobile__51001/summary.json` | 2562 | `a0e70a8063deaae3547a527f4174bfa98b15cff9eca051f0de4dba8fae96a3bc` |
| `training/iql_mobile/c01/51001/iql_mobile__iql_mobile__51001/training.jsonl` | 88088895 | `00432fbb2071c2d836a1621aff460721d19f3b7a8cf028642d07324e69d81d29` |
| `training/iql_mobile/c01/51002/iql_mobile__iql_mobile__51002/checkpoint.pt` | 1630959637 | `0b4ef17e3fdb331b565a74f8af3abcf17f632149d9bb139f392e6b3e46375637` |
| `training/iql_mobile/c01/51002/iql_mobile__iql_mobile__51002/manifest.json` | 1670 | `2773a6fc3d2273d20f00548cb0bff40557f760755731364e648241db5acfea4c` |
| `training/iql_mobile/c01/51002/iql_mobile__iql_mobile__51002/summary.json` | 2563 | `9e049926814728fa0bae82f0e2d83381526f87a7a4c0546cf04e470559f40e91` |
| `training/iql_mobile/c01/51002/iql_mobile__iql_mobile__51002/training.jsonl` | 88088895 | `00432fbb2071c2d836a1621aff460721d19f3b7a8cf028642d07324e69d81d29` |
| `training/iql_mobile/c01/51003/iql_mobile__iql_mobile__51003/checkpoint.pt` | 1630959701 | `eed1f12065e706a8f9f75abed279d8e317c4be8b3fba132de94939a7bbe3de87` |
| `training/iql_mobile/c01/51003/iql_mobile__iql_mobile__51003/manifest.json` | 1670 | `e6f13dccf49f30750deb5dc066e63143dc02cba12d94de7d615a63d3e13c76d6` |
| `training/iql_mobile/c01/51003/iql_mobile__iql_mobile__51003/summary.json` | 2563 | `54e3731e872ab93e9f1fbf615d00db376adbcf84ea3da016f2f410ad9c5a4501` |
| `training/iql_mobile/c01/51003/iql_mobile__iql_mobile__51003/training.jsonl` | 88088895 | `00432fbb2071c2d836a1621aff460721d19f3b7a8cf028642d07324e69d81d29` |
| `training/iql_mobile/c02/51001/iql_mobile__iql_mobile__51001/checkpoint.pt` | 1630959701 | `fa7ff7ed6b8fe8750b5e17e96bcbf7c35156588954aa70e6592ae517fda13eee` |
| `training/iql_mobile/c02/51001/iql_mobile__iql_mobile__51001/manifest.json` | 1670 | `9f701a55dd6808b73acda38b786babdd3b7078f875643930e60f7bc744d3e9d4` |
| `training/iql_mobile/c02/51001/iql_mobile__iql_mobile__51001/summary.json` | 2562 | `a508a1a83c84ff6dae053df5b9d66376b9bd1216eef2362c86c1317daee06812` |
| `training/iql_mobile/c02/51001/iql_mobile__iql_mobile__51001/training.jsonl` | 88088895 | `3d993cebbfb0e91319a1d9e280860f2ba648925e7aaec20813e2f4dd2904b919` |
| `training/iql_mobile/c02/51002/iql_mobile__iql_mobile__51002/checkpoint.pt` | 1630959637 | `55972cf055d17951b0c47b618db99581c05d8d7a8cdbe00b59a600d165c67251` |
| `training/iql_mobile/c02/51002/iql_mobile__iql_mobile__51002/manifest.json` | 1670 | `d046233eb03b3fac5c7bcabebaa5e67c2267ace6f21668f87b0b1a3566d73344` |
| `training/iql_mobile/c02/51002/iql_mobile__iql_mobile__51002/summary.json` | 2563 | `9cb683830b017dcf6551103c3e34b2dc68f35a6282e3f248627a730bbe1e169a` |
| `training/iql_mobile/c02/51002/iql_mobile__iql_mobile__51002/training.jsonl` | 88088895 | `3d993cebbfb0e91319a1d9e280860f2ba648925e7aaec20813e2f4dd2904b919` |
| `training/iql_mobile/c02/51003/iql_mobile__iql_mobile__51003/.checkpoint.pt.spu__xft.tmp` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `training/maddpg_mobile/c01/51001/maddpg_mobile__maddpg_mobile__51001/checkpoint.pt` | 818977549 | `902739c2743d4d40a3a708fa7c611eaff64ecdf47c361a4550ffbf0d13e867dd` |
| `training/maddpg_mobile/c01/51001/maddpg_mobile__maddpg_mobile__51001/manifest.json` | 1678 | `97688a33c885e1505bf255d9e51ea46aac7b4d84b7a763173e68308b6135d05b` |
| `training/maddpg_mobile/c01/51001/maddpg_mobile__maddpg_mobile__51001/summary.json` | 2692 | `d07a50f7d8a5ad628e8d669de623fb9f7e129a50c19229436bc6687acd4fc8dc` |
| `training/maddpg_mobile/c01/51001/maddpg_mobile__maddpg_mobile__51001/training.jsonl` | 89288895 | `cf49f2b7708b706b49ae8e076a134ea126383784174aa316014bc3a409be3994` |
| `training/maddpg_mobile/c01/51002/maddpg_mobile__maddpg_mobile__51002/checkpoint.pt` | 818977485 | `24cd7dd651e7d8ad2deefc9f688fccfe8d8e197f60a1607e1df13ef1368f7d85` |
| `training/maddpg_mobile/c01/51002/maddpg_mobile__maddpg_mobile__51002/manifest.json` | 1678 | `3e56606597494821b22cecf68a7f2dc1ccc8d24f0a4546ab13e528849edcfff2` |
| `training/maddpg_mobile/c01/51002/maddpg_mobile__maddpg_mobile__51002/summary.json` | 2693 | `4bce1d0348ad321835be146c02878c3af446a5b8b3de0171770bf71f4ce80ab3` |
| `training/maddpg_mobile/c01/51002/maddpg_mobile__maddpg_mobile__51002/training.jsonl` | 89288895 | `cf49f2b7708b706b49ae8e076a134ea126383784174aa316014bc3a409be3994` |
| `training/maddpg_mobile/c01/51003/maddpg_mobile__maddpg_mobile__51003/checkpoint.pt` | 818977549 | `4cc8f1e01a5b4e3b68c197f39d5cf54afaf9c0b9b0a90d30f94c566eb5757767` |
| `training/maddpg_mobile/c01/51003/maddpg_mobile__maddpg_mobile__51003/manifest.json` | 1678 | `cd24d5aef779be55d166cc02dd89b8de0e6d5877496d99c1e5bb9641f9707e40` |
| `training/maddpg_mobile/c01/51003/maddpg_mobile__maddpg_mobile__51003/summary.json` | 2694 | `68a3601f4aef890f1650706612eef74a3a5b64bacc2623bd554c1c086eaee1f9` |
| `training/maddpg_mobile/c01/51003/maddpg_mobile__maddpg_mobile__51003/training.jsonl` | 89288895 | `cf49f2b7708b706b49ae8e076a134ea126383784174aa316014bc3a409be3994` |
| `training/maddpg_mobile/c02/51001/maddpg_mobile__maddpg_mobile__51001/checkpoint.pt` | 818977549 | `7c288fc3d4b10b3ed30711349521da724a25332b9af541a25d2c70bc9691ad94` |
| `training/maddpg_mobile/c02/51001/maddpg_mobile__maddpg_mobile__51001/manifest.json` | 1678 | `6d7c3864ec6f01ccb43020ad6179e3d2918ef9bd443b065a86142e26cbaa4d9e` |
| `training/maddpg_mobile/c02/51001/maddpg_mobile__maddpg_mobile__51001/summary.json` | 2692 | `5bdf44dfa004df11032511999629e8f962b146b097380271fb3435bb3b4a88e5` |
| `training/maddpg_mobile/c02/51001/maddpg_mobile__maddpg_mobile__51001/training.jsonl` | 89288895 | `e4983b4181845f1b783de55d6702c84091a86a42e62edc5f2bcaa56644b58cae` |
| `training/maddpg_mobile/c02/51002/maddpg_mobile__maddpg_mobile__51002/checkpoint.pt` | 818977485 | `06e5a44cd4967be025686216bc3974d4d9f51678f58058af7bee48c9d9354c63` |
| `training/maddpg_mobile/c02/51002/maddpg_mobile__maddpg_mobile__51002/manifest.json` | 1678 | `2a3fbe35fdbac0ad9dd240167d1be6c665a37aedbfd9e3f4b615a83f1f7de7aa` |
| `training/maddpg_mobile/c02/51002/maddpg_mobile__maddpg_mobile__51002/summary.json` | 2693 | `decf4bf1c6fedd0d6fad5a2dde9b1eee83cde902d7d877677b674efe3edd7739` |
| `training/maddpg_mobile/c02/51002/maddpg_mobile__maddpg_mobile__51002/training.jsonl` | 89288895 | `e4983b4181845f1b783de55d6702c84091a86a42e62edc5f2bcaa56644b58cae` |
| `training/maddpg_mobile/c02/51003/maddpg_mobile__maddpg_mobile__51003/checkpoint.pt` | 818977549 | `11663e554e913841285118b5f152c4f6306a23128be59fa9425df3f67bc9e905` |
| `training/maddpg_mobile/c02/51003/maddpg_mobile__maddpg_mobile__51003/manifest.json` | 1678 | `2398726940e718b2124abbcdc2924671b8321eef74a58242383e370fdd3132d6` |
| `training/maddpg_mobile/c02/51003/maddpg_mobile__maddpg_mobile__51003/summary.json` | 2694 | `dd3cf3f1fafbc14a5927c8766c6cbd36d2a6ddc7c1efa3ad97449cd126ae33d2` |
| `training/maddpg_mobile/c02/51003/maddpg_mobile__maddpg_mobile__51003/training.jsonl` | 89288895 | `e4983b4181845f1b783de55d6702c84091a86a42e62edc5f2bcaa56644b58cae` |
| `training/maddpg_mobile/c03/51001/maddpg_mobile__maddpg_mobile__51001/checkpoint.pt` | 818977549 | `6fb8ac897f29e051fcbb663b759315a7d732a8a59e90de237f472360de05ddd5` |
| `training/maddpg_mobile/c03/51001/maddpg_mobile__maddpg_mobile__51001/training.jsonl` | 4584478 | `d157a43be9d6d767bc719ba08c8fdf5879f6b24523f4b8bf5e9ffab7bb9c0926` |
| `training/mappo_mobile/c01/51001/mappo_mobile__mappo_mobile__51001/checkpoint.pt` | 1961542823 | `720db5a7c4278d7e1503dd8abce1ae4eb6c375b03c3fd0e36dda5e364fa47fc8` |

## Required Quarantine Action

The original directory is to be moved as one unit to
`outputs/problem2_sr_mappo_v1/g5/quarantine/task12-first-attempt/`. After the
move, the large `.pt` and `.jsonl` files and the zero-byte temporary file may
be deleted from the quarantine copy to release disk space. The JSON
manifest/summary files and the ten training-log files are retained as failure
metadata. This audit remains the authoritative record of the deleted bytes;
the quarantine path must never be used by a training or validation loader.

The repository-local `_tmp_docx_assets/` directory and every `tmp-*` directory
are outside this action and must remain untouched.

## Completed Quarantine

The directory was moved to
`outputs/problem2_sr_mappo_v1/g5/quarantine/task12-first-attempt/` after this
inventory was written. The original `g5/validation/` path no longer exists.
Exactly 34 large files (`17 .pt`, `16 .jsonl`, and `1 .tmp`) totalling
23,745,414,990 bytes were deleted from the quarantine copy. Exactly 40 failure
metadata files (`30 .json` and `10 .log`) totalling 67,276 bytes remain. No
repository-local temporary directory or protected external asset was changed.
