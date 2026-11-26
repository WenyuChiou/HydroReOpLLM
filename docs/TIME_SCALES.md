# Time scales and units

<div class="hero-band" markdown="1">

The public template and F.E. Walter cases run on the maintained **daily** (`dt_seconds: 86400`) clock. Coupled or prepared-inflow studies can also run on explicit fixed sub-daily intervals (`llm-reservoir-network.v3`) when forcing, runoff, routing, and reservoir clocks agree (`src/llm_reservoir_agent/time_axis.py`, `time_config.py`).

</div>

## Physical and forcing unit conventions

| Quantity | Native / Expected unit | Kernel & conversion rules |
| --- | --- | --- |
| Reservoir storage, capacity, dead storage | `m3` | Volume change over one step is `(inflow - controlled_release - spill) * dt_seconds`. |
| Inflow, release, spill, routed flow | Interval-mean `m3/s` | Applied uniformly across `dt_seconds`; site units (e.g., `cfs`) convert at the prompt/parser boundary. |
| `dt_seconds` | Seconds (`s`) | Must match across `network.reservoirs.*.physical.dt_seconds`, `TimeAxis`, and hydrology engine. |
| `unit_hydrograph` & `fraction` | Dimensionless | Weights `>= 0` summing to `1.0` per edge; index `0` is same step, index `1` is `+1` step. |
| Daily precipitation & PET | Accumulated depth (`mm/day` & `cm/day`) | `weather.py` divides `precipitation_mm` by `10` to match HydroCNHS's `cm/day` input. |
| Sub-daily precipitation & PET | Accumulated depth per interval | Supply the depth accumulated over that exact interval (`dt_seconds`), never a daily total or rate. |
| Temperature | Interval mean (`°C`) | Signed finite float; negative temperatures allowed. |

## Daily and sub-daily time configuration

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Legacy daily (`v1` / `v2` networks)

- Uses `start_date` and `end_date` as quoted inclusive `YYYY-MM-DD` strings.
- `inflows.csv` uses column `date` and format `daily-node-local-cms.v1`.
- Default `dt_seconds` is `86400.0`.

</div>
<div class="panel-card" markdown="1">

### Explicit fixed interval (`v3` networks)

- Uses canonical UTC `start_time` and exclusive `end_time` (`...Z`).
- `inflows.csv` uses column `timestamp` and format `interval-node-local-cms.v1`.
- Coupled hourly HydroCNHS supports `3600` s (`1800` / `900` s supported by standalone `run_GWLF_hourly` and `v3` interval routing).

</div>
</div>

## Aggregation and cadence rules

Declare `time:` in `experiment.yaml` to export aggregated summary tables alongside the preserved native step CSVs (`src/llm_reservoir_agent/time_config.py` & `temporal_output.py`):

```yaml
time:
  simulation_step: hourly   # daily | hourly (must match network dt_seconds)
  output_step: daily        # hourly | daily | monthly (cannot be finer than simulation_step)
```

- **Aggregation invariant**: `output_step` derives `network_flows_<output_step>.csv` and `reservoir_trajectory_<output_step>.csv` after execution without altering native `reservoir_trajectory.csv` or `network_balance.csv`.
- **No silent resampling**: Never label daily forcing or daily unit-hydrograph bins as hourly; finer simulation steps require interval-aligned forcing, runoff, routing weights, and cadence-aware rules (`supported_dt_seconds`). Continue with [Experimental hourly GWLF](HOURLY_GWLF.md).
