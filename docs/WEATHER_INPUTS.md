# Weather and inflow inputs

The coupled entry expects an already accepted HydroCNHS model and a complete daily
weather table. It does not download weather, delineate a basin, calibrate
parameters or decide whether the hydrological model is scientifically adequate.

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

`hydrology.inflow_bindings` must name every local-flow node in the operation
network: each reservoir inlet, junction and common outlet. Each node has exactly
one binding:

```yaml
hydrology:
  model: accepted_hydrology.yaml
  forcing: complete_weather.csv.gz
  zero_flow_nodes: [native_placeholder]
  inflow_bindings:
    Reservoir1_inlet: {routed: native_outlet}
    Reservoir2_inlet: {runoff: lateral_subbasin}
    Downstream: {constant: 0}
```

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

## A generic configured LLM simulation

This abbreviated example uses the reusable configured strategy. The physical
case, prompt and model must be appropriate for the user's basin.

```yaml
schema_version: hydroops-coupled-simulation.v1
case: reservoirs.json
run_id: basin-operator-v1
output: ../runs/basin-operator-v1
start_date: '2020-01-01'
end_date: '2020-12-31'
max_calls: null

hydrology:
  model: accepted_hydrology.yaml
  forcing: complete_weather.csv.gz
  zero_flow_nodes: []
  inflow_bindings:
    R1_inlet: {routed: basin_outlet}
    Downstream: {constant: 0}

models:
  local_model:
    provider: ollama
    model: your-model
    base_url: http://localhost:11434
    max_attempts: 2
    retry_delay_seconds: 2

agents:
  operator:
    reservoir: R1
    strategy: configured
    mode: llm
    model: local_model
    prompt: operator.txt
    prompt_version: '1'
    knowledge: {}
    context: {}
    response_schema: reservoir-action.v1
    auditors: [release_limits]

auditors:
  release_limits: {type: release_bounds, version: '1'}
```

`max_calls: null` removes the total-call cap. `max_attempts: 2` remains a separate
per-decision bound, and a retry uses unchanged decision inputs without advancing
storage. Network access still requires `run --allow-network`.

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

Continue with [Build a weather-to-operation simulation](BUILD_SIMULATION.md).
