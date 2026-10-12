# Coupled hydrology and reservoir operations figure

The English diagram is a generic framework view. It contains no case studies.
The master is `../../hydrocnhs-coupling-framework-en.drawio`.
PNG, SVG and PDF exports use the same filename stem.

Open the master in draw.io Desktop to change native labels, module cards and
attached connectors. Icons are separate, movable PNG objects. Their pixels
are raster artwork; they are not vector drawings. Use the separate PNG assets
to replace an icon. `generation.json` preserves exact prompts and asset hashes.

The lower blue frame identifies the native HydroCNHS host: GWLF/ABCD rainfall–runoff,
Lohmann routing and the Dam API. Rule-based and LLM are alternative user-configured
policies at that API. The yellow reservoir box is the shared **added** physical
solver, not an original built-in HydroCNHS reservoir model. Both policies pass
through it in the daily operations runner.

The upper frame contains the LLM modules: daily prompt, optional knowledge
(DKP is one example), decision, format/value checker and audit/trace. Invalid
actions stop before the physical transition. The LLM branch returns a checked
release; actual storage and executed history feed the next day's observation.
Solid blue arrows are water, dashed plum arrows are decisions, dashed green
arrows are state feedback and dotted gray arrows are data/records.

River topology belongs to model configuration; the diagram does not prescribe
reservoir locations or a fixed count. Repeat decision units where the network
requires them. Passive outlets do not require LLM decisions. The six original
generated assets are unchanged; icons now occupy 180 × 180 native drawing units.

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
moved a module and its icon, and reconnected a record edge. It was saved,
reopened through draw.io XML export, then rendered. GUI dragging and arbitrary
layout changes were not tested. Keep the master unchanged when trying edits;
the rebuild script recreates the saved layout and overwrites manual changes.

Visual review covers the full PNG and a 900-pixel preview. Audience comprehension
and the user's design acceptance remain pending. Earlier source/exports and QA
are preserved in Git history and the task-local revision snapshot. Current QA
is in `quality.json`; its history is not evidence that the new geometry passed.
