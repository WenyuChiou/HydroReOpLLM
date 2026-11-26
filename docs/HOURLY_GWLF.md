# Experimental hourly GWLF-derived runoff

<div class="hero-band" markdown="1">

`run_GWLF_hourly` computes sub-daily catchment runoff directly from interval meteorological forcing without disaggregating saved daily hydrographs. It is an experimental engineering formulation; numerical execution and mass-balance closure do **not** imply calibrated sub-daily runoff skill.

</div>

## Standalone synthetic example

Run the kernel directly from an installed checkout without a model server or reservoir network:

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
- **Units**: `Area` is hectares (`ha`), storage states (`S0`, `U0`, `SnowS`, `B0`) and `Ur` are `cm`, `prec`/`pet` are accumulated `cm` per interval, and returned `flow_cms` is interval-mean `m3/s`.

## Coupled hourly workflow and schema

To connect hourly GWLF runoff to reservoir operations (`src/llm_reservoir_agent/coupled.py` & `interval_weather.py`):

| Layer | Hourly requirement |
| --- | --- |
| `experiment.yaml` | `schema_version: hydroops-coupled-simulation.v2`, canonical UTC `start_time` & exclusive `end_time`, `time: {simulation_step: hourly, output_step: hourly\|daily\|monthly}`. |
| `hydrology.yaml` | `engine: gwlf_hourly`, `forcing_step: hourly`, continuous hourly forcing with UTC timestamps (`...Z`), `inflow_bindings` mapping every `routing_node`. |
| `reservoirs.yaml` | `network.schema_version: llm-reservoir-network.v3`, `dt_seconds: 3600`, `start_time` aligned with `experiment.yaml`, hourly `unit_hydrograph` bins. |
| `agents` extensions | Any extension used in an hourly run must declare `supported_dt_seconds` containing `3600`. |

`prepare` exports `hydrology_diagnostics.json`, `hydrology_state.json`, and `hydrology_routing.json` alongside `inflows.csv` (`timestamp,node,local_inflow_cms`).

## State continuity, diagnostics, and validation

<div class="callout callout-warn" markdown="1">

**State transfer rules.** The returned `state` carries soil, shallow groundwater, deep groundwater, snow, antecedent moisture, and event memory. Pass it only to the next consecutive interval block with identical parameters and `dt_seconds`. Never skip, overlap, reorder, or silently backfill forcing timestamps, and never substitute a daily `BF0` discharge depth for an hourly deep-storage state.

</div>

Inspect `diagnostics` (or `hydrology_diagnostics.json`) for interval storage/flux terms and water-balance residuals at your study's scale. Validate initial spin-up, event-memory parameters, runoff, and hourly unit hydrographs against independent observations before interpreting operational comparisons. See [Time scales and units](TIME_SCALES.md) and [Native HydroCNHS hydrology](HYDROLOGY_SETUP.md).
