# FE Walter: hydrology, parameters and calibration / validation

[English](hydrology.md) | [繁體中文](hydrology.zh-TW.md) · [Case study](README.md)

This chapter explains the hydrological boundary used by the reservoir decisions.
It records the accepted data, parameter derivation and C&V. A fixed-parameter
reproduction on 16 October 2026 recomputed the hydrology and metrics; it did not
search for new parameters or run an LLM. The main walkthrough remains focused on
the operation methods and their coupled effects.

## 1. From weather to dam inflow

**Subcatchment weather → HydroCNHS GWLF → Lohmann upstream routing → summed dam inflow.**

Seven real subcatchments retain local weather, area, latitude, soil/land attributes and flow length. The native YAML also contains a 1 ha computational aggregation outlet; the preserved runner assigns it zero runoff. It is not an eighth physical catchment.

Operation experiments read the frozen daily inflow. The LLM proposes release; common physics updates storage and spill, and downstream routing receives implemented total outflow. It does not change GWLF or upstream weather. Calibrated upstream Lohmann routing is separate from the three-day operation tutorial’s downstream `UH=[1.0]`, which is an interface demonstration.

## 2. Data and periods

| Input | Use in this case |
|---|---|
| Weather | Daymet V4 R1 daily precipitation and minimum/maximum temperature; polygon-area weighting. NOAA nClimGrid-Daily supplements only the documented leap-year December 31 entries, not general missing values. |
| Model input units | Temperature °C; precipitation and PET cm/day. The stored forcing precipitation is mm/day and is converted before GWLF. PET is preserved as supplied; its separate derivation is not documented in the retained source manifest. |
| Flow observations | USGS 01447500 daily streamflow for C&V. It covers two of the seven units; the other five have no separate gauge validation. |
| Land and soil | Annual NLCD 2021 and NRCS Soil Data Access map units/attributes. Hydrologic soil group and upper-100-cm available water inform CN2 and Ur; these are not a downloaded gSSURGO raster. |
| Geometry | Mapped subcatchment area, latitude and river-path length; native FlowLength is in metres. |
| Periods | Warm-up: 1989; calibration: 1990–2010; validation: 2011–2020; frozen forward simulation: 2021–2025. Native continuous run: 1989–2025; reservoir reference reports 1996–2025. |

## 3. Seven subcatchments

The preparation workflow retains the USGS calibration-basin boundary, the
01447720 diagnostic branch, and the remaining reservoir-upstream area. It
partitions these regions using NHDPlus HR catchments and directed flowlines,
then links their routes to the target outlet. Geometry and area checks use the
equal-area CRS EPSG:5070. The resulting seven units comprise two donor units
(`FEW-D-01/02`), three diagnostic units (`FEW-X-01/02/03`) and two residual units
(`FEW-R-01/02`). Only the donor pair drains through calibration gauge 01447500.

Land-cover and soil lookups supply each unit's initial curve number and available
water storage. The CN lookup combines marginal NLCD class fractions and soil-group
fractions; it is not a pixel-by-pixel land/soil overlay. Soil storage is an
area-weighted NRCS SDA `aws0100wta` value for the upper 100 cm, converted to mm in
the intermediate table. A dual soil group such as A/D uses D under the retained
undrained assumption.

The two calibrated adjustments preserve mapped local differences within bounds:

```text
CN2_i = clip(m_CN2 × CN_lookup_i, 25, 100)
Ur_i  = clip(m_Ur × AWS_i_mm / 10, 1, 15)   [cm]
```

The accepted values are `m_CN2 = 0.4359081674473122` and
`m_Ur = 0.6895206617730479`. For FEW-D-01, a lookup CN of 77.0779 and storage of
117.8577 mm yield CN2 33.5989 and Ur 8.1265 cm. These are effective model inputs,
not direct measurements of each hydrological process.

`CN2` controls direct runoff and is dimensionless; `Ur` is available soil-water capacity in cm. Displayed values are rounded; downloads and the native YAML retain full precision.

| Subcatchment | Area (ha) | Latitude (°) | Flow length (m) | CN2 | Ur (cm) |
|---|---:|---:|---:|---:|---:|
| FEW-D-01 | 4,118.43 | 41.17586 | 20,452.68 | 33.59889 | 8.12653 |
| FEW-D-02 | 20,092.14 | 41.21625 | 14,597.68 | 32.40945 | 7.40845 |
| FEW-R-01 | 13,284.60 | 41.20126 | 2,511.72 | 32.37751 | 7.08487 |
| FEW-R-02 | 6,787.55 | 41.12002 | 1.00 | 31.79762 | 7.50440 |
| FEW-X-01 | 6,878.79 | 41.12448 | 31,053.68 | 34.23231 | 7.49884 |
| FEW-X-02 | 8,200.22 | 41.05516 | 20,620.68 | 30.04543 | 8.44527 |
| FEW-X-03 | 15,719.40 | 41.15540 | 19,479.68 | 33.04439 | 8.03468 |

## 4. Shared GWLF and routing parameters

HydroCNHS `GA_DEAP` jointly selected **13 search values**: two common adjustments to mapped CN2/Ur, seven shared GWLF values and four shared Lohmann values. Nine parameters were not independently fitted for each ungauged unit. Below are final shared parameters; the preceding table contains the adjusted local CN2/Ur.

