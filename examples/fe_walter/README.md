# FE Walter case study

[English](README.md) | [繁體中文](README.zh-TW.md)

One reservoir, one hydrological setting and three operation methods.
Follow **hydrological setting → coupled daily workflow → operation method → results**.
Prepare the shared case here; the linked chapters explain each step.

## The site and hydrological background

F.E. Walter Reservoir lies on the Lehigh River in the Delaware River Basin.
The upstream model is **semi-distributed**: seven geographic subcatchments retain their own forcing, area and flow length.
**GWLF** generates runoff and **Lohmann routing** delivers it to the reservoir.

![FE Walter catchment, rivers and gauges](../../docs/figures/fe-walter-catchment.png)

The frozen simulation supplies reservoir inflow; operation experiments do not recalibrate or recompute it.
The accepted hydrological calibration uses **1990–2010** and validation uses **2011–2020**.
USGS 01447500 covers two of the seven units; the remaining five are not independently gauged validation units.

See [Hydrology, parameters and C&V](hydrology.md) for this case; the [native HydroCNHS workflow](../../docs/HYDROLOGY_SETUP.md) explains how to build another catchment.
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

The reservoir inflow is **simulated by HydroCNHS**, not supplied by the LLM:
subcatchment weather → GWLF runoff → Lohmann upstream routing → summed inflow
at the dam. The operations runner reads that frozen daily series; it does not
rerun rainfall–runoff at each decision. The [case hydrology chapter](hydrology.md)
lists weather, observed flow, the seven subcatchments, accepted parameters and
calibration/validation results.

Prepare these files before changing the operation method:

| File | What it controls |
|---|---|
| [Case JSON](../../cases/fe_walter_ollama_demo/case.json) | Reservoir limits, initial storage and river connections for the three-day tutorial |
| [Inflow CSV](../../cases/fe_walter_reference/inflows.csv) | Daily inflow and its source pin |
| Experiment YAML | Dates, method, model, auditors and new output location |
| Prompt file, for LLM methods | Fixed operating instructions and response fields |
| Knowledge file, when selected | Sourced operating guidance and retrieval settings |

The [simulation design chapter](../../docs/BUILD_SIMULATION.md) explains how to adapt these components to your own reservoir.

## Seasonal pool levels

The current case uses four **study-defined** compliance windows, in ft N.G.V.D.
The two new prompt variants use the same windows. These are study settings, not an official annual operating schedule.

| Season | Dates, inclusive | Pool-level check |
|---|---|---|
| Winter hold | November 1–March 14 | 1297–1303 ft, near the 1300 ft conservation pool |
| Spring fill | March 15–May 9 | 1300–1370 ft |
| Summer | May 10–October 14 | At or below 1370 ft; no lower bound in this check |
| Fall drawdown | October 15–October 31 | 1300–1370 ft and falling |

March 15, May 10 and October 15 belong to the later season. Height limits include both endpoints.
The [versioned criteria](seasonal_pool_criteria.json) contain the dates, bands and shared instruction:

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

For a new experiment, use the [available-information YAML](zero_shot/experiment.seasonal.ollama.yaml)
or [retrieved-knowledge YAML](dkp/experiment.seasonal.ollama.yaml).
Both select `system_prompt_mode: custom`, separate prompt files and new output locations.
Only the operation-target paragraph changes; response fields and reference-method code stay the same.
These variants have been checked without a provider request; no new LLM results are supplied.
Saved exchanges retain their original winter/summer instruction and audit verdicts.

### Check a saved pool-level series

```sh
python examples/fe_walter/check_pool_levels.py examples/fe_walter/reference_outputs/long_term_dkp/plotted_daily.csv --output runs/fe-walter-seasonal-pool-v1.csv
```

Run from the repository root and use a new output filename. The script writes a separate CSV
with input/criteria hashes and refuses to overwrite an existing file.
It does not run a model, simulation or policy audit.

The supplied series contains **beginning-of-day** `pool_elevation_start_ft` values.
This checks daily snapshots, not subdaily peaks or end-of-day compliance.
In fall, “falling” means strictly lower than the immediately preceding calendar day's snapshot;
a flat day fails, including at 1300 ft. Missing/nonfinite levels or missing fall history produce
`UNKNOWN`; an observed band violation remains `FAIL`. No extra numeric tolerance is applied.
Reference decision audits keep their original target logic and remain separate from this
new pool-level assessment. The saved trajectory was not generated with the revised prompt.

## Follow the coupled daily workflow

Read [the daily coupling chapter](coupling.md) before selecting a method.
Each day, HydroCNHS routes water to the Dam API; the policy requests release,
reservoir physics updates storage and spill, and actual outflow enters downstream routing.
Implemented release and ending storage feed the next decision.

The current examples read precomputed hydrological inflow.
The same chapter explains weather-driven native wiring and the verification it still requires.

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

Use [Results and decision records](results.md) to follow **one year of daily operation (2020)**,
then the full 2016–2020 record: flow, pool elevation, storage and audit verdicts.

| Saved evidence | Period and model | Purpose |
|---|---|---|
| Three-method tutorial | 2016-01-01–01-03; LLM methods use `gemma3:4b`, temperature 0.7 | Learn each method under common three-day conditions |
| One-year results walkthrough | 2020-01-01–12-31; 366 days from the historical retrieved-knowledge record | Inspect seasonal operation and individual decisions |
| Historical retrieved-knowledge experiment | 2016-01-01–2020-12-31; `gemma4:12b`, temperature 0.7 | Inspect the complete 1,827-day trajectory and decision behaviour |

The five-year record belongs to the historical DKP experiment.
No matching five-year rule-based or available-information trajectory is supplied.
The three-day tutorial and the historical run have different model versions and code provenance.

The [main notebook](../../tutorials/main.ipynb) preserves the three-day tutorial.
The [advanced notebook](../../tutorials/advanced.ipynb) explains multiple reservoirs.
