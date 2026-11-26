# Hourly GWLF (experimental)

<div class="hero-band" markdown="1">

`run_GWLF_hourly` computes sub-daily runoff directly from interval climate forcing without disaggregating daily flows. It is an experimental engineering formulation; mass-balance closure does **not** establish calibrated hourly skill.

</div>

## Standalone synthetic example

```python
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly

parameters = {
    "CN2": 70, "IS": 0.2, "Res": 0.02, "Sep": 0.01,
    "Alpha": 0.12, "Beta": 0.2, "Ur": 8, "Kc": 0.8, "Df": 0.12,
}
initial = {"Area": 1000, "S0": 10, "U0": 4, "SnowS": 0.2, "B0": 1}
diagnostics = []
flow_cms, state = run_GWLF_hourly(
    parameters,
    initial,
    temp=[5.0] * 48,          # interval-mean degrees C
    prec=[0.01] * 48,         # accumulated cm in each interval
    pet=[0.003] * 48,         # accumulated cm in each interval
    monthly_Tavg=[5.0] * 48,  # aligned seasonal mean, degrees C
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

- **Accepted steps**: `dt_seconds` must be `3600`, `1800`, or `900`.
- **Units**: `Area` in `ha`, initial storages (`S0`, `U0`, `SnowS`, `B0`) and `Ur` in `cm`, `prec`/`pet` in accumulated `cm` per interval, and returned `flow_cms` in `m³/s`.

## Coupled hourly workflow and schema

| Layer | Hourly requirement |
| --- | --- |
| `experiment.yaml` | `schema_version: hydroops-coupled-simulation.v2`, UTC `start_time` & exclusive `end_time`, `time: {simulation_step: hourly, output_step: hourly\|daily\|monthly}`. |
| `hydrology.yaml` | `engine: gwlf_hourly`, `forcing_step: hourly`, continuous UTC forcing (`...Z`), `inflow_bindings` covering every non-dam node. |
| `reservoirs.yaml` | `network.schema_version: llm-reservoir-network.v3`, `dt_seconds: 3600`, aligned `start_time`, hourly `unit_hydrograph` lags. |
| `agents` extensions | Custom extensions must declare `supported_dt_seconds` containing `3600`. |

`prepare` writes `hydrology_diagnostics.json`, `hydrology_state.json`, and `hydrology_routing.json` alongside `inflows.csv`.

## State continuity, diagnostics, and validation

<div class="callout callout-warn" markdown="1">

**State transfer rules.** Pass the returned `state` only to the next consecutive interval block with identical parameters and `dt_seconds`. Never skip, overlap, or backfill timestamps, and never substitute a daily `BF0` discharge depth for an hourly deep-storage state.

</div>

Inspect `diagnostics` (or `hydrology_diagnostics.json`) for storage/flux terms and validate spin-up, runoff, and hourly routing against observed hydrographs before interpreting operational results. See [Time scales & units](TIME_SCALES.md) and [Inflows & HydroCNHS](HYDROLOGY_SETUP.md).
