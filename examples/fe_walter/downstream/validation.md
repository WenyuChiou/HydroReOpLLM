# Check the downstream hydrology

[English](validation.md) | [繁體中文](validation.zh-TW.md)

This workflow tests the watershed and river between **White Haven (USGS 01447800)** and **Lehighton (USGS 01449000)**. It supplies observed White Haven discharge to HydroCNHS, adds runoff from the intervening subcatchments, and compares the routed flow with Lehighton observations. The accepted upstream calibration remains available in the [hydrology reference](../hydrology.md).

Follow the executable steps in {download}`the downstream validation notebook <../../../tutorials/downstream_validation.ipynb>`. Install the geometry dependencies from the repository root with `python -m pip install -e ".[gis]" -c environment/requirements-bundled.txt`. Keep study inputs and run directories outside the repository.

## What the workflow does

1. Preserve daily discharge, station identifiers, units and USGS quality flags.
2. Check the lower subcatchments, weather, native model and contributing flow paths.
3. Check transferred parameters with a fixed parameter run, or calibrate the new lower model using the calibration years.
4. Freeze the selected parameters and evaluate the independent validation years.
5. Retain daily results and input hashes for the later reservoir-operation comparison.

The calibration search stops at the end of 2010. Validation observations do not enter its objective. The later operation evaluation supplies simulated flow at White Haven in place of its observations. That flow includes reservoir outflow and runoff entering the short reach between the dam and White Haven.

| Stage | Period | Use |
|---|---|---|
| Warm-up | 1989 | Initialize watershed and river states; omit from scores |
| Calibration | 1990–2010 | Select lower-watershed parameters using observed upstream flow |
| Validation | 2011–2020 | Evaluate the same parameters on independent years |
| Later operation evaluation | 2021–2025 | Compare the three operators with common, fixed hydrology |

![Observed upstream flow and local runoff are routed to the downstream comparison.](../../../docs/figures/downstream-validation.svg)

*Figure 1. White Haven observations supply the upstream boundary. HydroCNHS adds intervening runoff and routes the combined flow to Lehighton. The comparison uses separate calibration and validation years. [Editable draw.io source](../../../docs/figures/downstream-validation.drawio).*

## Files to prepare

Start with the complete [validation configuration](validation.yaml) and [calibration settings](calibration.yaml). The notebook displays both files and explains where to fill their paths. Empty input references and parameter groups identify preparation that remains to be done.

| File | Contents |
|---|---|
| `observations.csv` | `date,station_id,flow_cfs,qualifiers`; both gauges, with original daily date labels |
| `source_manifest.json` and `usgs_daily.json` | Source URL, raw response, units, dates and matching SHA256 hashes |
| Native lower model | GWLF subcatchments and Lohmann connections from White Haven to Lehighton |
| Weather CSV or CSV.gz | `date,subbasin_id,precipitation_mm,temperature_c,pet_cm`; every day and weather-driven unit |
| Partition JSON | Gauge basin polygons and lower subcatchments in EPSG:5070, matching native unit IDs and areas |
| Calibration settings | Explicit parameter targets, scientific bounds, population and generation settings |

The partition describes **Lehighton basin minus White Haven basin**. Its JSON contains `crs`, `upstream_gauge`, `downstream_gauge`, `upstream_basin`, `downstream_basin`, `subbasins`, and `outlet_precision`. Basin values are GeoJSON geometries; `subbasins` is a list of GeoJSON Features whose `properties.subbasin_id` matches the native model. Each lower unit and the observed boundary must contribute exactly once. The check retains the precision statement for the gauge divides.

Each calibration parameter group declares `name`, `mode`, `bounds` and `paths`. A `set` group assigns one common value to its listed native `Pars` targets. A `scale` group multiplies each target's initial value, retaining its local differences. Bounds and target groups should follow the prepared physical attributes and the documented hydrological assumptions. The accepted upper model is preserved separately.

The search maximizes KGE (2009). Its roulette selector receives the positive score `1 / (2 - KGE)`, which preserves KGE ordering even when KGE is negative. Candidate records retain both values; native optimizer summaries report the transformed selection score. Final calibration and validation reports retain the original KGE.

## Execution and outputs

The notebook gives the full commands for three explicit actions:

| Action | Calculation | New outputs |
|---|---|---|
| `check` | Read and validate inputs | `preflight.json`; exit code 2 identifies missing preparation |
| `run` | Run the native lower model with fixed parameters | `preflight.json`, `daily.csv`, `report.json` |
| `calibrate` | Native GA search on calibration years, then fixed-parameter C&V run | The above, plus `candidate_evaluations.jsonl`, `calibration.json`, `calibrated_model.yaml` and native optimizer records |

`daily.csv` reports discharge in **cfs**, with both observation flags and the downstream eligibility mask. `report.json` uses the existing flow evaluator: MAE/RMSE/bias in m³/s, relative volume bias, NSE and KGE (2009). Undefined metrics retain a reason. A completed run reports execution and scores; research acceptance requires interpreting those results.

USGS estimated records carrying `A,e` are included by the supplied policy and counted separately. Change the quality policy explicitly when performing a sensitivity check. An unavailable or excluded upstream boundary day stops the native run; the workflow applies no interpolation. Missing downstream observations remain visible in the score counts.

## Current preparation

Both historical gauge series have been preserved for 1989–2020, with **11,688 valid daily records per gauge and no missing dates**. Their raw responses, normalized tables and provenance remain in the external research evidence. The nine lower units shown on the study-area map are spatial preparation. Their complete daily weather, native model and checked White Haven partition still need to be supplied before a real calibration or validation run can begin.

This observation-boundary test evaluates the combined intervening runoff and routing. Its results help interpret the later Hanasaki/LLM comparison. Separate tributary observations would provide additional constraints on individual subcatchments.

The setup follows the upstream-to-downstream evaluation approach described in the [USACE HEC-HMS Applications Guide](https://www.hec.usace.army.mil/software/hec-Hms/documentation/HEC-HMS_Applications_Guide_20231107.pdf); calibration and independent validation follow the [USACE calibration procedure](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/calibration/summary-of-the-calibration-procedure).
