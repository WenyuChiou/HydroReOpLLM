# Editable figure sources

`render_concept.py` generates native text, boxes and arrows as SVG plus PNG/PDF;
`render_study_map.py` plots the frozen EPSG:5070 geometry, labels and markers.
Labels remain SVG text; paths/shapes are separate objects. Python sources are the
authoritative editable master. SVG edges are paths, not automatically attached
connectors: moving a node in an SVG editor requires moving its edges too.

```powershell
python docs/figures/source/render_concept.py --language en --output docs/figures/hydrocnhs-upgrade-en
python docs/figures/source/render_concept.py --language zh-TW --output docs/figures/hydrocnhs-upgrade-zh-TW
python docs/figures/source/render_study_map.py
```

To edit labels, module locations or arrow endpoints, update the Python master and
regenerate. Previous accepted figure files remain unchanged for historical links.
The concept depicts original HydroCNHS runoff/routing and the existing Dam API;
the common reservoir physics and decision adapters are added implementations at
that API. Solid blue = water, dashed brown = decisions, dotted green = state feedback.

The map contains seven model units: two donor, three spatial-transfer diagnostic
and two residual units. All seven supply the frozen FE model; the eighth YAML
subbasin is a dummy aggregation node, not a geographic footprint. Dam/outlet
coordinates are a project record; the inlet is a derived river/lake boundary
crossing, not a surveyed point. See [exact sources](../../../data/figures/SOURCES.md).
