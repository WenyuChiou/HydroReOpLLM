# HydroOpsLM editable concept figure

The outer boundary is HydroOpsLM. Native HydroCNHS supplies GWLF/ABCD runoff,
Lohmann routing and the Dam API. The highlighted reservoir operations are added
through that API; the common deterministic reservoir solver is not native HydroCNHS.
Choose rules or a checked LLM release for each controlled reservoir.

The upper route is Prompt → Language model → Rule output → Checker.
Rule output is a requested release value, not executable code. Invalid or incomplete
replies stop before applying release; there is no automatic fallback. Strategy
audit findings are recorded separately from format/value checking.

Blue solid arrows carry water; plum arrows carry proposed release; gray dashed
arrows supply inflow/optional knowledge; green dashed arrows return executed
reservoir information and record evidence. Audit/trace is a record, not a bypass.

## Edit and export

Text, cards and attached connectors are native draw.io objects. The six preserved
icon assets are separately movable raster images; their pixels are not vector objects.
The cover uses a new text-free illustration plus native editable title/subtitle.

```powershell
python docs/figures/source/build_coupling_drawio.py
draw.io --export --format png --scale 1.5 --output docs/figures/hydrocnhs-coupling-framework-en.png docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format svg --embed-svg-images --embed-svg-fonts false --output docs/figures/hydrocnhs-coupling-framework-en.svg docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format pdf --crop --output docs/figures/hydrocnhs-coupling-framework-en.pdf docs/figures/hydrocnhs-coupling-framework-en.drawio
```

Use the installed executable path if needed. The producer overwrites manual
layout edits, so keep a separate copy when editing in draw.io. Cover master:
`docs/figures/hydroopslm-cover.drawio`; illustration provenance is beside its asset.
SVG accessibility title/description do not change diagram geometry.

Current checks cover full and 900-pixel rendering and a native label, icon,
card and connector edit → save → reopen → render probe. GUI dragging and
reader comprehension are separate, unmeasured outcomes. Previous layouts and
quality records remain in Git history and the task-local original snapshot.
