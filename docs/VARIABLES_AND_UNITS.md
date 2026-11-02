# Variables, phases and units

The core uses SI units. A case adapter can use feet or cfs in its external
prompt, but must convert at the interface and retain the original evidence.
Renaming `daily` to `hourly` does not change the physical meaning of a flow rate.
The integration duration changes the volume represented by that rate.

| Quantity or field | Meaning and unit | Ownership/check |
|---|---|---|
| `date` / `timestamp` | Operating interval start; network v1/v2 uses `date` as `YYYY-MM-DD`; v3 uses `timestamp` normalized to UTC with `Z` | `TimeAxis.from_network(...)` defines the common network clock |
| `start_date` / `end_date` | Daily operation window with inclusive end date | Network v1/v2 requires 86,400-second steps |
| `start_time` / `end_time` | Interval operation window with exclusive end time | Network v3 requires timezone-aware starts and bounds aligned to its grid |
| `dt_seconds` | Fixed integration duration, s; Daily = 86,400; hourly = 3,600 | v3 accepts positive whole seconds; connected reservoirs and routing kernels must agree |
| `local_inflow_cms` | Interval-mean local inflow at a boundary, m³/s | Excludes upstream water already routed by this network |
| Reservoir `inflow_cms` | Local plus routed upstream inflow arriving this step, m³/s | Computed before that reservoir's decision |
| `storage_start_m3` | Beginning-of-step physical water stock, m³ | Previous committed ending storage |
| `requested_release_cms` | Agent's requested controlled release, m³/s | Retained even if physics limits it |
| `controlled_release_cms` | Implemented controlled release, m³/s | Feasible available-water and outlet bounds |
| `spill_cms` | Capacity overflow, m³/s | Added exactly once after controlled release |
| `total_outflow_cms` | Controlled release plus spill, m³/s | Input to downstream routing |
| `storage_end_m3` | End-of-step reservoir stock, m³ | `S_start + (Q_in - Q_controlled - Q_spill) * dt` |
| Elevation | Water-surface elevation from the case's rating curve | Units and datum belong to the case; no universal target |
| `unit_hydrograph` | Dimensionless routing weights per declared time step | Nonnegative normalized finite weights |
| Routing lag | Index offset in operation steps, not an unlabelled number of days | Kernel duration must match the operation clock |
| Channel storage | Water still travelling in a route, m³ | Included in whole-network conservation and full tails |
| Information availability | Earliest timestamp at which an input is usable | Must be no later than the current decision |
| History | Completed observations/actions/transitions for the same reservoir | Excludes current/future decisions |
| Runtime | Host elapsed seconds, labelled by request/run scope | Not interchangeable with native model timers |
| Token usage | Provider-native counts, retained with raw response | Missing values remain unknown; no fabricated zero |
| Hourly `precipitation_mm` / `pet_cm` | Accumulated precipitation in mm and PET in cm over each hour | Explicit hourly GWLF forcing; precipitation converts from mm to cm once |
| `temperature_c` / `seasonal_temperature_c` | Interval mean temperature and explicitly supplied seasonal temperature, °C | Hourly forcing does not infer seasonal temperature from an event window |
| Aggregated flow / `covered_seconds` | Duration-weighted mean flow in m³/s over the covered duration in s | Daily/monthly summaries integrate native interval means on UTC calendar boundaries |
| Aggregated storage | Period-start and period-end physical water stock, m³ | Split intervals use declared linear endpoint interpolation; storage is not averaged or summed |

The reservoir balance is `S_end − S_start = (Q_in − Q_controlled − Q_spill) × dt`.
Whole-network balance also includes local external inflow, outlet discharge and
the change in water stored in channels. A nonzero final channel stock is not
lost water. Flush tails only for conservation/routing analysis, without inventing
additional operating decisions or model requests.

The clock contract is defined in `time_axis.py`; physical integration is defined
in `physics.py`. Time steps use fixed elapsed seconds across daylight saving
changes. The YAML time selector supports daily/hourly simulation and output no
finer than the simulation step; monthly denotes derived output only. See
[fixed-interval operation](TIME_SCALES.md) and
[YAML time-scale settings](YAML_TIME_SCALES.md) for the supported entry paths.

Scientific case assumptions, station identifiers, model names,
seasonal objectives, calibrated parameters and external-unit conversions belong
in configuration or case extensions. The F.E. Walter compatibility extension
retains the original program's conversion precision for reproducibility; do not
quietly substitute another precision into accepted historical trajectories.

[Daily workflow](DAILY_WORKFLOW.md) · [API reference](API_REFERENCE.md)
