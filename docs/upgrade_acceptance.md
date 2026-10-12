# HydroCNHS upgrade acceptance — 2026-10-12

This acceptance covers T1–T6 software and an initial English Technical Note.
It does not accept an operating policy or authorize a real LLM experiment.

| Task | Delivered evidence |
|---|---|
| T1 inventory | [Original/current/Demo comparison](PROJECT_INVENTORY.md); 691 protected existing files unchanged |
| T2 benchmark | Shared Dam API backend, 162 exact reference comparisons, both capacity-ratio branches, environmental floor and operating-year tests |
| T3 prompts/configuration | Original FE system text, daily builders, schema, conditional DKP retrieval and native audit retained; validated reservoir profiles and compact variables |
| T4 multiple reservoirs | 31-day two-controller/passive network; regression coverage for cascades, confluence, delay and channel balance; independent state and fail-before-physics behavior |
| T5 figures/tutorial | English/Chinese concept SVG/PDF/PNG, formal GIS map and editable Python masters; eight executed notebooks, 23 cells |
| T6 documents | Concise EN/zh-TW README and settings/tutorial guides; [English draft](../paper/technical_note.md) and [draft scope](../paper/DRAFT_STATUS.md) |

## Numerical and reproduction evidence

[The results package](../results/technical_note_offline/README.md) contains the
complete four-run bundle, per-file hashes, independent verification and captured
commands. Each FE method passed three daily transitions; the network passed 31
days / 93 reservoir-days. Maximum system residual was 3.725290298461914e-9 m³;
routing reconstruction differed by 0 m³/s; model calls were 0. Prompton's 31
UNKNOWN audit records and unset policy acceptance were retained.

The final full suite passed 472 tests and 395 subtests. The affected
suite passed 114 tests and 60 subtests. A new venv and fresh source snapshot passed
the tutorial with an offline editable installation and reused local dependencies.
This verifies those installed dependency versions; it does not establish a newly
downloaded environment, Jupyter-kernel execution or every inherited module's
empirical validity. Native HydroCNHS files/license/source pins are unchanged.

Review corrections bind reference profiles to physical reservoir IDs, reject
cached tutorial outputs when current settings/input/runtime pins differ, and
support the documented `verify --require-offline` CLI. Earlier acceptance files
remain preserved; the final evidence package identifies the corrected execution.

## Documentation and figures

The multi-locale mirror contract checks EN/zh-TW structure, technical terms,
relative links and script conventions. Parent semantic review checks the opposing
claims directly: both READMEs say the LLM changes storage/downstream flow and does
not change calibrated runoff equations; both guides require per-reservoir rules;
both tutorial pages distinguish a tributary contribution test from full Delaware
flow and calibrated travel time. Structural counts alone are not translation proof.

Figure labels and arrows distinguish native runoff/routing from added physics and
decision systems. The GIS map retains seven source geometries, 299 river features,
two gauges and the project dam location; the inlet is explicitly derived. Python
is the editable master; SVG paths do not automatically follow moved nodes. Actual
rendering and a temporary label/node/edge edit are checked separately. Reader
comprehension has not been measured in a user study.

## Conditions preserved

Initial storage remains a reference assumption; physical and prompt capacities
differ; identity routing does not validate travel timing. DKP date applicability,
environmental exceptions, other reservoirs' sourced settings, provider/model,
budget and replication require resolution before a real experiment. See
[live readiness](LIVE_READINESS.md). Earlier diagnostic policy FAIL/WARN and
unknown request costs retain their status. The draft still needs author metadata,
current journal-format confirmation and a release/archive decision before submission.
