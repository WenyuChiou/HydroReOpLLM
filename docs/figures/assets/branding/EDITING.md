# HydroOpsLM visual candidate

This illustrative cover is a visual candidate for review; the user has not
approved it as final branding. Gate openings and release widths are illustrative,
not measurements or simulation results. The cover retains **Built on HydroCNHS**.
The existing project mark is retained, without introducing a new logo design.

## Cover and logo

- [Editable cover SVG](../../hydroopslm-cover.svg): 1800 × 600, native text and vectors.
- [README PNG](../../hydroopslm-cover.png): 1800 × 600; existing README references work.
- [Large cover PNG](hydroopslm-cover-3600.png): 3600 × 1200.
- [Logo SVG](hydroopslm-logo.svg) and [transparent 1024px PNG](hydroopslm-logo.png).
- Transparent logo previews: [64px](logo-64.png), [32px](logo-32.png).

## Editable groups and reusable components

Cover text groups are `project-title`, `project-subtitle`, `source-credit`.
Fonts are **Georgia** and **Segoe UI**. Shapes, text and shadows remain separate.
Terrain is `terrain-illustration` / `elevation-contours`; shoreline objects are
`shore-life`; reservoirs and ripples are `reservoir-*` / `water-surface-*`.
Dams, gates, releases and robots are `dam-*`, `gate-*`, `release-*`, `robot-*`.
Shadows are `scene-shadows` / `robot-ground-shadows`.

[Component preview](components-preview.png) shows independent transparent SVGs:

- Dams: [upstream](components/dam-upstream.svg), [downstream](components/dam-downstream.svg).
- [LLM robot](components/llm-robot.svg).
- Reservoirs: [upstream](components/reservoir-upstream.svg), [downstream](components/reservoir-downstream.svg).
- [Water-surface strokes](components/water-surface.svg), [river segment](components/river.svg).

These are compound native groups, not flattened single paths or embedded bitmaps.
Their individual paths, circles and ellipses remain primitives. Each component
has a self-contained viewBox, required defs and an identifier prefix. Geometry
and colors are extracted from the cover; only viewport placement and IDs change.
The water-surface preview uses a blue card that is absent from its transparent SVG.
Moving objects does not automatically reposition other scene objects. Cross-editor
import/drag behavior has not been tested.

## Provenance

Artwork is authored as native SVG geometry and text, rendered with CairoSVG.
Pillow assembles previews only. No image-generation service was used. The SVGs
contain no raster image embeds, scripts or external resource references.
[provenance.json](provenance.json) records SHA-256 hashes and the visual-candidate scope.
