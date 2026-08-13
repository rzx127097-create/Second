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
| CH4-FIG-02 | figure | 4.1.2-4.1.3 | `docs/design/section-4.1-design-contract.md`; no experiment data | `python scripts/figures/generate_section_4_1_figures.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile`; shared service interface for rolling A* | not applicable | conceptual request/service sequence | request trigger, inventory/feasibility check, parallel travel, conditional waiting, co-arrival, service lock, stepwise transfer, inventory update | descriptive only | `artifacts/figures/chapter4/fig4-2_service_process.{svg,pdf,png,tiff}` | Replenishment follows an auditable discrete-event sequence with deterministic road execution, conditional waiting, service locking, partial refill, and explicit exception branches. | thesis-ready | State-machine implementation and deterministic tests remain for M2. |
| CH4-TEXT-01 | text-claim | 4.1.1-4.1.5 | `docs/design/section-4.1-design-contract.md` | authored in `docs/thesis/section-4.1.md`; built by `python scripts/documents/build_section_4_1_docx.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile`; comparison interfaces named but not evaluated | not applicable | model specification only | eight numbered equations; time, space, inventory, and objective relations | descriptive only | `docs/thesis/section-4.1.md` | Section 4.1 defines the entities, dynamic replenishment demand, rendezvous/service mechanism, coupling relations, and research objectives without presupposing algorithm superiority. | thesis-ready | Engineering values must be calibrated and frozen in the experiment settings. |
| CH4-DOC-01 | docx | 4.1 | `docs/thesis/section-4.1.md`; CH4-FIG-01; CH4-FIG-02 | `python scripts/documents/build_section_4_1_docx.py` | `section-4.1-M1` | delivery commit in repository history | `sr_mappo_mobile` (design only) | not applicable | model specification only | 90 editable Office Math objects, eight display equations, two figures | descriptive only | `artifacts/documents/4.1问题描述与空地协同保障机制设计.docx` | Standalone thesis-formatted delivery of Section 4.1. | thesis-ready | Equations are editable OMML and MathType-compatible, not MathType OLE objects. |

## Integrity records

| File | SHA-256 |
|---|---|
| `scripts/figures/generate_section_4_1_figures.py` | `697E9D35133306A51A8C79EFEC69880E8488D559DAB914982789E7BC6BBE9BD4` |
| `scripts/documents/build_section_4_1_docx.py` | `2C8FECAE3C25DE7F3A5F805F98596E8E3ABBF52FA8F896D58D22E94A6D1969D7` |
| `docs/thesis/section-4.1.md` | `38F7EA3617719FA83BE96BE4185C74F649C24AAD91414D2997C78481AA2C0EF9` |
| `artifacts/figures/chapter4/fig4-1_air_ground_system.pdf` | `5410CD36F68655122BFB9248A342114BF9E3F705365A5FEF232C06F3460F1F25` |
| `artifacts/figures/chapter4/fig4-2_service_process.pdf` | `039022B18C63F3BCD36D4B3EB93CE8AB166D6663FDCCCB2A5130B7A242DD0343` |
| `artifacts/documents/4.1问题描述与空地协同保障机制设计.docx` | `ECB3B6A0FF1345D49C0B6978E150998F34430136A453DC889EE0B6E2F15D36F1` |

The user-facing DOCX copy has the same SHA-256 as the repository copy.

## Verification record

- Python source preflight: 18 PASS, 2 reviewed warnings, 0 FAIL. The 154.9 mm width matches the thesis text block rather than a journal column; the math-script warning is resolved by the rendered PDF text audit.
- PDF text audit: Figure 4-1 and Figure 4-2 both have a minimum text size of 5.04 pt and pass the 5 pt floor.
- Raster exports: PNG and TIFF are 600 dpi.
- DOCX structure: 90 `m:oMath` objects, 8 `m:oMathPara` display equations, 2 inline embedded images, 1 `Heading1`, and 5 `Heading2` paragraphs. Numbering uses `(4.1)`-style tags throughout.
- Figure PNGs were visually inspected at original resolution. Microsoft Word exported the final DOCX to an 8-page A4 PDF; all eight rendered pages were inspected at full resolution. Equations (4.1)-(4.8), including the multiline constraints in Equation (4.6), are complete, and neither figure overflows the text block. DOCX ZIP/OOXML integrity, 90 editable math objects, eight display equations, captions, inline image anchoring and the byte-identical delivery copy were also verified structurally.
