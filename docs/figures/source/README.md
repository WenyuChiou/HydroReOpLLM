# Editable figure sources

The main README uses the HydroReOpLLM [cover](../hydroopslm-cover.svg) and generic [coupling framework](../hydrocnhs-coupling-framework-en.drawio).
[Branding editing instructions](../assets/branding/EDITING.md) describe the cover's native SVG groups and reusable components.
Edit the coupling framework's native draw.io cards, icons and attached connectors independently;
[editing instructions](../assets/coupling-framework/EDITING.md) explain exports and icon provenance.
`build_coupling_drawio.py` preserves the native master and derives its relationship manifest.
Use the current editing instructions above to export that reviewed layout.

The maintained study map is [fe-walter-catchment.png](../fe-walter-catchment.png).
`render_fe_catchment.py` exports its portable ArcGIS package; this optional authoring
step requires ArcGIS Pro and is not needed to install or run the module.

`extract_fe_map.py` preserves the geographic input extraction used by the
downstream example. Its frozen geometry remains an active example dependency;
see [sources and extraction instructions](../../../data/figures/SOURCES.md).

Superseded concept/study-map exports and their old generators are available in
Git history at `f6eff89`. They are not alternate current editing entrypoints.
