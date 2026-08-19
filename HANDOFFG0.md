# HANDOFF G0

> This document is the handoff for a new conversation with no prior context.
> It records the project state at the end of G0. Do not start new thesis
> writing or large-scale experiments from this document alone.

## 1. What We Are Doing

The project is building a reproducible, auditable, thesis-level package for
the second research problem:

> Road-constrained air-ground heterogeneous cooperative pesticide spraying
> with multiple UAVs and a mobile pesticide-supply vehicle, using SR-MAPPO as
> the flagship algorithmic framework.

The intended end-to-end package includes:

- problem and physical modeling;
- engineering parameter registration and source tracking;
- offline GIS road modeling;
- finite pesticide, request, queue, rendezvous, and service-state logic;
- heterogeneous SR-MAPPO implementation;
- fair learned and traditional baselines;
- sensitivity, multi-scale, ablation, mechanism, and counterfactual experiments;
- immutable job orchestration and recovery;
- sealed-test evaluation;
- paired statistics and negative-result diagnosis;
- figures, tables, artifact manifests, and a thesis chapter generated from
  locked summaries.

Simulation results must never be described as real deployment evidence.

## 2. User Request Versus Attached Template

The attached image was treated as a handoff template: stop new thesis edits and
leave a complete project-state record for the next Master Agent. The direct user
request controls the deliverable path: create `HANDOFFG0.md` in the `Second`
repository. The image does not authorize new thesis-content changes or override
the current project constraints.

## 3. Repository And Branch

Authoritative repository:

`C:/Users/RZX/Documents/ChatGPT/Second`

GitHub remote:

`https://github.com/rzx127097-create/Second.git`

Current branch:

`codex/problem2-g0-orchestration`

Remote branch:

`origin/codex/problem2-g0-orchestration`

G0 commits:

1. `7731d37` - `chore: register problem2 orchestration state`
2. `9fdd560` - `docs: record g0 verification and push`

At the time of handoff, the branch is intended to be clean and synchronized
with its remote. Verify this before starting G1.

## 4. Current Maturity And Gate

- Highest maturity: `M1`, design/specification evidence.
- G0: passed.
- Next gate: `G1`, evidence registration and existing-code audit.
- Sealed test: locked; it must not be used for tuning.
- Formal results: none are authorized from the current G0 state.
- Allowed wording: designed, defined, proposed, specified, planned for
  verification.
- Forbidden wording: proved, significantly outperformed, formal experiments
  show, universally optimal, real deployment verified.

Do not claim that mobile replenishment works or that SR-MAPPO is always best
until formal paired experiments have passed the required gates.

## 5. What Has Been Completed

### Orchestration And Exploration

Four read-only subagents were used during initial orchestration:

- Repo Explorer: audited the first-problem repository and protected dirty files.
- Environment Explorer: audited `D:/Pycharm/Locust_rl`.
- Planning Analyst: read the two second-problem planning documents.
- Experiment Architect: designed the proposed experiment and evidence pipeline.

Key conclusion: the second problem was only M1 before G0. The existing
specification is not evidence that the environment, algorithm, or experiments
are already valid.

### G0 Files

Created or updated:

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `.gitignore`
- `HANDOFFG0.md` (this file)

`AGENTS.md` now requires every important phase to:

1. write outputs into `Second`;
2. run fresh verification;
3. commit;
4. push to GitHub;
5. record the pushed commit hash and verification result in
   `docs/PROJECT_STATE.md`.

### Verification

Fresh G0 verification included:

- `python -m pytest tests\test_section_4_2_artifacts.py -q`
  -> `7 passed`;
- required-field scans for project state and handoff metadata;
- `git diff --check`;
- GitHub remote branch verification with `git ls-remote`;
- `.gitignore` verification for generated `__pycache__` and `.pyc` files;
- final check that the first-problem repository retained its pre-existing dirty
  files and was not modified.

No first-problem Word file, experiment output, or source file was changed.

## 6. Existing Assets In Second

The `origin/main` history already contains M1 chapter 4.1/4.2 design and
document-delivery assets, including:

- `docs/design/section-4.1-design-contract.md`
- `docs/design/section-4.2-design-contract.md`
- `docs/thesis/chapter4-outline.md`
- `docs/thesis/section-4.1.md`
- `docs/thesis/section-4.2.md`
- `docs/artifacts/section-4.1-artifact-ledger.md`
- `docs/artifacts/section-4.2-artifact-ledger.md`
- `scripts/figures/generate_section_4_1_figures.py`
- `scripts/figures/generate_section_4_2_figures.py`
- `scripts/documents/build_section_4_1_docx.py`
- `scripts/documents/build_section_4_2_docx.py`
- existing chapter 4 figures and DOCX files under `artifacts/`

These are design/document assets, not formal second-problem experimental
results. The 4.2 artifact ledger explicitly says the project remains M1 until
road, service, conservation, mask, MARL, and experiment gates are verified.

