# Draft scope and evidence

Active artifact: `technical_note.md`, complete provisional English tool note.
Target: JWRPM Technical Note. Readers are assumed to know hydrology but need the
decision, physical, routing, and evidence responsibilities separated before
implementation detail. The supplied 2022 HydroCNHS manuscript guides structure
and tone only; its authors, affiliations, funding, case claims, and submission
metadata were not copied.

## Current candidate

- Candidate SHA256: `58d6833bff1ce674ac1ca4d36ad33475929cb978a3765b2c9587635a28cfbc33`.
- Candidate size: 23,186 bytes and 383 lines.
- Lifecycle state: complete internal provisional draft after parent editorial
  review; submission-package decisions remain open. It is not labeled final, verified,
  submission-ready, or journal-compliant.
- Reader sequence: research need → native/added responsibility boundary → daily
  method and contracts → researcher use → FE Walter and network demonstrations →
  implications, limitations, conclusion, and availability.
- Embedded Figure 1 source:
  `docs/figures/hydrocnhs-coupling-framework-en.png`, SHA256
  `21a3ea1f51fdf88d55d60cb789439981c6fd25464aa98ae78e283b8b19130fd2`.
- Embedded Figure 2 source: `docs/figures/fe-walter-study-map.png`, SHA256
  `aa4ad48f118c44ab40b024f1d3d4934551d497d411531f87c39cd6b28b46ff77`.

## Writing and evidence contract

| Claim | Evidence | Inference boundary |
|---|---|---|
| Native HydroCNHS capability retained | `third_party/hydrocnhs/SOURCE.json`; pinned source hashes | Availability and identity, not fresh validation of all inherited modules |
| Benchmark compatibility | Frozen 162-vector comparison; Hanasaki and Abeshu citations; pinned Anik daily function | Compatibility with the daily reference function, not official FE policy |
| Real model integration | Six preserved Ollama `gemma3:4b` responses, completion metadata, raw traces, and original audits | Bounded historical diagnostic, not comparative performance or stochastic replication |
| Storage and routing conservation | Current independent verification in `saved-evidence-recheck.json` and committed run files | Software/accounting verification; identity routing does not validate travel time |
| Multi-reservoir isolation | 31-day saved branch network with two controlled reservoirs and passive Prompton | Independent agents and managed contributions, not joint coordination or complete Delaware flow |
| Reproducibility readiness | Saved files, hashes, tutorial inspection route, and Stagge et al. (2025) policy record | Private repository, DOI archive, and independent human reproduction remain open |

The authoritative current evidence record is
`runs/hydroopslm-cleanup-20261012/diagram-redesign-20261013/saved-evidence-recheck.json`,
SHA256 `ff730b569ebffd25829d6c69c0c7e10c576e1b78e210ae1ebb4e55ec32649a6d`.
It records no new model requests during recheck. The note uses the saved
three-day rule result (3 PASS; 2.3283064365386963 × 10⁻¹⁰ m³ maximum system
residual), real zero-shot result (2 PASS, 1 FAIL; 0 m³; three calls), real DKP
result (3 FAIL; 8.731149137020111 × 10⁻¹⁰ m³; three calls), and synthetic
31-day network result (93 UNKNOWN; 1.862645149230957 × 10⁻⁹ m³ maximum system
residual; zero calls). Every strategy-acceptance field remains null.

## Sources and venue basis

- Supplied structural example: `20220802 JWRPM-mR2-Manuscript-clean-submit.docx`,
  SHA256 `1cef77d59ed823de4b2c9e2b791e45e876039baa3d84c184f52d0f91a5bb1a01`.
- Native package citation: Lin, Yang, and Wi (2022), DOI
  `10.1061/(ASCE)WR.1943-5452.0001630`.
- Benchmark publication identity: Hanasaki et al. (2006), DOI
  `10.1016/j.jhydrol.2005.11.011`. Its full article was not used to certify all
  adapter details; formula support also comes from Abeshu et al. (2023), Eq. 4,
  DOI `10.5194/gmd-16-5449-2023`, and the pinned daily reference function.
- Reproducibility-policy source: Stagge et al. (2025), DOI
  `10.1061/JWRMD5.WRENG-6726`, checked in full in the retained source record.
  Its Reproducible Results program is opt-in; the listed public archive and
  independent reproduction items are program conditions, not universal
  submission requirements.
- The latest detailed journal author guide was unavailable. No page, word,
  display, or formatting limit was invented, and no venue-compliance claim is
  made.

## Remaining submission conditions

Confirm authors, affiliations, acknowledgments, and declarations; verify the
current journal format and length rules; complete public repository and archival
DOI decisions; and obtain project-independent human reproduction with a named
reviewer and affiliation. The Markdown source can be rendered in the local
manual, but it is not a formatted Word submission package. Word layout, tracked
changes, and editor-identity checks are outside this artifact. A separate,
authorized experiment is required for policy-performance conclusions or live
operation claims.

## Current editorial checks

- Argument and structure: Introduction objectives map to the native/added boundary,
  method contracts, user workflow, and two diagnostic demonstrations. Each section
  adds the prerequisite for the next; the conclusions retain the diagnostic scope.
- Evidence and scope: the equations match the pinned daily adaptation and Abeshu
  Eq. 4. Table 1 agrees with current saved-file verification. Six historical
  responses, four failed daily audits, identity routing, and all 93 UNKNOWN network
  verdicts are reported without a strategy-performance or live-operation claim.
- Prose: complete parent reading and sentence/paragraph continuity review retained
  visible actors and the proposal/implemented-release distinction. The independent
  language audit of the preceding complete candidate found two repeated-opening
  warnings; both were corrected. Its targeted recheck reported
  0 Critical and 0 Warning for the preceding complete candidate. The current
  revision clarifies the example opening and map caption; those bounded passages
  receive a new semantic and context review. The earlier language result is not
  claimed for the revised exact file and is not scientific certification.
- Delivery: the preceding complete draft was inspected in the local HTML manual. Figures,
  three locally rendered equations, captions, and Table 1 were inspected at
  1,000 px display width, with Arial 18 px body text. Audit words and storage
  numbers remain on one line, images load, and the page has no horizontal overflow.
  The editable equation source is docs/figures/source/render_note_equations.py.
  The revised diagram receives new full-size, 900 px, PDF, and manual checks;
  the bounded prose changes receive a new semantic and context review.
- Current author-guide length/format remains unverified. Author metadata, public
  release/DOI, human reproduction, and a formatted submission package remain open.

## Historical draft record

The preceding initial draft had SHA256
`3b15b8ee3b674208acf18210c54764587e8402ae99323f4b1d611bbab2266c1d`.
Its independent banned-word audit covered an earlier candidate SHA256
`51e6ec72b46a8ed03053ace4bd05de0627bb764ad53b7939ceae29b99ee12174`
and reported 0 Critical and 0 Warning findings across 122 prose sentences. That
historical language result does not apply to the current rewritten candidate and
does not substitute for scientific, editorial, or independent code review.
