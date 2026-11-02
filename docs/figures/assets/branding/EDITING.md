# HydroReOpLLM editable cover

## Current display-name revision — 18 October 2026

The author selected HydroReOpLLM. Current editable sources and exports use this brand; Compatibility filenames remain stable; maintained repository links now use HydroReOpLLM. Earlier records below are retained as history. See the accompanying provenance's branding_revision for current hashes and renderer details.

## Earlier design and typography record


The existing illustrative cover was selected and merged in PR #26. This revision
updates its displayed name to HydroOpsLLM and enlarges all four text nodes;
the revised cover typography was approved by the user on 2026-10-16.
Repository integration remains subject to PR review and separate merge approval. Gate openings and release widths are illustrative,
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

Artwork is authored as native SVG geometry and text. The original exports used
CairoSVG; this typography revision uses Inkscape 1.4.
Pillow assembles previews only. No image-generation service was used. The SVGs
contain no raster image embeds, scripts or external resource references.
[provenance.json](provenance.json) records SHA-256 hashes and the revision scope.


## Typography revision

Title: 100 px (previously 86); subtitles: 40 px (previously 32);
credit: 32 px (previously 24). Positions and line spacing avoid overlap.
All terrain, reservoir, robot, logo and other non-text geometry is unchanged.
SVG text remains editable. The renderer used Noto Serif/OpenAI Sans fallbacks
because Georgia/Segoe UI were unavailable; original font-family declarations
remain in the SVG. Rendering can vary on machines with different fonts.

Use the cover SVG as the editable master. The superseded bitmap-based draw.io
cover is available in Git history at `f6eff89`; it is not a current source.
Repository, package and API names are unchanged.