## 7. Existing Feature Branch That Must Be Audited

Remote branch:

`origin/feature/problem2-code-framework`

Observed commit at G0:

`52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`

It contains substantial candidate assets:

- `src/problem2/` environment, road, domain, demand, algorithms, experiments,
  and artifact modules;
- `configs/`;
- `scripts/`;
- `tests/`;
- road data and verification reports;
- M3 pilot and formal-readiness documents.

Do not merge, cherry-pick, or trust its maturity claims automatically. G1 must
audit source, tests, hashes, and semantics independently from a clean branch.

## 8. Frozen Research Decisions

### Algorithm Identity

- Public flagship name: `SR-MAPPO`.
- Problem 2 description: air-ground heterogeneous extension of SR-MAPPO.
- Do not implement or claim HAPPO.
- Do not rename the method to `AG-SR-MAPPO`.

### Resource Boundary

- Main resource: pesticide only.
- Battery replenishment: inactive until a separate activation audit passes.
- Main experiment: one mobile pesticide-supply vehicle.
- Fixed-support comparison must match inventory, service capability, speed,
  service time, horizon, scenarios, and information conditions.

### Primary Method Family

- `sr_mappo_mobile`
- `sr_mappo_fixed`
- `sr_mappo_astar`
- `mappo_mobile`
- `sr_mappo_two_stage`

Rolling A* is a normal baseline only when it uses the frozen information and
budget conditions. Future-information planners must be labeled oracle
diagnostics, not ordinary baselines.

### Scale And Seed Protocol

| Scale | Max physical decision steps |
|---|---:|
| `g20x20_d2` | 150 |
| `g20x30_d3` | 180 |
| `g20x40_d3` | 220 |
| `g30x30_d3` | 220 |
| `g30x40_d4` | 280 |
| `g30x50_d4` | 350 |

- Training seeds: `42`, `123`, `2024`, `3407`, `7919`.
- Validation scenario seeds: `20000-20049`.
- Sealed-test scenario seeds: `30000-30099`.
- Primary success threshold:
  `reduction_rate >= 0.85`.
- Frozen output root:
  `outputs/problem2_sr_mappo_v1`.

## 9. Protected First-Problem Assets

First-problem repository:

`C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`

Remote:

`https://github.com/rzx127097-create/locust-rl-paper.git`

Inventory HEAD:

`1ca9e5ccc5f77ed775cd2b607dd70d635720accf`

The first-problem working tree contains pre-existing user changes. Do not
reset, checkout, revert, overwrite, or mix them into Problem 2.

Protected dirty files include:

- `scripts/run_sr_mappo_sensitivity.py`
- `source/locust_rl_selected/config/settings.py`
- `source/locust_rl_selected/evaluation/ablation_convergence.py`
- `source/locust_rl_selected/evaluation/ablation_integrity.py`
- `source/locust_rl_selected/main.py`
- `source/locust_rl_selected/rewards/calculator.py`
- `source/locust_rl_selected/tests/test_sr_mappo_sensitivity.py`
- `source/locust_rl_selected/training/trainer.py`
- `KNOWLEDGE.md`
- the four reward-sensitivity scripts under `scripts/`

Protected Word assets include:

- `方向.docx`
- `无人机蝗灾.docx`
- `消融.docx`
- `knowledge/archive/旧第4章-RL算法比较主线/deliverable/第4章-实验结果与分析.docx`

Protected experiment and figure roots include:

- `outputs/sr_mappo_paper_v1`
- `Table`
- `picture`
- `source/locust_rl_selected/logs`

First-problem historical tables, figures, curves, and fixed-station values may
be background/context only. They are not second-problem formal causal evidence.

## 10. External Inputs

Base project:

`D:/Pycharm/Locust_rl`

This directory is not a Git repository. It contains candidate first-problem
code, OSM data, and old outputs. Any future code reuse must receive a controlled
source snapshot, a reproducible tree hash, or an audited copy in `Second`.

Read-only OSM inputs and G0 hashes:

- `data/jodhpur_drive.graphml`
  -> `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`
- `data/jodhpur_buildings.geojson`
  -> `08A81DF6C8FA401014ACD161661072714D9231B2B95173CBE932C86FE57F37DB`
- `data/jodhpur_green.geojson`
  -> `B80F54C7C03EE42B4F8E8A55BFBCFBD4B7A166ED5E3EB97CD443069398CE0647`

The road data supports road-constrained simulation input only. It does not
support claims about real field deployment or actual agricultural efficacy.

## 11. Scientific Argument And Evidence Boundary

The proposed causal chain is:

```text
limited onboard pesticide
-> dynamic replenishment demand
-> fixed support may cause extra rendezvous travel, waiting, and spraying interruption
-> a road-constrained vehicle approaches demand locations
-> rendezvous distance, waiting, and pesticide-disabled time may decrease
-> effective spraying time may increase
-> pest reduction and the 85% success rate may improve
```

