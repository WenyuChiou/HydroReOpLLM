# Coupled hydrology and reservoir operations figure

The English diagram is a generic framework view. It contains no case studies.
The new master is `../../hydrocnhs-coupling-framework-en.drawio`.
PNG, SVG and PDF exports use the same filename stem.

Open the master in draw.io Desktop to change native labels, module cards and
attached connectors. Icons are separate, movable PNG objects. Their pixels
are raster artwork; they are not vector drawings. Use the separate PNG assets
to replace an icon. `generation.json` preserves exact prompts and asset hashes.

The muted blue frame identifies HydroCNHS hydrology and river routing. The
reservoir solver is marked as an addition through the existing Dam interface.
The upper frame shows configurable operation modules. River topology belongs
to model configuration; the diagram does not prescribe reservoir locations or
a fixed number of reservoirs. Repeat operation units where the configured
network requires them. Passive outlets do not require language-model decisions.

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
checked with draw.io Desktop 26.0.4. The diagnostic copy changed a native label,
moved a module and its icon, and reconnected a record edge. It was saved,
reopened through draw.io XML export, then rendered. GUI dragging and arbitrary
layout changes were not tested. Keep the master unchanged when trying edits;
the rebuild script recreates the saved layout and overwrites manual changes.

Visual review covered the full PNG and a 900-pixel preview. Audience
comprehension and the user's design acceptance remain pending. Previous
accepted figure exports were preserved; this is a sibling design candidate.
