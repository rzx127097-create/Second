# Section 4.1 artifact ledger

## Evidence boundary

- Maturity gate: **M1 (frozen specification and acceptance criteria)**.
- These artifacts document the proposed air-ground replenishment mechanism. They do not contain experimental observations and do not support a performance-superiority claim.
- Canonical method identity: SR-MAPPO with a road-constrained mobile pesticide-supply vehicle. No HAPPO or renamed algorithm is introduced.
- Resource boundary: pesticide replenishment only; battery replenishment is outside the model.
- Repository state at generation: based on parent commit `905fe8e`; the delivery commit is recorded by repository history.

## Artifact records

| artifact_id | artifact_type | chapter_slot | source_data | generating_script | config_id | git_commit | methods | seed_coverage | scenario_coverage | metrics | statistical_basis | output_path | claim_supported | status | blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CH4-FIG-01 | figure | 4.1.1 | `docs/design/section-4.1-design-contract.md`; no experiment data | `python scripts/figures/generate_section_4_1_figures.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile` (design only) | not applicable | conceptual road-constrained scene | entities, physical flow, information flow | descriptive only | `artifacts/figures/chapter4/fig4-1_air_ground_system.{svg,pdf,png,tiff}` | The system comprises multiple UAVs, a road-constrained mobile pesticide-supply vehicle, candidate rendezvous points, and explicit physical/information interactions. | thesis-ready | No formal run data; no efficacy claim permitted. |
| CH4-FIG-02 | figure | 4.1.2-4.1.3 | `docs/design/section-4.1-design-contract.md`; no experiment data | `python scripts/figures/generate_section_4_1_figures.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile`; shared service interface for rolling A* | not applicable | conceptual request/service sequence | request trigger, reservation, queue, co-arrival, service lock, partial refill, inventory update | descriptive only | `artifacts/figures/chapter4/fig4-2_service_process.{svg,pdf,png,tiff}` | Replenishment follows an auditable discrete-event sequence with deterministic road execution, service locking, partial refill, and explicit exception branches. | thesis-ready | State-machine implementation and deterministic tests remain for M2. |
| CH4-TEXT-01 | text-claim | 4.1.1-4.1.5 | `docs/design/section-4.1-design-contract.md` | authored in `docs/thesis/section-4.1.md`; built by `python scripts/documents/build_section_4_1_docx.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile`; comparison interfaces named but not evaluated | not applicable | model specification only | eight numbered equations; time, space, inventory, and objective relations | descriptive only | `docs/thesis/section-4.1.md` | Section 4.1 defines the entities, dynamic replenishment demand, rendezvous/service mechanism, coupling relations, and research objectives without presupposing algorithm superiority. | thesis-ready | Engineering values must be calibrated and frozen in the experiment settings. |
| CH4-DOC-01 | docx | 4.1 | `docs/thesis/section-4.1.md`; CH4-FIG-01; CH4-FIG-02 | `python scripts/documents/build_section_4_1_docx.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile` (design only) | not applicable | model specification only | 65 editable Office Math objects, eight display equations, two figures | descriptive only | `artifacts/documents/4.1问题描述与空地协同保障机制设计.docx` | Standalone thesis-formatted delivery of Section 4.1. | thesis-ready | Equations are editable OMML and MathType-compatible, not MathType OLE objects. |

## Integrity records

| File | SHA-256 |
|---|---|
| `scripts/figures/generate_section_4_1_figures.py` | `D92C4E294FAC14846CC602BE1F58B6DC9F838A20D2D5BB366FF6B7FAD047409C` |
| `scripts/documents/build_section_4_1_docx.py` | `2C8FECAE3C25DE7F3A5F805F98596E8E3ABBF52FA8F896D58D22E94A6D1969D7` |
| `docs/thesis/section-4.1.md` | `44088896C76EAC9372783AAAF7719AB03D5EA15F01F659DD4C0FF167BED27B74` |
| `artifacts/figures/chapter4/fig4-1_air_ground_system.pdf` | `FCDC9E62F864B1880250E553CF82E9753703ADF5B413C0FBC3BEC571CBACC571` |
| `artifacts/figures/chapter4/fig4-2_service_process.pdf` | `80CF0461D48FD43E97EBE12D11ECBAA77510DD84BE63B06EEDE5CC4DD5189186` |
| `artifacts/documents/4.1问题描述与空地协同保障机制设计.docx` | `8ED7AB36634E6E560DF94D59F8343099B196ED8F3E25C550C4CD371834FB83A1` |

The user-facing DOCX copy has the same SHA-256 as the repository copy.

## Verification record

- Python source preflight: 19 PASS, 1 target-width warning, 0 FAIL. The 154.9 mm width matches the thesis text block rather than a journal column.
- PDF text audit: Figure 4-1 and Figure 4-2 both have a minimum text size of 5.0 pt and pass the 5 pt floor.
- Raster exports: PNG and TIFF are 600 dpi.
- DOCX structure: 65 `m:oMath` objects, 8 `m:oMathPara` display equations, 2 unique embedded images, 1 `Heading1`, and 5 `Heading2` paragraphs.
- Word PDF export: 7 pages; all pages visually inspected for clipping, overlap, pagination, and formula completeness.
