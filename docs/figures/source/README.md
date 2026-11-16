# Figure sources

The main README uses the HydroReOpLLM [cover](../hydroopslm-cover.png) and generic [coupling framework](../hydrocnhs-coupling-framework-en.png).
Their editable and vector sources are not kept in this repository.

The maintained study map is [fe-walter-catchment.png](../fe-walter-catchment.png).
`render_fe_catchment.py` exports its portable ArcGIS package; this optional authoring
step requires ArcGIS Pro and is not needed to install or run the module.

`extract_fe_map.py` preserves the geographic input extraction used by the
downstream example. Its frozen geometry remains an active example dependency;
see [sources and extraction instructions](../../../data/figures/SOURCES.md).

Superseded concept/study-map exports and their old generators are available in
Git history at `f6eff89`. They are not alternate current editing entrypoints.
