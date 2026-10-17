# Inputs and outputs

HydroOpsLLM adds reservoir decision configuration and durable records around
HydroCNHS. Use the [native input/output reference](https://cylin928.github.io/HydroCNHS/files/4_input_output.html#inputs)
for unchanged hydrology APIs. This page specifies the added interface and its differences.

## What changes at the boundary?

| Boundary | Native HydroCNHS | HydroOpsLLM experiment entry |
|---|---|---|
| Weather | Dictionaries of daily temperature, precipitation and optional PET | CSV or CSV.gz, one row per subbasin/day; PET is required. |
| Precipitation unit | cm/day | Stored `precipitation_mm` is mm/day; preparation divides by 10. |
| Temperature/PET | °C and cm/day | Same units in `temperature_c` and `pet_cm`. |
| Model configuration | Native model YAML and ABM settings | Retain an agent-free native model; add experiment YAML and physical case. |
| Agent registration | User ABM classes and native API links | Select reservoir ID, rule/LLM method and registered extensions in YAML; the framework wires the Dam agent. |
| Spatial mapping | Native outlets and routing links | Explicit native-flow → local inlet → reservoir → downstream graph mapping. Information location remains separate. |
| Time | Native simulation dates | Full hydrology dates plus an operation window inside them; reservoir initial storage is separate. |
| Decision result | User-defined ABM behavior | A normalized requested controlled release in m³/s; physics computes spill and implemented flow. |
| Results | In-memory data collector, including routed flow | Persisted decision/provider/audit/physics records and exported trajectories, flows and balances. |
| Recovery | Application-defined | Source hashes, durable attempts and verified committed-prefix recovery. |

The current weather entry supports GWLF/ABCD with Lohmann routing. It rejects
native ABM agents during hydrology preparation to avoid applying reservoir control
twice. The bundled core uses `RainfallRunoff` in its accepted configuration;
older upstream documentation can show `LSM`. Use the bundled model/schema rather
than copying historical key names. No native hydrology equation is replaced.

## Experiment inputs

| Input | Required content | Consumer |
|---|---|---|
| Experiment YAML | Version, run/output, operation dates, hydrology, case and agents; selected catalogs | `configuration.py`, `coupled.py` |
| Native model YAML | Consistent dates, weather-driven outlet IDs, accepted runoff/routing parameters, no ABM | `weather.load_weather()` |
| Forcing CSV(.gz) | `date,subbasin_id,precipitation_mm,temperature_c,pet_cm` | `weather.simulate_weather()` |
| Physical case YAML/JSON | Reservoir capacity, dead/initial storage, release limits, timestep and directed network | `network.py`, `physics.py` |
| Rule module and parameters | Registered rule ID and its own parameter mapping | `rule_based.py` and the selected extension |
| LLM profile and prompts | Provider/model, explicitly selected generation and retry settings; user-supplied messages | `configured_backend.py`, `providers.py` |
| Optional information/context | Typed timed sources, fixed variables or retrieval callbacks and provenance | `information.py`, `context.py` |
| Auditors | Declared check IDs, types, versions and parameters | `auditor.py` and selected plugins |

Every weather-driven `(subbasin_id, date)` pair must appear exactly once.
Temperature must be finite; precipitation and PET must also be nonnegative.
Additional weather columns are retained inputs but are not automatically visible
to an agent. Duplicate column names, missing dates or unknown subbasin IDs stop validation.
Units are defined by these column names; the loader cannot detect mislabeled measurements.

Each operation inlet/junction/outlet has exactly one `inflow_bindings` entry:
`runoff` selects local subbasin runoff, `routed` selects a native routed outlet,
and `constant: 0` declares no added lateral inflow. Nonzero constant boundaries
are not supported. Overlapping source catchments are rejected to prevent double counting.

## What an agent receives

`ReservoirObservation` is the shared detached input for rules and LLM backends:

| Field | Meaning |
|---|---|
| `timestep`, `timestamp` | Zero-based step and decision-time clock. |
| `inflow_cms` | Current routed inlet flow, m³/s. |
| `release_upper_bound_cms` | Feasible controlled-release ceiling, not an operation target. |
| `state` | Beginning storage/capacity/dead storage in m³, release limits in m³/s and timestep seconds. |
| `context` | Reservoir ID and explicitly selected supplementary information. |
| `schema_version` | `reservoir-observation.v1`. |

An information profile selects what the agent may see. Observations must be valid
and published by decision time. Forecasts may concern future times but must already
be issued and available. Other reservoirs' state/release and routed flow use
previously committed values. Missing optional data is explicit `MISSING`, not zero.

Generic prompts explicitly place `$observation`, `$previous_transition`,
`$information`, `$knowledge` or custom variables. No common system prompt is
injected. A custom callback receives `DecisionContext` and returns `ContextValue`;
it cannot mutate storage or add physical inflow.

## What a decision returns

The generic normalized action is:

```json
{"schema_version": "reservoir-action.v1", "release_cms": 5.0}
```

Here `5.0` is an illustrative requested mean controlled release in m³/s, not a
suggested rule. `parse_action()` rejects additional fields, negative/nonfinite
flow and coercive values. Reasoning and provider-specific fields remain in raw
records or the selected response parser's metadata.

F.E. Walter intentionally has a different **raw** contract: its native response
uses `release_cfs` plus reasoning and target/direction fields. The case parser
validates that schema, converts cfs to m³/s and clips to the case release bounds.
The confirmed knowledge variant adds `operating_mode` and `rules_applied` (eight raw fields).
It uses `dkp_no_missing_inputs: true` and omits `missing_inputs`. Older saved diagnostics
used a nine-field variant; see the [case results](../examples/fe_walter/coupled/README.md#verified-2016-results).
Common physics then applies available water and computes spill.
Always distinguish:

```text
raw LLM release → normalized requested release → implemented controlled release
                                                     + spill → routed total outflow
```

FE history keeps at most two committed entries, recording the requested action
and implemented total outflow after
physical commit. Raw proposed release can differ from both. Pool elevation is a
case-derived value from storage and a pinned elevation–storage curve; generic
reservoir storage is not automatically an elevation measurement.

## Files written by the workflow

The chosen output contains preparation files and an `operation` directory.
File names below are relative to those two locations.

| Stage/file | Content and interpretation |
|---|---|
| Preparation: `inflows.csv` | `date,node,local_inflow_cms`; incremental boundaries in m³/s. |
| Preparation: `case.json`, `experiment.yaml` | Generated physical case and operation plan. Do not edit them independently of the source configuration. |
| Preparation: `hydrology.json`, `preparation.json` | Periods, bindings, source/generated hashes and preparation provenance. |
| Operation: `summary.json`, `experiment.json` | Completion/accounting summary and resolved experiment provenance. |
| `decisions.jsonl` | Observations, normalized actions and their provenance links. |
| `provider_attempts.jsonl`, `raw/` | Actual prompts, requests/replies, attempt/model/error metadata and saved artifacts. Fields depend on the selected provider/backend; secrets are redacted. |
| `audit.jsonl` | Diagnostic PASS/WARN/FAIL/UNKNOWN results. They do not replace the model decision. |
| `physics.jsonl`, `reservoir_trajectory.csv` | Requested/implemented controlled release, spill, beginning/ending storage and balance. |
| `network_flows.csv` | `date,node,local_inflow_cms,routed_flow_cms`; routed flow includes relevant upstream outflows. |
| `network_balance.csv`, `reach_volume_trace.json` | System storage/flow accounting, including water remaining in routing reaches. |
| Optional `outcome_audit.jsonl` | Configured control-point checks after routing. |

`verify` checks integrity, causal links and water accounting. It does not certify
hydrological calibration or operating quality. Seasonal target failure is an audit
outcome, not a provider-format failure. Invalid replies/timeouts can use bounded
retries; authentication/configuration and evidence-write failures stop.

Resume verifies the committed prefix into a new output directory, skips committed
decisions and reuses captured replies where available. External network delivery
cannot be guaranteed exactly once across every crash boundary. Dynamic numeric
information extensions currently lack a resume contract; resumable studies use
pinned CSV/static information. See [resources and interruptions](RUNNING.md).

## Continue

[F.E. Walter file-by-file tutorial](../tutorials/fe_walter.md) ·
[Python API documentation](API_REFERENCE.md) · [Result interpretation](RESULTS_GUIDE.md)
