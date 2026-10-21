# F. E. Walter study-area map source

The manual uses the study-area v4 accepted on 2026-10-21. Its
[PNG](../../../docs/figures/fe-walter-catchment.png) and
[SVG](../../../docs/figures/fe-walter-catchment.svg) are exact copies of the
approved ArcGIS exports. File sizes, SHA256 hashes, source attribution and
previous revisions are recorded in [provenance.json](provenance.json).
The [complete source manifest](source_manifest.json) records all 156 supplied
source files; every listed file and its packaged copy were verified at integration.

## Editable source

Extract [fe-walter-arcgis-source.zip](fe-walter-arcgis-source.zip) and open
`native/project/river-legend-study-area.aprx` in ArcGIS Pro 3.2. River symbology
is editable in native layers. Labels, the legend and the color bar are editable
in `native/commondata/pictures/layout-numbered.svg`.

For an ArcPy export, use `native/project` as the working directory. If the
annotation picture needs relinking after relocation, point it to
`../commondata/pictures/layout-numbered.svg`. The source was saved, reopened and
exported in its authoring environment; GUI relocation to another computer has
yet to be checked. Terrain basemaps use Esri services, so a fresh export can
depend on service availability. Published exports retain fixed hashes.

## Map labels and periods

The [label crosswalk](subcatchment_labels.csv) preserves the model IDs for
U1–U7 (upstream) and D1–D9 (downstream). L1–L2 identify cartographic intersections
of the local areas shown between the dam and White Haven in the inset.
These labels describe the map geometry; the current simulation status is
recorded separately in the [operation case](../../../examples/fe_walter/operation/README.md)
and [downstream validation](../../../examples/fe_walter/downstream/validation.md).

Orange-brown and purple-red outlines identify the full study watershed and
the F. E. Walter watershed, respectively. Grey lines with white casings mark
subbasins; bright-blue lines (`#0096E0`) show the thematic river layers.
The Daymet V4 R1 precipitation background covers **1996–2025**. The current
reservoir-operation comparison covers **2021–2025**.

The supplied v4 exports comprise PNG and SVG. The
[previous PDF](../../../docs/figures/fe-walter-catchment.pdf) remains available
as a historical export and is excluded from the current map downloads.
This update preserves all hydrologic inputs and simulation results.
