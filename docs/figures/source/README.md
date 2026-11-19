# Figure sources

The main README uses the HydroReOpLLM [cover](../hydroopslm-cover.png). Its
editable source is not kept in this repository. The manual uses the maintained
[simulation stages](../simulation-stages.svg) software diagram.

`render_fe_catchment.py` can export a user-supplied ArcGIS Pro package. This
optional authoring step requires ArcGIS Pro and is not needed to install or run
the module. Generated maps stay under `outputs/` and are not published by the
documentation build.

`extract_fe_map.py` preserves the geographic input extraction used by the
downstream example. Its frozen geometry remains an active example dependency;
see [sources and extraction instructions](../../../data/figures/SOURCES.md).

Superseded concept/study-map exports and their old generators are available in
Git history at `f6eff89`. They are not alternate current editing entrypoints.
