# Time scales and units

<div class="hero-band" markdown="1">

The public template and F.E. Walter studies run on a **daily** (`dt_seconds: 86400`) clock. Coupled or prepared studies also support explicit sub-daily intervals (`llm-reservoir-network.v3`) when forcing, runoff, routing, and reservoir timesteps agree.

</div>

## Physical and forcing unit conventions

| Quantity | Native unit | Simulation rule |
| --- | --- | --- |
| Storage, capacity, dead storage | `m3` | Volume step change is `(inflow - controlled_release - spill) * dt_seconds`. |
| Inflow, release, spill, routed flow | Interval-mean `m3/s` | Applied uniformly across `dt_seconds`; site units (e.g., `cfs`) convert at the boundary. |
| `dt_seconds` | Seconds (`s`) | Must match across reservoir `physical.dt_seconds`, network clock, and hydrology engine. |
| `unit_hydrograph`, `fraction` | Dimensionless | Weights `>= 0` summing to `1.0` per reach (`[1.0]` = no lag). |
| Daily precipitation, PET | `mm/day`, `cm/day` | `precipitation_mm` converts internally to `cm/day` for GWLF/ABCD. |
| Sub-daily precipitation, PET | Depth per interval (`cm`) | Supply depth accumulated over that exact interval, never a daily total. |
| Temperature | Interval mean (`°C`) | Signed finite number; negative values allowed for snow. |

## Daily and sub-daily time configuration

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Legacy daily (`v1` / `v2` networks)

- Uses quoted inclusive `YYYY-MM-DD` `start_date` and `end_date`.
- `inflows.csv` uses column `date` (`daily-node-local-cms.v1`).
- Default `dt_seconds` is `86400.0`.

</div>
<div class="panel-card" markdown="1">

### Explicit fixed interval (`v3` networks)

- Uses UTC `start_time` and exclusive `end_time` (`...Z`).
- `inflows.csv` uses column `timestamp` (`interval-node-local-cms.v1`).
- Coupled hourly HydroCNHS supports `3600` s (`1800` / `900` s in `run_GWLF_hourly` & `v3` routing).

</div>
</div>

## Aggregation and cadence rules

```yaml
time:
  simulation_step: hourly   # daily | hourly (must match network dt_seconds)
  output_step: daily        # hourly | daily | monthly (cannot be finer than simulation_step)
```

- `output_step` exports `network_flows_<output_step>.csv` and `reservoir_trajectory_<output_step>.csv` alongside the preserved native CSVs.
- Never relabel daily forcing or daily unit hydrographs as hourly; finer timesteps require interval-aligned forcing, routing weights, and `supported_dt_seconds`. Continue with [Experimental hourly GWLF](HOURLY_GWLF.md).
