# HydroReOpLLM Figure 1

## Current workflow — 19 October 2026

The author approved the v34 layout. Both ends of the horizontal Valid reply? → Trace records connector are attached to their native nodes. Its location and the author’s labels are preserved. Current PNG/SVG/PDF exports match the native source; quality.json records their hashes. Earlier design records remain below and in Git history.

## Earlier design and typography record


The [native draw.io source](../../hydrocnhs-coupling-framework-en.drawio) is canonical.
Text, boundaries, icon placement and connectors are separate editable objects.
Raster illustrations are embedded; the project logo uses the existing SVG mark.

## Meaning and appearance

HydroCNHS supplies rainfall-runoff, routing and the original Dam API.
HydroReOpLLM supplies decision integrations and the shared reservoir calculation.
The pale left area shows coupling context, not original source ownership.
Rule-based and LLM-based agents are alternatives. Both request release;
implemented controlled release plus spill enters routing once.

Prompt construction receives selected information and optional knowledge.
Response validation checks the reply's structure and values.
Operating-rule check assesses configured criteria without automatically changing or vetoing release.
It is required in this illustrated case; generic configurations may select their auditors.
Enabled auditors complete before the physical transition.
This view focuses Trace records on LLM inputs, replies, release requests and check results.
Rule methods may also use the generic check and trace interfaces.
The Valid reply? diamond represents response parsing and structural/numerical validation;
its No branch summarizes configured retry or stop behavior.

Neutral-gray data cards replace the stark white cards. Blue identifies physical
calculation, warm tones decision generation, and sage checks/assessment/recording.
The warmer right scope emphasizes the expanded LLM path. The agent's pale warm
fill groups its three required steps. The canvas is transparent; the package
uses a neutral paper fill. Colors do not encode strategy quality or code origin.
The dashed card border marks Optional knowledge; Operating-rule check has a solid border.
All arrows remain solid and directed: blue water, dark decision information/requests,
sage records. No module, arrow label or route changed in the v15 fill correction.

## Edit and export

Edit the native source. `source/build_coupling_drawio.py` now preserves its exact
bytes and derives the relationship manifest; it does not redraw or export the
figure. Use `--output-dir` to inspect a separate source copy.
See [Figure 1 interpretation](../../FIGURE1.md) for the execution boundary and
each arrow's meaning.

```sh
draw.io --export --format svg --embed-svg-images --output docs/figures/hydrocnhs-coupling-framework-en.svg docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format png --width 4252 --output docs/figures/hydrocnhs-coupling-framework-en.png docs/figures/hydrocnhs-coupling-framework-en.drawio
draw.io --export --format pdf --crop --output docs/figures/hydrocnhs-coupling-framework-en.pdf docs/figures/hydrocnhs-coupling-framework-en.drawio
```

Wait for each export. --crop prevents paper-size pagination from cutting the figure.
The supplied PDF is one page, normalized to 180 mm width; place a fresh native-size
export at the same width in the manuscript. The supplied PNG is 4252 x 2617 at 600 dpi.
This is a proposed full-width layout, not a verified journal requirement.
Inspect actual manuscript placement; single-column reduction is unsuitable.

The manual embeds the current PNG and offers local, original-byte PNG/PDF downloads.
Documentation builds do not execute models. relationship-map.json describes the
current graph; quality.json separates historical review from current checks.
