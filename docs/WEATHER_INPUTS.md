# Weather and inflow inputs

The coupled entry expects an already accepted HydroCNHS model and a complete daily
weather table. It does not download weather, delineate a basin, calibrate
parameters or decide whether the hydrological model is scientifically adequate.

## Start from the complete hydrology section

The canonical starter keeps hydrology in one full source file:

```{literalinclude} ../templates/coupled/hydrology.yaml
:language: yaml
```

Open the [complete hydrology template](../templates/coupled/hydrology.yaml) beside
the [top-level experiment template](../templates/coupled/experiment.yaml) while
editing. The experiment references this section with `hydrology: {file:
hydrology.yaml}`. In this manual, `hydrology.model` means the `model` key inside
the expanded hydrology section. It is key-path shorthand, not a function call.
The [HydroCNHS setup chapter](HYDROLOGY_SETUP.md) explains the full file before
this page narrows to weather and binding rules.

## Native hydrology model

`hydrology.model` points to an agent-free HydroCNHS YAML with:

- `WaterSystem.RainfallRunoff` set to `GWLF` or `ABCD`;
- `WaterSystem.Routing` set to `Lohmann`;
- consistent `StartDate`, `EndDate` and `DataLength`; and
- one `RainfallRunoff` definition for every declared outlet.

Reservoir agents belong in the coupled simulation YAML, so the hydrology model
must not contain ABM agents. The accepted HydroCNHS installation is hash checked
before execution.

## Weather table

`hydrology.forcing` points to UTF-8 CSV or gzip-compressed CSV. Required columns are:

| Column | Unit | Rule |
|---|---|---|
| `date` | `YYYY-MM-DD` | Every native model day |
| `subbasin_id` | native outlet ID | Every weather-driven unit |
| `precipitation_mm` | mm/day | Finite and nonnegative |
| `temperature_c` | °C | Finite |
| `pet_cm` | cm/day | Finite and nonnegative |

Rows may include additional columns, but column names must not be duplicated.
Every `(subbasin_id, date)` pair occurs exactly once. `zero_flow_nodes` identifies
native outlets that intentionally receive zero assigned flow instead of weather;
those IDs must be unique declared outlets. At least one outlet must remain
weather-driven.

Preparation runs every native model day, preserving warm-up and routing history.
The coupled top-level `start_date` and `end_date` select the operation window from
that completed hydrology; they must lie within the native period.

## Bind natural flow to operation nodes

`inflow_bindings` in the complete template must name every local-flow node in
the operation network: each reservoir inlet, junction and common outlet. Each
node has exactly one binding. The table below lists the three accepted forms;
replace the template placeholders with IDs from the accepted hydrology model and
physical network.

| Binding | Meaning |
|---|---|
| `{routed: native_outlet}` | Native routed flow from that outlet and its contributing catchments |
| `{runoff: subbasin}` | Direct rainfall-runoff generated for one weather-driven unit |
| `{constant: 0}` | Explicit zero incremental lateral flow; no other constant is accepted |

The loader traces native routing contributors. If two bindings include the same
weather-driven catchment, validation stops because that water would be counted
twice. Unknown sources, routing cycles and routed outlets with no weather-driven
contributor also stop validation. The check report lists weather-driven units that
are valid but unused.

For reservoirs in series, never bind an upstream routed total again as a
downstream local input. Bind only the downstream reach's incremental lateral
runoff. The operation network separately routes the upstream reservoir's
implemented controlled release plus spill.

## Reuse a preparation

To compare another operation method without rerunning hydrology, keep the model,
forcing, full and selected periods, bindings and runtime unchanged. Give the new
simulation its own `run_id` and `output`, then add:

```yaml
hydrology:
  prepared_from: ../runs/basin-operator-v1
```

The loader verifies the preparation manifest and inflow checksum. Changed bytes,
dates, bindings, code or numeric-library versions require a fresh preparation.

Continue with [Build a simulation](BUILD_SIMULATION.md), then use the
[configuration chapter](CONFIGURATION.md) for agents, prompts, and model
profiles. The canonical files remain the source of complete examples; this
weather reference does not redefine them.
