# F.E. Walter case study

[English](README.md) | [繁體中文](README.zh-TW.md)

Use this research example after completing the generic workflow in
[Build a simulation](../../docs/BUILD_SIMULATION.md). It applies one accepted
HydroCNHS hydrological boundary and one physical reservoir model to three
operation methods: a rule example, an LLM with available information, and an LLM
with retrieved knowledge. The methods share the same physics, so differences can
be traced to decision inputs and logic rather than different water accounting.

For the exact current configuration sequence, continue to
[F.E. Walter: configure the reservoir agent](../../tutorials/fe_walter.md).

## Site and study scope

F.E. Walter Dam is near White Haven, Pennsylvania, at the confluence of the
Lehigh River and Bear Creek in Carbon and Luzerne counties. The dam was
constructed in 1961. Its official authorized purposes are **Flood Risk
Management** and **Recreation**. Releases also support downstream whitewater
boating and fishing when stored water and flood-management priorities allow.
See the U.S. Army Corps of Engineers
[project page](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/),
[re-evaluation study](https://www.nap.usace.army.mil/Missions/Factsheets/Fact-Sheet-Article-View/Article/490871/francis-e-walter-dam-re-evaluation-study/),
and [flow-management plan and schedule](https://www.nap.usace.army.mil/Missions/Civil-Works/Francis-E-Walter-Dam/Flow-Management-Plan-Schedule/).

```{figure-md} fe-walter-study-area
:class: study-area-figure

![F.E. Walter modeled catchment, rivers, dam, and gauge](../../docs/figures/fe-walter-catchment.png)

**Figure 1.** Modeled subcatchments, dam, gauge, and 1996–2025 mean annual
precipitation. The seven modeled contributing units total **750.811 km²**. This
is modeled watershed area, not official reservoir surface area or project
property area. The native model's separate 1 ha artificial aggregation outlet
is excluded. **Source credits:** Esri, CGIAR, USGS, data.pa.gov, TomTom, Garmin,
SafeGraph, METI/NASA, EPA, NPS, USDA, USFWS, New Jersey Office of GIS, FAO, and
NOAA.
```

## Accepted hydrological boundary

The upstream model is semi-distributed. Seven geographic subcatchments retain
their own weather, area, latitude, land and soil attributes, and flow length.
GWLF generates runoff and Lohmann routing delivers it to the dam. Operation
experiments use the resulting daily inlet flow; changing the operator does not
recalibrate hydrology.

| Data or period | Use in this case |
|---|---|
| Daily weather | Daymet V4 R1 precipitation, minimum temperature, and maximum temperature, weighted by polygon overlap |
| Documented weather patches | nClimGrid-Daily only for leap-year December 31 entries, not general gap filling |
| PET | HydroCNHS Hamon PET derived from daily mean temperature and subcatchment latitude |
| Land cover | NLCD 2021 summarized at 60 m and treated as static across the historical simulation |
| Soil | SSURGO polygons and NRCS Soil Data Access attributes; no gSSURGO raster |
| Native continuous period | 1989–2025, with 1989 as warm-up |
| Calibration / validation | 1990–2010 / 2011–2020 at USGS 01447500 |
| Forward period | 2021–2025; a forward simulation, not additional gauge validation |

USGS 01447500 covers two of the seven units. The other five are not independently
gauge-validated units. Read [Hydrology, parameters, and C&V](hydrology.md) for
the accepted data and metrics. To build and calibrate another basin, use the
[official HydroCNHS manual](https://cylin928.github.io/HydroCNHS/) and
[HydroCNHS setup](../../docs/HYDROLOGY_SETUP.md); this overview does not repeat
the native construction or calibration workflow.

## Common case setup

| Item | Setting and interpretation |
|---|---|
| Reservoir | One controlled F.E. Walter reservoir and one decision unit |
| Inflow | Frozen daily HydroCNHS simulated inlet flow, m³/s |
| Initial storage | 2,457,848.279729185 m³ (1,992.61 acre-ft); integration assumption, not an observed January 2016 state |
| Reservoir losses | Zero direct precipitation, evaporation, seepage, and withdrawals in the reservoir kernel |
| Downstream routing | Identity unit hydrograph, `UH=[1.0]`; interface assumption, not calibrated travel time |
| Physical calculation | One storage update; implemented controlled release plus spill enters downstream routing once |

The LLM never supplies catchment inflow or performs water accounting. The shared
physical kernel applies water availability and release limits to every method,
computes storage and spill, and passes the implemented outflow downstream.

## Distinguish hydrology inputs from LLM-visible information

| Information | Hydrology / physics use | LLM use |
|---|---|---|
| Daymet weather, PET, land, soil, and HydroCNHS parameters | Produce accepted daily inlet flow | Not automatically shown to the LLM |
| Current date, inlet flow, beginning pool elevation and up to two completed decisions | Describe the daily operating state | Included in the daily case message; the separate storage-volume line is disabled in this example |
| Seasonal operating target | Does not alter hydrology | Included explicitly in both current LLM methods |
| Retrieved operating guidance | Does not alter hydrology or physics | Added only for the retrieved-knowledge method |
| Proposed release | Checked against physical state and limits | Generated by the selected rule or LLM method |

This separation prevents hydrological inputs from becoming unstated model
knowledge. The saved messages and trace show exactly what each daily LLM
decision could use.

## Start with the current 2016 configurations

The maintained comparison uses `gemma4:12b`, temperature 0.7, and explicit v2
entry files:

| Method input | File |
|---|---|
| LLM with available information | [`coupled/llm_available.gemma4.yaml`](coupled/llm_available.gemma4.yaml) |
| LLM with retrieved knowledge | [`coupled/llm_knowledge.gemma4.yaml`](coupled/llm_knowledge.gemma4.yaml) |
| Shared model profile | [`coupled/models.gemma4.yaml`](coupled/models.gemma4.yaml) |
| Rule example | [Rule-based operation](benchmark/README.md) |

The older Gemma 3 files remain unchanged as preserved inputs. Do not use them to
claim reproduction of the current Gemma 4 comparison. Follow the
[configuration tutorial](../../tutorials/fe_walter.md) for the exact files,
commands, success checks, and output locations.

## Seasonal pool levels

The current case uses four **study-defined** compliance windows, in ft N.G.V.D.
The two current prompt variants use the same windows. These settings are not an
official annual operating schedule.

| Season | Dates, inclusive | Pool-level check |
|---|---|---|
| Winter hold | November 1–March 14 | 1297–1303 ft, near the 1300 ft conservation pool |
| Spring fill | March 15–May 9 | 1300–1370 ft |
| Summer | May 10–October 14 | At or below 1370 ft; no lower bound in this check |
| Fall drawdown | October 15–October 31 | 1300–1370 ft and falling |

March 15, May 10, and October 15 belong to the later season. Height limits
include both endpoints. The [versioned criteria](seasonal_pool_criteria.json)
contain the dates, bands, and shared instruction:

```text
Operation target: Your goal is to keep the water level within the designated seasonal pool levels.
From November 1 through March 14, keep the pool near the conservation pool at
1300.0 ft N.G.V.D., within 1297.0 to 1303.0 ft.
From March 15 through May 9, keep the pool between 1300.0 and 1370.0 ft and,
when hydrologic conditions allow, fill toward 1370.0 ft by May 10.
From May 10 through October 14, keep the pool at or below 1370.0 ft.
From October 15 through October 31, keep the pool between 1300.0 and 1370.0 ft
and lower it toward 1300.0 ft by November 1.
```

### Check a saved pool-level series

```sh
python examples/fe_walter/check_pool_levels.py examples/fe_walter/reference_outputs/long_term_dkp/plotted_daily.csv --output runs/fe-walter-seasonal-pool-v1.csv
```

Run this from the repository root with a new output filename. The script writes
a separate CSV with input and criteria hashes and refuses to overwrite an
existing file. It does not run a model, simulation, or policy audit.

The supplied `pool_elevation_start_ft` values are beginning-of-day snapshots,
not subdaily peaks or end-of-day compliance. During fall, “falling” means lower
than the immediately preceding calendar day's snapshot; a flat day fails,
including at 1300 ft. Missing or nonfinite levels and missing fall history yield
`UNKNOWN`; an observed band violation remains `FAIL`. No extra numeric tolerance
is applied. Reference decision audits retain their original target logic. The
historical series above was not generated with the revised prompt.

## Compare the methods through common physics

| Method | Decision source | Method-specific input |
|---|---|---|
| [Rule-based operation](benchmark/README.md) | Hanasaki-based daily flood-control example | Rule parameters and historical statistics |
| [LLM with available information](zero_shot/README.md) | Case instructions and daily state | Current Gemma 4 profile and explicit case prompt |
| [LLM with retrieved knowledge](dkp/README.md) | Same interface plus retrieved guidance | Current Gemma 4 profile, prompt, and knowledge source |

The rule follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation of
[Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
It is a registered case rule, not a native HydroCNHS operating policy. The
[daily coupling chapter](coupling.md) explains how all three methods pass through
the same reservoir physics and downstream routing.

## Read the results

Read current and historical results separately. Start with the
[latest Gemma 4 comparison](coupled/README.md#verified-2016-results).
[Historical results and decision records](results.md) preserve the earlier 2020
walkthrough and 2016–2020 study.

| Saved evidence | Period and model | Purpose |
|---|---|---|
| Current original-code/framework comparison | 2016-01-01–12-31; 366 days per engine and LLM method; `gemma4:12b`, temperature 0.7 | Water levels, controlled release, seasonal compliance, and same-reply engineering checks |
| Earlier three-method annual example | 2016-01-01–12-31; 366 days per method; LLM methods use `gemma3:4b`, temperature 0.7 | Preserved earlier configuration, separate from the current comparison |
| Historical three-day tutorial | 2016-01-01–01-03; LLM methods use `gemma3:4b`, temperature 0.7 | Preserved teaching snapshots and original audit verdicts; not the current first-run route |
| One-year results walkthrough | 2020-01-01–12-31; 366 days from the historical retrieved-knowledge record | Seasonal operation and individual decisions |
| Historical retrieved-knowledge experiment | 2016-01-01–2020-12-31; `gemma4:12b`, temperature 0.7 | Complete 1,827-day trajectory and decision behavior |

The five-year record belongs to the historical retrieved-knowledge experiment.
No matching five-year rule or available-information trajectory is supplied. The
three-day tutorial and historical run have different model versions and code
provenance. Their seasonal YAMLs were checked offline but not rerun; saved
exchanges retain the original instructions and verdicts.

The [main notebook](../../tutorials/main.ipynb) preserves the historical
three-day tutorial. The [advanced notebook](../../tutorials/advanced.ipynb)
explains multiple reservoirs.
