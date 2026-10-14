# Draft scope and evidence

Active artifact: `technical_note.md`, complete provisional English tool note.
Target: JWRPM Technical Note. Readers are assumed to know hydrology but need the
decision, physical, routing, and evidence responsibilities separated before
implementation detail. The supplied 2022 HydroCNHS manuscript guides structure
and tone only; its authors, affiliations, funding, case claims, and submission
metadata were not copied.

## Current candidate

- Candidate SHA256: `b785ecd1f5b1853cf4b8d71e4a1307e500b9e12bb829bf4e1daa6d68ab82f5ee`.
- Candidate size: 29,256 bytes and 476 lines.
- Lifecycle state: complete internal provisional draft after parent editorial
  review; submission-package decisions remain open. It is not labeled final, verified,
  submission-ready, or journal-compliant.
- Reader sequence: research need → native/added responsibility boundary → daily
  method and contracts → researcher use → FE Walter and network demonstrations →
  implications, limitations, conclusion, and availability.
- Embedded Figure 1 source:
  `docs/figures/hydrocnhs-coupling-framework-en.png`, SHA256
  `97695ce9386aab5c9cf63dc4c3a1dcc2aedfcdf2876dbd3ad4955da5b2ed63c9`.
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
| Configurable information | Synthetic availability, forecast, revision, missing/stale, history and multi-reservoir tests; captured source records | Input/coupling verification, not operating-purpose physical validation |
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

- Argument and structure: parent read all 476 lines of the exact candidate. The
  Introduction links operating-purpose information needs to the common physical
  interface. Methods define selection and causality before outcome diagnostics;
  the Results distinguish preserved trajectories from new synthetic interface
  tests. The Abstract and Conclusions make the same bounded contribution.
- Evidence and scope: original numbers, equations, C&V, inflow, and audit verdicts
  are unchanged. The new USACE downstream-control source and Abeshu discussion
  support information needs, not an implemented flood or energy model. CSV and
  native information can be reconstructed; external provider truth is outside
  saved-file verification. No same-step downstream feedback or joint optimization
  is claimed.
- Scholarly writing: the independent audit read all 476 lines of candidate
  8659a367 and found 0 Critical and 2 noun-chain warnings. Parent shortened the
  two example openings. The same reviewer confirmed only those replacements
  changed and checked lines 214–246 in context on current b785ecd1, with
  0 Critical and 0 Warning. This language evidence is not scientific certification.
- Delivery: current Sphinx 8.2.3 build completed with notebook execution off;
  38 HTML pages, 2,091 local references and two notebook downloads passed the
  validator. Actual Chrome screenshots checked the manuscript, embedded figures,
  Table 1, and the manual at desktop and narrow widths. Arial body text is 18 px;
  no missing images or page overflow was observed. The diagram was independently
  inspected at full size and 900 px and rendered from its native PDF; its text,
  icons and connectors were changed on a separate draw.io copy and reopened.
- Retrospective: the requested tool description, configurable information,
  three examples, map, figures, and preserved evidence are covered. Current venue
  length/format remains unverified. Author metadata, public release/DOI, human
  reproduction, and a formatted submission package remain open.

## Historical draft record

The preceding initial draft had SHA256
`3b15b8ee3b674208acf18210c54764587e8402ae99323f4b1d611bbab2266c1d`.
Its independent banned-word audit covered an earlier candidate SHA256
`51e6ec72b46a8ed03053ace4bd05de0627bb764ad53b7939ceae29b99ee12174`
and reported 0 Critical and 0 Warning findings across 122 prose sentences. That
historical language result does not apply to the current rewritten candidate and
does not substitute for scientific, editorial, or independent code review.
