# Native HydroCNHS hydrology setup

<div class="hero-band" markdown="1">

HydroReOpLLM builds on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) so you can drive reservoirs from **prepared inflow CSVs** or a **calibrated HydroCNHS watershed model** (`GWLF`/`ABCD` + Lohmann routing).

</div>

## Two hydrology entry paths

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Path A: Prepared inflows (`llm-reservoir-experiment.v1`)

- Best when you already have subbasin local inflows (`examples/template/`, `examples/fe_walter/`).
- Uses `case.json` + `inflows.csv` (`date,node,local_inflow_cms`) and routes dam releases downstream.

</div>
<div class="panel-card" markdown="1">

### Path B: Native HydroCNHS coupled (`hydroops-coupled-simulation.v2`)

- Best when running rainfall–runoff (`GWLF`/`ABCD`) and Lohmann routing from weather forcing.
- Uses `hydrology.yaml` + `forcing.csv` (or `.csv.gz`); `prepare` creates `inflows.csv` before `run` operates dams.

</div>
</div>

```csv
# inflows.csv (incremental local runoff in m³/s, excluding upstream dam releases)
date,node,local_inflow_cms
2026-03-26,upper_local,4.0
2026-03-26,lower_local,1.5
2026-03-26,outlet,0.0
```

## Native HydroCNHS model and forcing

### `hydrology.yaml` schema and inflow bindings

Connect an agent-free HydroCNHS model (`ABM: null`) to every `inflow_node`, `junction`, and `outlet` in `reservoirs.yaml`:

```yaml
model: synthetic_catchments.yaml      # HydroCNHS GWLF/ABCD + Lohmann YAML (ABM: null)
forcing: forcing.csv                  # date (or timestamp), subbasin_id, precipitation_mm, temperature_c, pet_cm
zero_flow_nodes: []                   # Native outlets fixed at 0 m³/s
diagnostics: true                     # Optional: export GWLF states & water-balance diagnostics
inflow_bindings:
  inlet_a: { runoff: basin_a }        # Single subbasin lateral runoff
  inlet_b: { routed: gauge_upstream } # Routed flow from all subbasins upstream of gauge_upstream
  river_out: { constant: 0 }          # Zero local lateral flow at outlet
```

| Field | Required | Role |
| --- | --- | --- |
| `model` | Yes | Calibrated HydroCNHS YAML (`RainfallRunoff: GWLF \| ABCD`, `Routing: Lohmann`, `ABM: null`). |
| `forcing` | Yes | Daily or hourly weather CSV (`.csv` or `.csv.gz`). |
| `zero_flow_nodes` | No | Native outlets assigned `0.0 m³/s` without weather entries. |
| `inflow_bindings` | Yes | 1-to-1 map for all non-dam nodes (`runoff`, `routed`, or `constant: 0`). |
| `engine`, `forcing_step` | No | Default daily (`gwlf_daily` / `daily`); set `gwlf_hourly` / `hourly` for hourly GWLF. |
| `diagnostics`, `prepared_from` | No | Export GWLF state/balance diagnostics or reuse an earlier `prepare` folder. |

<div class="callout callout-warn" markdown="1">

**Never double-count upstream catchments.** `routed:` includes every subbasin upstream of that outlet, whereas `runoff:` takes one subbasin. Overlapping bindings or including upstream dam releases in `inflows.csv` causes `check` to fail or double-counts water.

</div>

### Forcing units and warm-up window

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **Units**: Daily precipitation in `mm/day` (converted internally to `cm/day`), PET in `cm/day`, and temperature in `°C`.
- **Warm-up vs. operation**: HydroCNHS `StartDate`–`EndDate` can start earlier than `start_date`–`end_date` to spin up soil and groundwater; reservoir `initial_storage_m3` always starts on `start_date`.

## GWLF states and calibration boundary

- GWLF initializes `S0`, `U0`, `SnowS`, and `B0`/`BF0` from your HydroCNHS model file (daily `BF0` is a discharge depth, not an hourly deep-storage volume; see [Hourly GWLF](HOURLY_GWLF.md)).
- HydroReOpLLM runs your calibrated HydroCNHS parameters as supplied; watershed calibration and bias correction stay upstream of coupling.

## HydroCNHS ModelBuilder, Dam nodes, and routing

During daily runs, HydroReOpLLM registers `LLMReservoirAgent` (`examples/llm_reservoir_abm.py`) as a HydroCNHS `DamAPI` node linking `inflow_node` (`-1`) and `reservoir` (`+1`). Outflow (`controlled_release_cms + spill_cms`) routes through `fraction` splits and `unit_hydrograph` lags in upstream-to-downstream order.

## Preparation outputs and mass-balance diagnostics

Run `reservoir-experiment prepare experiment.yaml` to inspect `inflows.csv` before running operators:

| Output artifact | Location | What to check |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | Simulated incremental local inflows (`m³/s`) over the operation window. |
| `hydrology_diagnostics.json`, `hydrology_state.json` | `<output>/` | Subbasin GWLF fluxes, residuals, and final states (when `diagnostics: true` or hourly). |
| `network_balance.csv`, `reach_volume_trace.json` | `<output>/operation/` | Reservoir + channel mass balance (`m³`) across the full run (`system_residual_m3` near `0`). |