| Parameter | Role | Unit | Saved value |
|---|---|---|---:|
| `IS` | Interception / initial-abstraction coefficient | — | 0.392319499 |
| `Res` | Groundwater recession coefficient | day⁻¹ | 0.3112407406 |
| `Sep` | Deep seepage coefficient | day⁻¹ | 0.2083763352 |
| `Alpha` | Baseflow allocation coefficient | — | 0.008265514706 |
| `Beta` | Percolation / deep-seepage partition | — | 0.05468370457 |
| `Kc` | Evapotranspiration coefficient | — | 0.8493605974 |
| `Df` | Degree-day snowmelt coefficient | cm/(°C·day) | 0.5050611615 |
| `GShape` | Within-subcatchment unit-hydrograph shape | — | 0.4680630977 |
| `GScale` | Within-subcatchment unit-hydrograph scale | h | 4.998998848 |
| `Velo` | River wave velocity | m/s | 0.3800151307 |
| `Diff` | River diffusivity | m²/s | 2996.73159 |

The native YAML also preserves the 1989 initial fields `S0=2`, `U0=10`, `SnowS=5`. Antecedent hydrological state is separate from the operation tutorial’s assumed initial reservoir storage; choosing a new start date does not reconstruct either state automatically.

## 5. Accepted calibration and validation results

| Metric | Calibration 1990–2010 | Validation 2011–2020 |
|---|---:|---:|
| KGE (2009) | 0.7326 | 0.7112 |
| NSE | 0.4428 | 0.4576 |
| RMSE (m³/s) | 5.6774 | 4.6012 |
| PBIAS (%) | 0.0943 | 1.4072 |
| Mean peak timing error (days) | 2.4000 | 4.4000 |
| Mean relative peak-flow error (%) | 44.6945 | 57.1134 |
| False alarms / misses | 4 / 4 | 7 / 7 |
| Valid daily observations | 7670 | 3653 |

Positive PBIAS means overprediction. The CSV stores PFE as a fraction; this table multiplies it by 100. Peak metrics are event means with declared unmatched-event penalties: 15 observed events per period, at least seven days apart and one-to-one matching within ±7 days. The threshold comes only from calibration observations. These are gauge-scale hydrological metrics, not independent validation of the five ungauged units or acceptance of an LLM policy.

### Fixed-parameter reproduction

The 16 October 2026 replay recovered the preparation/evaluation source at commit
`8d59dcac2f9d06fe16030f68826b425d492c9529` and used its saved best parameters.
It rebuilt all seven CN2/Ur/shared-parameter rows from the retained physical
attribute table; every value matched the accepted native YAML exactly.

At gauge 01447500, it used only FEW-D-01/02 and their **gauge-specific** routing
lengths of 5,856 m and 1 m. The longer routes to the reservoir were not substituted
for these lengths. The observed calibration Q95 was 15.630899318784 m³/s and was
held fixed for validation. All 28 scalar metric comparisons matched the accepted
values within an absolute tolerance of 1e-9 and a relative tolerance of 1e-10.

| Connection checked | Reproduced result |
|---|---|
| Public HydroCNHS Model versus native-kernel gauge calculation | Maximum difference 3.02 × 10⁻¹⁴ m³/s |
| Seven-unit 1989–2025 continuous hydrology | 13,514 simulated days |
| Reservoir inflow, 1996–2025, versus preserved reference | 10,958 days; maximum difference 1.09 × 10⁻¹¹ cfs |
| Independent reservoir-inflow routing convolution | Maximum difference 1.14 × 10⁻¹³ m³/s |

[Reproduced metrics](hydrology_data/reproduced_cv_metrics_20261016.csv) and the
[reproduction record](hydrology_data/reproduction_20261016.json) retain values,
runtime, source hashes and tolerances. Raw daily outputs and recovered research
sources remain in the separate local evidence package. Geometry delineation and
raw land/soil intersections were not rerun; the replay begins with the retained
boundaries' attribute tables and saved forcing. No optimizer, model requests or
simulation network access occurred. This verifies reproducibility, not a new
calibration or acceptance of a weather-driven LLM experiment.

## 6. Files and sources

[Native model YAML](../../data/accepted/fe_walter_hydrology.yaml) · [Seven-subcatchment table](hydrology_data/subcatchments.csv) · [C&V CSV](hydrology_data/calibration_validation_metrics.csv) · [Source hashes](hydrology_data/provenance.json) · [Forcing/inflow manifest](../../data/accepted/historical_manifest.json)

The recovered preparation sources are `scripts/prepare_semidistributed_geometry.py`,
`scripts/prepare_subbasin_physical_attributes.py` and
`docs/parameter_initialization/README.md` at the source commit above. They belong
to the companion hydrology workspace; they are not required to run a supplied-inflow
operation example. Preserve their source version when rebuilding inputs for a new
catchment.

For building and calibrating another catchment, use [Native HydroCNHS setup](../../docs/HYDROLOGY_SETUP.md) and the [HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).

Next: [follow the coupled daily workflow](coupling.md), then choose an operation method.
[Return to the common case](README.md).
