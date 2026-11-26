# Native HydroCNHS hydrology setup

<div class="hero-band" markdown="1">

HydroReOpLLM builds on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) for watershed rainfall–runoff modeling, channel routing, and reservoir simulation. You can either supply **pre-computed local inflows** (`inflows.csv`) or couple directly to a **HydroCNHS catchment model** (`GWLF` or `ABCD` with Lohmann routing).

</div>

## Two hydrology entry paths

Choose the workflow that matches how your basin inflows are prepared:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Path A: Prepared inflows (`llm-reservoir-experiment.v1`)

- **Best when**: You already have calibrated local runoff or gauge-derived subbasin inflows (`examples/template/` and `examples/fe_walter/`).
- **Inputs**: `case.json` + `inflows.csv` (`date,node,local_inflow_cms`).
- **Behavior**: HydroReOpLLM reads `local_inflow_cms` directly without re-running rainfall–runoff, then routes reservoir releases downstream.

</div>
<div class="panel-card" markdown="1">

### Path B: Native HydroCNHS coupled (`hydroops-coupled-simulation.v2`)

- **Best when**: You want HydroCNHS to simulate watershed runoff (`GWLF` / `ABCD`) and Lohmann routing from daily or hourly weather forcing before operating reservoirs.
- **Inputs**: `experiment.yaml`, `hydrology.yaml`, HydroCNHS model YAML, `forcing.csv` (or `.csv.gz`), and `reservoirs.yaml`.
- **Behavior**: `prepare` runs the catchment model over spin-up + operation dates, writes `inflows.csv` for inspection, and `run` operates the reservoirs.

</div>
</div>

### Prepared inflow CSV example (`inflows.csv`)

Every non-reservoir node (`inflow_node`, `junctions`, `outlets`) needs one non-negative **incremental local flow** (`m³/s`) per day, excluding water routed from upstream reservoirs:

```csv
date,node,local_inflow_cms
2026-03-26,upper_local,4.0
2026-03-26,lower_local,1.5
2026-03-26,outlet,0.0
2026-03-27,upper_local,6.0
2026-03-27,lower_local,2.0
2026-03-27,outlet,0.0
```

## Native HydroCNHS model and forcing

In a coupled `hydroops-coupled-simulation.v2` study, `hydrology.yaml` connects an **agent-free** HydroCNHS catchment model (`ABM: null`) to the reservoir network in `reservoirs.yaml`.

### `hydrology.yaml` schema and inflow bindings

```yaml
# hydrology.yaml
model: synthetic_catchments.yaml      # Agent-free HydroCNHS GWLF/ABCD + Lohmann YAML
forcing: forcing.csv                  # Daily weather table (date, subbasin_id, ...)
zero_flow_nodes: []                   # Native outlets fixed at 0 m3/s (absent from forcing.csv)
diagnostics: true                     # Optional: save GWLF states & water-balance diagnostics
inflow_bindings:
  inlet_a:
    runoff: basin_a                   # Incremental local runoff from subbasin basin_a
  inlet_b:
    routed: gauge_upstream            # Routed flow from gauge_upstream (all upstream subbasins)
  river_out:
    constant: 0                       # Outlet adds zero local lateral runoff
```

| Field in `hydrology.yaml` | Required | Role in hydrological coupling |
| --- | --- | --- |
| `model` | Yes | Calibrated HydroCNHS YAML (`WaterSystem.RainfallRunoff: GWLF \| ABCD`, `Routing: Lohmann`, `ABM: null`). |
| `forcing` | Yes | CSV or `.csv.gz` with columns `date` (or `timestamp`), `subbasin_id`, `precipitation_mm`, `temperature_c`, `pet_cm`. |
| `zero_flow_nodes` | No | Native outlets assigned `0.0 m³/s` without weather forcing entries. |
| `inflow_bindings` | Yes | 1-to-1 mapping for every `inflow_node`, `junction`, and `outlet` using `runoff: <unit>`, `routed: <outlet>`, or `constant: 0`. |
| `engine` & `forcing_step` | No | Defaults to daily (`gwlf_daily` / `daily`). Set `gwlf_hourly` / `hourly` for hourly GWLF runs. |
| `diagnostics` | No | When `true`, exports per-subbasin GWLF water-balance records and final states during `prepare`. |
| `prepared_from` | No | Path to a previously completed `prepare` folder to reuse matching `inflows.csv` directly. |

