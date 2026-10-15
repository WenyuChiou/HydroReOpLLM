# FE Walter case study

[English](README.md) | [繁體中文](README.zh-TW.md)

One reservoir, one hydrological setting and three operation methods.
Prepare the common case here, then choose a method and follow its decisions to the results.

## The site and hydrological background

F.E. Walter Reservoir lies on the Lehigh River in the Delaware River Basin.
The upstream model is **semi-distributed**: seven geographic subcatchments retain their own forcing, area and flow length.
**GWLF** generates runoff and **Lohmann routing** delivers it to the reservoir.

![FE Walter catchment, rivers and gauges](../../docs/figures/fe-walter-catchment.png)

The frozen simulation supplies reservoir inflow; operation experiments do not recalibrate or recompute it.
The accepted hydrological calibration uses **1990–2010** and validation uses **2011–2020**.
USGS 01447500 covers two of the seven units; the remaining five are not independently gauged validation units.

Hydrological parameters and C&V belong to the [native HydroCNHS workflow](../../docs/HYDROLOGY_SETUP.md).
This case focuses on how operating rules, information and language-model proposals affect reservoir operation.

## Common case setup

| Item | Setting |
|---|---|
| Reservoir | FE Walter; one controlled reservoir and one decision unit |
| Inflow | Frozen daily simulated inflow; m³/s |
| Initial storage | 2,457,848.279729185 m³, or 1,992.61 acre-ft |
| Reservoir losses | Zero precipitation, evaporation, seepage and withdrawals |
| Downstream routing | Identity unit hydrograph, `UH=[1.0]` |
| Physical calculation | Implemented controlled release + spill; one storage update and one routing injection |

Initial storage is an integration assumption, not an observed January 2016 state.
Identity downstream routing tests the coupling interface; it is not calibrated river travel time.

Prepare these files before changing the operation method:

| File | What it controls |
|---|---|
| [Case JSON](../../cases/fe_walter_ollama_demo/case.json) | Reservoir limits, initial storage and river connections for the three-day tutorial |
| [Inflow CSV](../../cases/fe_walter_reference/inflows.csv) | Daily inflow and its source pin |
| Experiment YAML | Dates, method, model, auditors and new output location |
| Prompt file, for LLM methods | Fixed operating instructions and response fields |
| Knowledge file, when selected | Sourced operating guidance and retrieval settings |

The [simulation design chapter](../../docs/BUILD_SIMULATION.md) explains how to adapt these components to your own reservoir.

## Choose an operation method

| Method | Decision source | Method-specific setup |
|---|---|---|
| [Rule-based operation](benchmark/README.md) | Hanasaki-based daily flood-control rule | Rule parameters and historical statistics |
| [LLM with available information](zero_shot/README.md) | Instructions plus current information | Model, independent prompt and response fields |
| [LLM with retrieved knowledge](dkp/README.md) | Same interface with retrieved operating guidance | Prompt, knowledge source and retrieval |

The rule follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation of [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
The [rule chapter](benchmark/README.md#sources-and-adaptation) identifies its daily adaptation; HydroCNHS itself does not supply this particular policy.

Each method chapter explains **configuration → operation method → execution → saved decisions**.
Shared physical setup is defined once on this page.

## Read the results

Use [Results and decision records](results.md) for the **full 2016–2020 daily trajectory**:
inflow and outflow, pool elevation, storage, and every recorded audit verdict.

| Saved evidence | Period and model | Purpose |
|---|---|---|
| Three-method tutorial | 2016-01-01–01-03; LLM methods use `gemma3:4b`, temperature 0.7 | Learn each method under common three-day conditions |
| Historical retrieved-knowledge experiment | 2016-01-01–2020-12-31; `gemma4:12b`, temperature 0.7 | Inspect the complete 1,827-day trajectory and decision behaviour |

The five-year record belongs to the historical DKP experiment.
No matching five-year rule-based or available-information trajectory is supplied.
The three-day tutorial and the historical run have different model versions and code provenance.

The [main notebook](../../tutorials/main.ipynb) preserves the three-day tutorial.
The [advanced notebook](../../tutorials/advanced.ipynb) explains multiple reservoirs.

<details>
<summary>Map downloads</summary>

[PNG](../../docs/figures/fe-walter-catchment.png) · [SVG](../../docs/figures/fe-walter-catchment.svg) · [PDF](../../docs/figures/fe-walter-catchment.pdf) · [Editable ArcGIS project](../../data/figures/manual_map/fe-walter-arcgis-source.zip)

The editable project requires ArcGIS Pro. Its Esri basemap layers need an internet connection.
The manual displays the saved figure without contacting a map service.

</details>
