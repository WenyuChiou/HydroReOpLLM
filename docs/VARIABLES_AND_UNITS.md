# Variables, phases and units

The core uses SI units. A case adapter can use feet or cfs in its external
prompt, but must convert at the interface and retain the original evidence.
Renaming `daily` to `hourly` does not change the physical meaning of a flow rate.
The integration duration changes the volume represented by that rate.

| Quantity or field | Meaning and unit | Ownership/check |
|---|---|---|
| `date` / `timestamp` | Operating interval start; Daily `YYYY-MM-DD`, timezone-aware timestamps for subdaily clocks | One continuous common network clock |
| `dt_seconds` | Fixed integration duration, s; Daily = 86,400 | Shared by connected reservoirs and routing kernels |
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

The reservoir balance is `S_end − S_start = (Q_in − Q_controlled − Q_spill) × dt`.
Whole-network balance also includes local external inflow, outlet discharge and
the change in water stored in channels. A nonzero final channel stock is not
lost water. Flush tails only for conservation/routing analysis, without inventing
additional operating decisions or model requests.

Mathematical constants and SI time conversions are explained in `timebase.py`
and `physics.py`. Scientific case assumptions, station identifiers, model names,
seasonal objectives, calibrated parameters and external-unit conversions belong
in configuration or case extensions. The F.E. Walter compatibility extension
retains the original program's conversion precision for reproducibility; do not
quietly substitute another precision into accepted historical trajectories.

[Daily workflow](DAILY_WORKFLOW.md) · [API reference](API_REFERENCE.md)