<div class="callout callout-warn" markdown="1">

**Never double-count upstream catchments.** A `routed:` binding already sums every subbasin upstream of that native outlet, whereas a `runoff:` binding takes only one subbasin's lateral runoff. If two bindings share any contributing catchment—or if an inflow CSV includes upstream dam releases—water is counted twice and `check` rejects overlapping bindings.

</div>

### Forcing units and warm-up window

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **Daily unit convention**: Supply precipitation in `mm/day` (converted internally to `cm/day` for GWLF/ABCD), PET in `cm/day`, and temperature in `°C` (negative values allowed for snowmelt).
- **Warm-up (spin-up) vs. operation window**: Set `WaterSystem.StartDate`–`EndDate` in the HydroCNHS model earlier than `start_date`–`end_date` in `experiment.yaml` so soil moisture and groundwater spin up realistically before reservoir operation begins. Reservoir `initial_storage_m3` always applies on the **first operation day** (`start_date`), regardless of how long the hydrologic warm-up runs.

## GWLF states and calibration boundary

- **GWLF initial states**: Soil moisture (`S0`), unsaturated zone (`U0`), snowpack (`SnowS`), and groundwater/baseflow (`B0` / `BF0`) are initialized per subbasin in the HydroCNHS model file (`Inputs` and `Pars`). Note that a daily baseflow depth (`BF0`) is not equivalent to an hourly deep-storage state (`HOURLY_GWLF.md`).
- **Calibration stays upstream**: HydroReOpLLM runs your calibrated HydroCNHS model deterministically as supplied; watershed delineation, parameter calibration, and bias correction remain your responsibility before coupling.

## HydroCNHS ModelBuilder, Dam nodes, and routing

When running daily simulations, HydroReOpLLM registers its neutral `LLMReservoirAgent` (`examples/llm_reservoir_abm.py`) as a HydroCNHS `DamAPI` module:

1. Each controlled reservoir connects one inlet (`inflow_node`, link factor `-1`) and one outlet (`reservoir`, link factor `+1`).
2. Network connections route `controlled_release_cms + spill_cms` through your declared `fraction` splits and `unit_hydrograph` travel-time weights (`index 0` = same step, `index 1` = `+1` step, summing to `1.0`).
3. HydroCNHS steps through the basin in upstream-to-downstream topological order, guaranteeing upstream outflows are committed and lagged before downstream reservoirs observe their inflow.

## Preparation outputs and mass-balance diagnostics

Run `reservoir-experiment prepare experiment.yaml` whenever you want to inspect watershed runoff before launching reservoir agents:

| Output artifact | Location | What to inspect |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | Simulated incremental local inflows (`m³/s`) for the operation window only—compare against gauge expectations before `run`. |
| `case.json` & `experiment.yaml` | `<output>/` | Compiled operation-ready case and experiment configuration used during `run`. |
| `hydrology_diagnostics.json` & `hydrology_state.json` | `<output>/` (when `diagnostics: true` or hourly) | Subbasin soil/groundwater/snow fluxes, water-balance residuals, and ending states. |
| `network_balance.csv` & `reach_volume_trace.json` | `<output>/operation/` | Reservoir + channel storage water balance (`m³`) across the full run (`system_residual_m3` near zero). |

<div class="callout callout-info" markdown="1">

**Engineering closure vs. hydrologic skill.** A near-zero `system_residual_m3` confirms exact water conservation across routing and reservoir storage, not calibrated runoff accuracy against streamflow gauges. Always validate prepared inflows before interpreting reservoir policy results.

</div>
