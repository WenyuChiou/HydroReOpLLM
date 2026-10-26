# Time scales and fixed-interval operation

Reservoir decisions, physical implementation and decision information share an
explicit time axis. Existing daily cases keep their input/output formats and
native HydroCNHS execution path. An interval case uses a separate fixed-step
operation host with the same reservoir agent and physical kernel.

## Choose the appropriate path

| Case | Clock | Host and input requirement |
|---|---|---|
| `llm-reservoir-network.v1` / `.v2` | Consecutive `YYYY-MM-DD`, 86400 seconds | Existing native daily HydroCNHS operation and routing |
| `llm-reservoir-network.v3` | Timezone-aware start, fixed positive whole seconds | Supplied interval mean local inflows and routing weights resolved at that step |
| Weather/GWLF preparation | Daily | Existing daily meteorology and hydrological parameter semantics |

The v3 host does **not** turn a daily GWLF model, calibrated daily parameters or
daily unit hydrographs into an hourly hydrological model. Obtain and verify
appropriate interval inputs and routing before using it for a scientific case.
The supplied-data path performs no resampling, forecast generation or download.
Its metadata identifies the engine as `fixed_step_reservoir_network`.

## Define the clock

An interval network uses `outlets`, `start_time` and `dt_seconds`:

```json
{
  "schema_version": "llm-reservoir-network.v3",
  "start_time": "2021-08-30T00:00:00-04:00",
  "dt_seconds": 3600,
  "outlets": ["Outlet"]
}
```

This fragment supplements the usual reservoir and connection settings; see the
complete [offline fixture](../examples/fixed_interval/case.json).
Every reservoir's physical `dt_seconds` must equal the network duration. UTC is
used internally, so the first input timestamp above is `2021-08-30T04:00:00Z`.
Naive interval timestamps, mixed durations, gaps and duplicate records are
rejected. Durations are fixed elapsed seconds, including across daylight saving
changes; local calendar rules belong to a declared case-specific adapter.

Each input mean rate applies to `[timestamp, timestamp + dt_seconds)`. Rates are
in m³/s; reservoir storage and integrated water volumes are in m³. Physical
integration uses `Q × dt_seconds`. Requested controlled release, implemented
controlled release, uncontrolled spill and total outflow remain separate.

`TimeAxis.from_network(network)` exposes `timestamp(step)`, `instant(step)`,
`dt_seconds`, `delta` and the input/output time-column `key`.

## Supply interval inflows and routing

Inline synthetic fixtures use rows with `timestamp` and `local_inflow_cms`.
File-based cases declare `format: interval-node-local-cms.v1` and pin the CSV
SHA256. Its columns are:

```text
timestamp,node,local_inflow_cms
2021-08-30T04:00:00Z,I,3.0
2021-08-30T04:00:00Z,Outlet,0.0
```

Supply every routing node at every interval. Local inflow is incremental runoff:
do not include upstream release/spill again in a downstream local input.
Connection `unit_hydrograph` weights describe **step lags** at this clock. For
example, `[0.0, 1.0]` delays a signal by one configured step. The host verifies
its topological step routing against whole-series convolution and independently
checks reservoir-plus-channel volume. Initial in-transit channel storage is
explicitly zero. Run continuous antecedent intervals to establish routing and
operation history; the host never silently resets state at an evaluation date.
That operation warmup does not initialize an external soil/groundwater/snow
model or establish that routing memory has fully decayed.

## Set the operation window and history

The experiment schema is unchanged. A v3 case accepts `start_time` and
`end_time`; the latter is the **exclusive** end of the selected interval window.
Both must align with the case's time grid. Legacy daily experiments retain
inclusive `start_date` / `end_date` semantics. Do not mix these vocabularies.

Generic configured agents can select a completed-history window:

```yaml
agents:
  fixture:
    reservoir: R
    mode: offline
    release_cms: 2.0
    prompt:
      user: prompt.txt
    history_steps: 7
```

The `$completed_history` prompt placeholder contains the previous seven
**completed step records**, oldest first. Records include observation, requested
action and physical transition. At the first step it is `[]`; no zeros or
observations are fabricated. Only physical feedback commits history, so the
current/future action cannot appear in it. A continuous run retains storage and
history across any scoring boundary. `history_steps` defaults to zero (disabled)
for the generic backend, preserving its existing `$previous_transition`
behavior. This setting does not alter the FE Walter example's accepted prompts
or its separate native formatter. Public agent sections may put `history_steps`
under `customization`.

Simulation information histories use the observation's physical duration for
valid and available times. Custom dynamic information/RAG providers must declare
appropriate availability provenance. Adding evaluation observations to decision
inputs changes an experiment's information assumptions and must be declared.
Knowledge of an interval's complete mean inflow is an explicit retrospective
assumption when that mean was unavailable at its start.

## Backend capabilities

Generic configured actions, rule interfaces and shared physical implementation
can use the interval host. Registered backend extensions must explicitly declare
their supported durations, for example `supported_dt_seconds = (900, 3600)`.
This declares support for the interval observation/feedback contract, not just a
change to a prompt label. Interval `validate_backend` callbacks receive `steps`
and `dt_seconds` instead of the legacy `days` count, along with the usual
physical/settings inputs. Existing FE Walter reference and Hanasaki benchmark
examples remain daily-only and are rejected for interval experiments before a
provider is constructed. Port their calendars, history and scientific rule
semantics explicitly before declaring support.

## Run the model-free example

From the repository root, after installing the package:

```console
reservoir-experiment check examples/fixed_interval/experiment.yaml
reservoir-experiment run examples/fixed_interval/experiment.yaml
reservoir-experiment verify runs/fixed-interval-offline --require-offline
```

The example is a synthetic constant-action fixture, performs no HTTP requests,
and does not represent an LLM result or observed hydrological validation. Use a
new output path/run ID for another execution; existing evidence is never
overwritten. The normal `resume` command can reconstruct an interrupted run in a
new directory only when its saved inputs, implementation and runtime still
match.

Interval CSVs use `timestamp`, and summaries/progress use `steps`,
`completed_reservoir_steps` and `completed_network_steps`. `dt_seconds` and
`time_axis` describe their duration and interval convention. Traces retain full
timestamps and unique decision identities. Independent verification derives the
clock from the saved source configuration and checks timestamps, volumes and
routing rather than trusting the reported duration. A verification PASS is an
engineering result; it is not proof of operating-rule compliance or improved
streamflow skill.
