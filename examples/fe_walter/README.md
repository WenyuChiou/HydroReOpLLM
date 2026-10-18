# F.E. Walter Reservoir research example

[English](README.md) | [繁體中文](README.zh-TW.md)

This case connects accepted HydroCNHS hydrology to one controlled reservoir and
compares three decision methods: **Rule-based**, **LLM with available
information**, and **LLM with retrieved knowledge**. Start with the
[maintained tutorial](../../tutorials/fe_walter.md).

## Site and study scope

F.E. Walter Dam is near White Haven, Pennsylvania, at the confluence of the
Lehigh River and Bear Creek in Carbon and Luzerne counties. The dam was
constructed in 1961. Its authorized purposes are **Flood Risk Management** and
**Recreation**. Releases also support downstream whitewater boating and fishing
when stored water and flood-management priorities allow. See the U.S. Army
Corps of Engineers [project page](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/),
[re-evaluation study](https://www.nap.usace.army.mil/Missions/Factsheets/Fact-Sheet-Article-View/Article/490871/francis-e-walter-dam-re-evaluation-study/),
and [flow-management plan and schedule](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/Flow-Management-Plan-Schedule/).

```{figure-md} fe-walter-study-area
:class: study-area-figure

![F.E. Walter modeled catchment, rivers, dam, and gauge](../../docs/figures/fe-walter-catchment.png)

**Figure 1.** Modeled subcatchments, dam, gauge, and 1996–2025 mean annual
precipitation. The callout locates the reservoir area; the diamond marks the
dam/outlet. Water surfaces and rivers share the same blue.[^map-sources]
```

[^map-sources]: Esri, CGIAR, USGS, data.pa.gov, TomTom, Garmin, SafeGraph,
    METI/NASA, EPA, NPS, USDA, USFWS, New Jersey Office of GIS, FAO, and NOAA.

## Accepted hydrological boundary

The seven modeled contributing units total 750.811 km², excluding the native
model's 1 ha artificial aggregation outlet. This is watershed area, not official
reservoir surface or project property area. HydroCNHS uses daily
weather and catchment properties to generate routed inflow at the dam. The
operation experiment selects 2016 from the accepted 1989–2025 series. Changing
the operator does not change or recalibrate hydrology.

| Data or period | Use in this case |
|---|---|
| Daily weather | Daymet V4 R1 precipitation (mm/day) and minimum/maximum temperature (°C), weighted by polygon overlap; daily mean temperature is their average |
| Documented weather patches | nClimGrid-Daily only for leap-year December 31 entries, not general gap filling |
| PET | HydroCNHS Hamon PET (cm/day), derived from daily mean temperature and subcatchment latitude |
| Land cover | NLCD 2021 summarized at 60 m and treated as static across the historical simulation |
| Soil | SSURGO polygons and NRCS Soil Data Access attributes; no gSSURGO raster |
| Catchment geometry | Subcatchment boundaries, areas, centroid latitude, and river-path lengths |
| Observed flow | USGS 01447500 daily streamflow for hydrological calibration and validation |
| Calibration / validation | 1990–2010 / 2011–2020 at USGS 01447500 |

USGS 01447500 covers two of the seven units. The other five are not independently
gauge-validated units. Read [hydrology, parameters, and C&V](hydrology.md) for
the accepted data, metrics, and forward-simulation boundary.

The accepted hydrology has calibration/validation KGE of **0.733/0.711** and NSE
of **0.443/0.458** at that gauge. These values assess the inflow model, not the
LLM operator. Native model-building and calibration procedures are covered by
the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
The case-specific parameter tables and full metrics remain in the C&V reference.

## Common case setup

| Item | Teaching setting |
|---|---|
| Reservoir | One controlled F.E. Walter node and one agent |
| Inflow | Saved daily HydroCNHS simulated inflow, m³/s |
| Initial storage | 2,457,848.279729185 m³; explicit assumption |
| Reservoir losses | Direct precipitation, evaporation, seepage, and withdrawals are zero |
| Downstream routing | `UH=[1.0]`; identity routing |

The operator proposes release; shared physics enforces feasibility, updates
storage, calculates spill, and routes implemented outflow.

## Method inputs

| Method | Additional decision input |
|---|---|
| Rule-based | Registered rule parameters and inflow statistics |
| LLM with available information | Daily state, seasonal instructions, short history |
| LLM with retrieved knowledge | The same information plus selected local guidance |

Model identity belongs in the model settings and saved provenance. It does not
replace these public method names.

## Seasonal pool levels

The current case uses study-defined compliance windows in ft N.G.V.D. They are
research settings, not an official annual operating schedule.

| Season | Dates, inclusive | Pool-level check |
|---|---|---|
| Winter hold | November 1–March 14 | 1297–1303 ft, near the 1300 ft conservation pool |
| Spring fill | March 15–May 9 | 1300–1370 ft |
| Summer | May 10–October 14 | At or below 1370 ft; no lower bound in this check |
| Fall drawdown | October 15–October 31 | 1300–1370 ft and falling |

The [versioned criteria](seasonal_pool_criteria.json) retain exact dates, bands,
and the shared instruction. A compliance count is a diagnostic for these study
criteria; it is not official operating acceptance.

## Where to continue

- [Configuration and commands](../../tutorials/fe_walter.md)
- [Hydrology, parameters, and C&V](hydrology.md)
- [Daily coupling](coupling.md)
- [Current saved annual results](coupled/README.md#current-saved-2016-results)
- [Current teaching results](results.md)
- [Engine comparison evidence](engine_comparison.md)
- [Main notebook](../../tutorials/main.ipynb)
- [Generic multi-reservoir notebook](../../tutorials/advanced.ipynb)
