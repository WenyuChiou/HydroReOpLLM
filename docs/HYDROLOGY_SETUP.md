# Inflows and HydroCNHS setup

<div class="hero-band" markdown="1">

HydroReOpLLM builds on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) so you can drive reservoirs from **prepared inflow CSVs** or a **calibrated HydroCNHS watershed model** (`GWLF`/`ABCD` + Lohmann routing).

</div>

## Two inflow paths

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Path A: Prepared inflow CSV

- Best when you already have subbasin local inflows (`examples/fe_walter/`, `examples/multi_reservoir/`).
- Reads `inflows.csv` directly and routes reservoir releases downstream.

</div>
<div class="panel-card" markdown="1">

### Path B: Coupled HydroCNHS watershed model

- Best when simulating rainfall–runoff (`GWLF`/`ABCD`) and Lohmann routing from weather forcing.
- `prepare` runs the catchment model and writes `inflows.csv` before `run` operates reservoirs.

</div>
</div>

### Path A format: `inflows.csv`

Provide one non-negative **incremental local flow** (`m³/s`) per day for every reservoir inlet, junction, and outlet—excluding water routed from upstream dams:

```csv
date,node,local_inflow_cms
2025-01-01,feitsui_local,11.152680
2025-01-01,zhitan_local,17.518809
2025-01-01,xindian_outlet,0.000000
```

## Coupled HydroCNHS model and forcing

### `hydrology.yaml` and inflow bindings

Connect an agent-free HydroCNHS model (`ABM: null`) to every non-reservoir node in `reservoirs.yaml`:

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
| `zero_flow_nodes` | No | Native outlets fixed at `0.0 m³/s` without weather entries. |
| `inflow_bindings` | Yes | 1-to-1 map for every inlet, junction, and outlet (`runoff`, `routed`, or `constant: 0`). |
| `engine` | No | Default `gwlf_daily`; set `gwlf_hourly` with `forcing_step: hourly` for hourly GWLF. |
| `diagnostics` | No | When `true`, exports per-subbasin GWLF state and balance diagnostics during `prepare`. |
| `prepared_from` | No | Path to an earlier completed `prepare` folder to reuse matching inflows. |

<div class="callout callout-warn" markdown="1">

**Never double-count upstream catchments.** `routed:` already sums every subbasin upstream of that outlet, whereas `runoff:` takes one subbasin. Overlapping bindings or including upstream dam releases in `inflows.csv` causes `check` to fail or counts water twice.

</div>

### Forcing units and warm-up window

```csv
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,12.5,4.2,0.18
2020-02-27,basin_b,8.0,2.5,0.15
```

- **Units**: Daily precipitation in `mm/day` (converted internally to `cm/day`), PET in `cm/day`, and temperature in `°C`.
- **Warm-up vs. operation**: HydroCNHS `StartDate`–`EndDate` may begin earlier than `start_date`–`end_date` to spin up soil and groundwater; reservoir `initial_storage_m3` always starts on `start_date`.

## GWLF initial states and calibration boundary

- GWLF initializes `S0`, `U0`, `SnowS`, and `B0`/`BF0` from your HydroCNHS model file (daily `BF0` is a discharge depth, not an hourly deep-storage volume; see [Hourly GWLF (experimental)](HOURLY_GWLF.md)).
- HydroReOpLLM runs your calibrated HydroCNHS parameters as supplied; catchment calibration and bias correction stay upstream of coupling.

## How reservoirs connect to river routing

At each timestep, every controlled dam receives its local incremental inflow plus lagged outflows arriving from upstream reaches. After enforcing storage and release limits, the water-balance engine routes `controlled_release_cms + spill_cms` downstream through each reach's `fraction` split and `unit_hydrograph` travel-time weights in upstream-to-downstream order.

## Preparation outputs and water-balance checks

Run `reservoir-experiment prepare experiment.yaml` to inspect watershed inflows before running operators:

| Output artifact | Location | What to check |
| --- | --- | --- |
| `inflows.csv` | `<output>/` | Simulated incremental local inflows (`m³/s`) over the operation window. |
| `hydrology_diagnostics.json`, `hydrology_state.json` | `<output>/` | Subbasin GWLF fluxes, residuals, and final states (when `diagnostics: true` or hourly). |
| `network_balance.csv`, `reach_volume_trace.json` | `<output>/operation/` | Reservoir + channel mass balance (`m³`) across the full run (`system_residual_m3` near `0`). |
