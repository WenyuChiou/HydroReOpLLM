# Daily and hourly simulation from YAML

The coupled YAML entry point can select daily or hourly hydrology. Output
aggregation is a separate setting; monthly is an output resolution, not a
rainfall–runoff calculation step.

```yaml
time:
  simulation_step: hourly
  output_step: monthly
```

Both keys are required when `time` is present. Calculation supports `daily` and
`hourly`; output supports `hourly`, `daily`, and `monthly`, and cannot be finer
than the calculation. Existing configurations without this section retain their
previous behavior. The section also works on experiments using saved inflows.

## Matching inputs and models

The selector does not resample climate, reinterpret a saved hydrograph, or
convert calibrated parameter sets into validated parameters at another scale.
Select the matching model and forcing resources alongside the time setting.

| Layer | Daily coupled run | Hourly coupled run |
| --- | --- | --- |
| Hydrology engine | Accepted native GWLF, or existing daily ABCD workflow | Experimental GWLF-derived hourly kernel |
| Forcing clock | One complete row per day and subbasin | One complete row per hour and catchment |
| Physical network | Existing daily network v1/v2 | Explicit interval network v3 |
| Duration | 86,400 seconds | 3,600 seconds |
| Operation bounds | `start_date` / inclusive `end_date` | UTC `start_time` / exclusive `end_time` |
| Routing | Existing native daily preparation and network routing | Explicit hourly catchment UH and network UH |

Hourly hydrology settings:

```yaml
hydrology:
  engine: gwlf_hourly
  forcing_step: hourly
  model: hourly_hydrology.yaml
  forcing: hourly_forcing.csv
  inflow_bindings:
    I: {routed: basin}
    Outlet: {constant: 0}
```

The hourly model uses `schema_version: hourly-gwlf-model.v1`, an explicit UTC
`start_time`, `dt_seconds: 3600`, a positive `steps` count and a `catchments`
mapping. Each catchment declares its nine GWLF parameters, initial stores
(including deep groundwater `B0`), and `routing` with `dt_seconds: 3600` and
normalized `unit_hydrograph` weights. These weights represent hourly intervals;
the driver never renames daily UH bins or normalizes an invalid UH silently.
The default 24-hour event dry gap is an experimental assumption, not a
calibrated event definition.

Required hourly forcing columns are:

```text
timestamp,subbasin_id,precipitation_mm,temperature_c,pet_cm,seasonal_temperature_c
```

Precipitation and PET are accumulated depths in each hour; precipitation is
converted from mm to cm once. Temperature is the interval mean. The seasonal
temperature input is supplied explicitly, rather than estimated from a short
event window. Missing, duplicate, off-grid or unknown samples fail before
hydrology or an operation agent is executed. Every hourly catchment must have
complete forcing. Local bindings are incremental; a catchment cannot enter the
operation network twice.

For daily runs, optional `engine: gwlf_daily` and `forcing_step: daily` make the
intended driver explicit. `gwlf_daily` requires a GWLF native model. Without an
explicit engine, the existing daily GWLF/ABCD configuration remains supported.
Daily forcing continues to use `date,subbasin_id,precipitation_mm,temperature_c,pet_cm`.

## Derived outputs and verification

Native CSVs, decision traces and water-balance evidence are always retained at
the simulation step. A coarser output request adds:

- `network_flows_monthly.csv` and `reservoir_trajectory_monthly.csv`, or
- the corresponding `_daily.csv` files for an hourly-to-daily request.

Flow means are weighted by covered seconds, and volumes are calculated by
integrating m³/s over those seconds. Storage is reported as period-start and
period-end state, not summed or labeled as a mean. If an input interval crosses
a calendar boundary, flow uses its interval-mean rate and storage endpoints use
an explicitly linear bookkeeping interpolation. The latter is not a new
subinterval reservoir simulation.

Periods use the UTC calendar, including leap years and actual month lengths.
`coverage_start`, `coverage_end`, `covered_seconds`, and `complete_period`
distinguish full months from partial event windows. No missing hours or days
are filled. `verify` checks the derived file hashes and recomputes their
contents from the preserved native CSVs.

Hourly preparation retains full-period GWLF diagnostics, final restart states,
and catchment routing volume balances as JSON. Water remaining in the UH tail
is retained as final channel storage. Source and generated-file hashes bind
reusable preparations; changing inputs, runtime or time bounds requires a new
preparation.

## Offline examples

From the repository root, using the installed environment or `PYTHONPATH=src`:

```console
python run_experiment.py check examples/time_scales/daily.yaml
python run_experiment.py run examples/time_scales/daily.yaml
python run_experiment.py verify runs/time-scale-daily/operation --require-offline
python run_experiment.py check examples/time_scales/hourly.yaml
python run_experiment.py prepare examples/time_scales/hourly.yaml
python run_experiment.py run examples/time_scales/hourly.yaml
python run_experiment.py verify runs/time-scale-hourly/operation --require-offline
```

Both examples are synthetic engineering fixtures with `max_calls: 0`. The
hourly example calculates 120 hours of hydrology and operates for 96 hours after
24 hours of hydrological initialization, crossing leap February into March.
Reservoir initial storage remains a separate explicit case value; this short
fixture does not establish groundwater equilibration or operation warmup. Existing output
directories are never overwritten; choose a new YAML output/run identity for a
fresh execution.

This integration does not establish empirical hourly hydrological skill.
Independent hourly calibration/validation, routing checks and initial-state
sensitivity are still required before evaluating LLM improvement. The legacy
`hydrocnhs.Model.run` itself remains daily; hourly YAML uses the separate driver.