Every arrow is a hypothesis until paired evidence supports it. The mechanism
must be tested through direct mediator logs:

- request count and completion;
- waiting and pesticide-disabled time;
- rendezvous and road distance;
- effective spray time;
- transferred pesticide;
- vehicle travel, idle time, and stranded inventory;
- final reduction rate and 85% success.

The formal evidence chain must be:

```text
source parameter/literature
-> frozen config and source commit
-> immutable run ID and raw log
-> validated long table
-> paired statistics
-> figure/table artifact manifest
-> thesis prose
```

## 12. Main Risks And Traps

Never do the following:

1. Do not continue editing thesis prose before the relevant evidence gate.
2. Do not claim SR-MAPPO is best because the design says it should be best.
3. Do not reuse first-problem fixed-station numeric results as second-problem
   causal evidence.
4. Do not weaken rolling A*, fixed support, MAPPO, or other baselines to force
   an SR-MAPPO win.
5. Do not tune on sealed-test scenarios or reopen sealed tests repeatedly.
6. Do not treat training reward as the primary governance outcome.
7. Do not call OSM simulation input real deployment validation.
8. Do not mix mobile and fixed support resource budgets.
9. Do not start formal jobs before deterministic G2, heterogeneous-MARL G3,
   and mechanism-activation G4 checks pass.
10. Do not recompute PPO masks from later states; store the exact behavior mask
    and candidate mapping.
11. Do not allow a vehicle to serve multiple UAVs simultaneously or violate
    resource conservation.
12. Do not terminate only because vehicle inventory or UAV pesticide is empty.
13. Do not introduce HAPPO or `AG-SR-MAPPO`.
14. Do not modify first-problem Word, code, logs, tables, or figures.
15. Do not use broad `git add` if unrelated files appear; inspect status first.

## 13. Current Blockers And Open Issues

### Blocking For G1

- The remote feature code branch has not been independently audited.
- No canonical parameter registry has been established in the current G0
  branch.
- Engineering source evidence, source values, conversions, and ranges remain
  incomplete.
- `D:/Pycharm/Locust_rl` lacks Git history.
- No sealed-test lock manifest exists in the current branch.
- No formal experiment matrix has been accepted as executable evidence in this
  branch.

### Unresolved Scientific Questions

- Does the selected road map and physical scale represent the intended
  agricultural simulation domain consistently?
- Which engineering parameter ranges are supported by manuals, field studies,
  or expert-confirmed records?
- Is the pesticide bottleneck active without making the scenario pathological?
- Does mobility add value beyond resource amount and fixed-support placement?
- Does joint heterogeneous SR-MAPPO add value beyond rolling A* under fair
  information and runtime budgets?

### Literature And Mentor Status

- No verified literature map was completed in G0.
- No new external literature claim was introduced in this handoff.
- No latest mentor instruction was provided in this session beyond the user
  request and the attached handoff template.
- Record future mentor feedback in `docs/PROJECT_STATE.md` before changing frozen
  decisions.

## 14. Next Conversation Plan

The next conversation should begin with G1 and should not start by editing thesis
正文 or launching training.

### G1.1 Audit Existing Feature Branch

- Compare `origin/feature/problem2-code-framework` against `origin/main`.
- Read its configs, source modules, tests, reports, and claims.
- Run only bounded smoke/audit tests first.
- Produce an audit report in `Second`.
- Decide explicitly whether to merge selected assets, copy them into a new
  controlled module, or rebuild them.

### G1.2 Register Evidence

Create and freeze:

- parameter registry with units, ranges, source type, source ID, source value,
  conversion, status, and scope;
- literature/source ledger;
- experiment matrix manifest;
- scenario and seed manifest;
- job identity and config-hash contract;
- raw-log schema and validated-table schema;
- artifact manifest schema;
- sealed-test lock record;
- output-root contract.

### G1.3 Do Not Cross The Gate

Do not implement or run large experiments until G1 is recorded, committed,
pushed, and the next gate is explicitly opened in `docs/PROJECT_STATE.md`.

## 15. Expected First Actions

1. Read `AGENTS.md`, `docs/PROJECT_STATE.md`, and this handoff.
2. Verify branch, remote, HEAD, and clean status.
3. Verify the first-problem repository remains untouched.
4. Audit the remote feature branch read-only.
5. Update `docs/PROJECT_STATE.md` with the G1 audit plan and evidence registry
   paths.
6. Commit and push the G1 planning record before implementation.

## 16. Handoff Completion Criteria

The receiving conversation should be able to answer these questions before
doing any work:

- What is the research problem and flagship algorithm?
- What is M1 versus formal evidence?
- Which files and repositories are protected?
- Which branch and commits contain the current state?
- What must happen in G1?
- Which claims are forbidden now?
- What mistakes would contaminate the evidence chain?

If any answer is unclear, stop and read the project files before proceeding.

