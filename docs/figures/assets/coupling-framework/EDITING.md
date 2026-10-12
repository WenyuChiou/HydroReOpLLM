# Coupled hydrology and reservoir operations figure

The English diagram is a generic framework view. It contains no case studies.
The master is `../../hydrocnhs-coupling-framework-en.drawio`.
PNG, SVG and PDF exports use the same filename stem.

Open the master in draw.io Desktop to change native labels, module cards and
attached connectors. Icons are separate, movable PNG objects. Their pixels
are raster artwork; they are not vector drawings. Use the separate PNG assets
to replace an icon. `generation.json` preserves exact prompts and asset hashes.

The lower blue frame follows the HydroCNHS workflow: rainfall–runoff (GWLF/ABCD),
upstream routing (Lohmann), reservoir operation via the Dam API, downstream
routing (Lohmann), and river flow. One reservoir card contains the exclusive
choice **Rule-based OR LLM**. The Dam API supports user-defined policies; the
original HydroCNHS does not supply our rule policy or reservoir physics solver.
The shared deterministic solver is an addition used by both policies in the
daily operations runner. Its storage, spill and water-balance details belong
in the tutorial, rather than this concept image.

The independent upper frame follows Prompt → language model → response reader
→ release decision → Checker. The Prompt card has an information icon; routed
inflow and state/release history are named on its incoming connectors. Optional
knowledge is a small secondary input, with no named example in the image.
The concept does not prescribe prompt frequency; the shipped operations driver
is daily. Reader and Checker are conceptual roles, not separate services.
A malformed response may fail in the reader; all invalid actions stop before
the physical transition. Checker **PASS** returns a checked proposal to the
selected LLM controller. **FAIL** stops; no rule-policy fallback is implied.
PASS is contract validation, not strategy-audit approval. Audit/trace records
both the proposal and execution. Actual execution supplies later history.
Solid blue arrows carry water; plum arrows carry decision data, with a dashed
return to the Dam API. Dashed green arrows carry state/history, and dotted gray
arrows carry context or records. Essential connections are labeled locally.

River topology belongs to model configuration; the diagram does not prescribe
reservoir locations or a fixed count. Repeat decision units where the network
requires them. Passive outlets do not require LLM decisions. The six original
generated assets are unchanged; major icons occupy 200 × 200 native drawing
units (Checker: 190 × 190). The book icon now represents the assembled Prompt.

Rebuild native objects with Python:

```bash
python docs/figures/source/build_coupling_drawio.py
```

Export with draw.io Desktop CLI:

```bash
draw.io --export --format png --border 30 --scale 1.5 --output docs/figures/hydrocnhs-coupling-framework-en.png docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format svg --border 30 --embed-svg-images --embed-svg-fonts false --output docs/figures/hydrocnhs-coupling-framework-en.svg docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format pdf --border 30 --crop --output docs/figures/hydrocnhs-coupling-framework-en.pdf docs/figures/hydrocnhs-coupling-framework-en.drawio
```

Use the installed executable path if `draw.io` is not on PATH. Rendering was
checked with draw.io Desktop 26.0.4. The revision diagnostic changes a native label,
moves a module and its icon, and reconnects a record edge. It is saved,
reopened through draw.io XML export, then rendered. GUI dragging and arbitrary
layout changes were not tested. Keep the master unchanged when trying edits;
the rebuild script recreates the saved layout and overwrites manual changes.

Visual review covers the full PNG and a 900-pixel preview. Audience comprehension
and the user's design acceptance remain pending. Earlier source/exports and QA
are preserved in Git history and the task-local revision snapshot. Current QA
is in `quality.json`; its history is not evidence that the new geometry passed.
