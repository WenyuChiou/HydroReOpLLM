# HydroOpsLM editable coupling figure

The outer boundary is HydroOpsLM. Native HydroCNHS supplies GWLF/ABCD
rainfall-runoff, Lohmann routing, and the Dam API callback host. The native Dam
API is not a reservoir physical solver. The separate **Added reservoir
operations** block owns deterministic state update and implemented release plus
spill, then returns total outflow to the Dam host once.

Each controlled reservoir selects one policy: **User rule policy OR the checked
LLM policy**. The LLM route is Prompt → Language model → Rule output (requested
release data) → Checker. A valid proposal connects directly to the shared
operations block. An invalid or incomplete proposal stops before physical state
changes; the figure omits a separate stop box so it cannot look like another
workflow stage or automatic fallback.

Prompt receives reservoir inflow, current storage or pool, and implemented
release history. Optional knowledge is a small secondary input. Audit/trace
records prompt, reply, proposal, check, and physical execution; it never gates
the controller or accepts reservoir physics.

Blue denotes hydrology and physical operations, purple denotes policy decisions,
teal denotes checking and records, and gray denotes optional or callback
information. Color does not mean pass or fail.

## Edit and export

Text, cards, native vector symbols, and attached connectors are editable draw.io
objects. The six preserved PNG icon files remain unchanged and are placed as
eight independently movable raster objects; their internal pixels are not vector
objects. Rebuilding overwrites manual layout edits, so retain a separate copy for
GUI experiments.

```powershell
python docs/figures/source/build_coupling_drawio.py
draw.io --export --format png --scale 1.5 --output docs/figures/hydrocnhs-coupling-framework-en.png docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format svg --embed-svg-images --embed-svg-fonts false --output docs/figures/hydrocnhs-coupling-framework-en.svg docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format pdf --crop --output docs/figures/hydrocnhs-coupling-framework-en.pdf docs/figures/hydrocnhs-coupling-framework-en.drawio
```

The current SVG contains native text, no `foreignObject`, and no external
resources. The PDF is one page. Full-size and 900-pixel PNG renders were
inspected; audience comprehension, scientific peer review, and user aesthetic
approval remain separate outcomes.
