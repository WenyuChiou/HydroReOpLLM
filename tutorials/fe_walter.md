# F.E. Walter: weather, hydrology, and daily operation

This is the maintained tutorial source for the F.E. Walter research example.
It uses the same inflow, initial state, and physical parameters for **Rule-based**,
**LLM without knowledge retrieval**, and **LLM with knowledge retrieval**.

Read in order: [experiment](#1-begin-at-experimentyaml) →
[hydrology](#2-connect-accepted-hydrology) →
[reservoir](#3-map-hydrology-reservoir-and-agent-ids) →
[agents](#4-select-rule-based-or-llm-operation) →
[prompts](#5-read-prompt-and-knowledge-assembly) →
[execution](#6-check-prepare-run-and-verify) →
[results](#7-read-the-current-saved-results).

Each step below links and displays its complete configuration file. Relative
paths start at the file that declares them.
The saved results below were produced **before daily seasonal context was added**.

## 1. Begin at `experiment.yaml`

Run commands from the repository root. The current Rule-based entry is
[`coupled/experiment.yaml`](../examples/fe_walter/coupled/experiment.yaml).
It declares the 2016 dates, physical case, output identity, hydrology, agents,
auditors, and registered rule extension.

```{literalinclude} ../examples/fe_walter/coupled/experiment.yaml
:language: yaml
```

| Entry field | Meaning in this case |
|---|---|
| `schema_version` | Configuration format understood by the loader; not the package version |
| `run_id` | Name saved in the run metadata; choose a new name for a new experiment |
| `case` | Relative path to reservoir and network settings |
| `output` | Parent output folder; daily records go in its `operation/` subfolder |
| `start_date`, `end_date` | First and last operation days, both included |
| `max_calls` | Total provider-attempt ceiling; zero for this Rule-based entry |
| `agents.file`, `auditors.file`, `hydrology.file` | Referenced settings files; these are keys, not functions |
| `extensions` | User modules registered for this case |

The two LLM entries retain the same case and hydrology:

- [`llm_available.yaml`](../examples/fe_walter/coupled/llm_available.yaml)
- [`llm_knowledge.yaml`](../examples/fe_walter/coupled/llm_knowledge.yaml)

Choose a new `run_id` and output path for any new execution. Resource paths are
relative to the file that declares them.

## 2. Connect accepted hydrology

[`hydrology.yaml`](../examples/fe_walter/coupled/hydrology.yaml) points to the
accepted HydroCNHS model and forcing. The weather path uses daily precipitation,
temperature, and precomputed PET for seven contributing subcatchments. GWLF
produces runoff and Lohmann routing moves it to the aggregation outlet. The
binding supplies that routed flow to operation inlet `FEW_INFLOW`.

```{literalinclude} ../examples/fe_walter/coupled/hydrology.yaml
:language: yaml
```

| Hydrology field | Meaning |
|---|---|
| `model` | Accepted native HydroCNHS model, including its full simulation period |
| `forcing` | Complete daily precipitation, mean temperature and PET for that native period |
| `zero_flow_nodes` | Artificial aggregation node assigned zero local runoff |
| `inflow_bindings.FEW_INFLOW.routed` | Native routed outlet supplying the physical inlet |
| `inflow_bindings.Downstream.constant` | Zero additional lateral input; routed reservoir outflow arrives separately |

The accepted native series covers 1989–2025; this experiment selects the 366
days of 2016. Changing the reservoir operator does not recalibrate hydrology.
See [hydrology, parameters, and C&V](../examples/fe_walter/hydrology.md) for data
sources, calibration, validation, and limits.

![Weather, inflow and daily reservoir decisions](../docs/figures/fe-walter-weather-workflow.svg)

**Figure 1.** Precipitation (**P**, mm/day), temperature (**T**, °C) and Hamon
PET (cm/day) supply HydroCNHS. Saved inflow then feeds reservoir operations.
[Editable draw.io source](../docs/figures/fe-walter-weather-workflow.drawio).

## 3. Map hydrology, reservoir, and agent IDs

[`reservoirs.json`](../examples/fe_walter/coupled/reservoirs.json) uses several
identifiers with distinct roles:

This retained case uses the supported network v1 format with one `outlet`.
New configurations should use the [v2 template](../templates/coupled/reservoirs.yaml)
with `outlets`. Changing the version tag alone does not convert the structure.

The physical initial storage is 2,457,848.279729185 m³. It is an integration
assumption, not an observed 1 January 2016 pool measurement. The daily step is
86,400 s; direct reservoir precipitation, evaporation, seepage, and withdrawals
are zero. Downstream `UH=[1.0]` is identity routing, not calibrated travel time.

```{literalinclude} ../examples/fe_walter/coupled/reservoirs.json
:language: json
```

| ID | Role |
|---|---|
| `FEW-D-01`, etc. | HydroCNHS contributing units. |
| `FEW_INFLOW` | Operation-network inlet. |
| `FEWalter` | Reservoir graph key; the agent must use this value as `reservoir_id`. |
| `fe_walter` | Physical case/profile ID. |
| `fe_operator` | Agent instance and state/history owner. |
| `Downstream` | Terminal routing node. |

| JSON field | Role |
|---|---|
| `network.reservoirs.FEWalter.inflow_node` | Binds prepared flow from `FEW_INFLOW`. |
| `physical.initial_storage_m3` | Sets the independent start state for each method. |
| `physical.minimum_release_cms`, `maximum_release_cms` | Bound implemented controlled release. |
| `connections[].unit_hydrograph` | Routes total outflow to the next node. |
| `outlet` | Names the terminal operation-network node. |

The [parameter reference](../docs/PARAMETER_REFERENCE.md) lists every physical
field. The [code reference](../docs/CODE_STRUCTURE.md) traces configuration
loading, agent construction and the daily reservoir calculation.

![Reservoir and agent mapping](../docs/figures/reservoir-agent-mapping.svg)

**Figure 2.** Generic ID mapping between hydrology, a reservoir, and its agent.
The tables above give the F.E. Walter IDs.
[Editable draw.io source](../docs/figures/reservoir-agent-mapping.drawio).

## 4. Select Rule-based or LLM operation

The [Rule-based agent file](../examples/fe_walter/coupled/agents.rule.yaml) selects
the registered Hanasaki case rule. The two LLM agents use the same daily
decision interface.

```{literalinclude} ../examples/fe_walter/coupled/agents.rule.yaml
:language: yaml
```

The [available-information agent file](../examples/fe_walter/coupled/agents.llm_available.yaml)
binds the prompt and model profile.

Here `customization.backend: reference_v3_7` selects the registered case extension
instead of the generic `prompt_file` recipe. The extension builds the native Anik
messages, parses its raw response, and returns the generic release action.
Settings inside `parameters.reference` belong to that extension. The agent ID,
`reservoir_id`, `model_profile` and auditor selections keep their generic roles.

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_available.yaml
:language: yaml
```

The available-information method receives the current date, inflow, starting
water elevation, seasonal instruction, and short completed-decision history.
The [retrieved-knowledge agent file](../examples/fe_walter/coupled/agents.llm_knowledge.yaml)
adds its local knowledge document:

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_knowledge.yaml
:language: yaml
```

Model identity, sampling controls, context size, timeout, and attempt limit live
in [models.yaml](../examples/fe_walter/coupled/models.yaml). They describe
the model execution and do not replace the three method names.

```{literalinclude} ../examples/fe_walter/coupled/models.yaml
:language: yaml
```

## 5. Read prompt and knowledge assembly

The [available-information system file](../examples/fe_walter/prompts/available_information.txt)
defines the task and structured response:

```{literalinclude} ../examples/fe_walter/prompts/available_information.txt
:language: text
```

The retrieved-knowledge method uses the current v2 prompt and the configured
[knowledge file](../examples/fe_walter/knowledge/operating_rules.md). Its
[system file](../examples/fe_walter/prompts/retrieved_knowledge.txt) is:

```{literalinclude} ../examples/fe_walter/prompts/retrieved_knowledge.txt
:language: text
```

The model proposes a release. The case parser converts cfs to m³/s before shared
physics applies water availability and release limits, computes spill and end
storage, and supplies the next day's state. The model does not calculate
catchment inflow or water balance.

Both agent files now reference
[`seasonal_pool_criteria.json`](../examples/fe_walter/seasonal_pool_criteria.json)
through the optional case setting `seasonal_criteria_file`. The backend appends
the simulation date's window, pool bounds and next window start to the user
prompt. It prescribes no release. The original Anik thin wrapper uses the same
addition while retaining its native policy and water calculation.

The [October comparison](../examples/fe_walter/prompt_review.md) separates the
actual saved requests from proposed messages containing this addition.
Removing the setting preserves the earlier prompt assembly.

![Prompt and context workflow](../docs/figures/prompt-context-workflow.svg)

**Figure 3.** Retrieved knowledge adds context to the prompt; system instructions
are optional and user-supplied. The two methods use six- and eight-field raw
response schemas, respectively; both return a release proposal to shared physics.
[Editable draw.io source](../docs/figures/prompt-context-workflow.drawio).

## 6. Check, prepare, run, and verify

`check` resolves configuration without hydrology or provider access. `prepare`
computes the selected hydrology. An LLM run requires the explicit network flag.

Before an LLM run, Ollama must serve the exact installed model tag named in
[`models.yaml`](../examples/fe_walter/coupled/models.yaml) at its configured
URL. See [provider settings](../docs/MODEL_PROVIDERS.md) before enabling
network access. Reading the saved results requires no inference service.

```powershell
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
reservoir-experiment prepare examples/fe_walter/coupled/experiment.yaml
reservoir-experiment run examples/fe_walter/coupled/experiment.yaml
reservoir-experiment verify runs/fe-walter-current-rule/operation
```

For an LLM method, copy its YAML, set a new `run_id` and output, review model,
prompt, and knowledge settings, then use `run ... --allow-network`.

## 7. Read the current saved results

The maintained teaching export combines only saved rows:

- Rule-based: `coupled/outputs/2016/daily.csv`
- both framework LLM methods: `coupled/outputs/gemma4_2016_comparison/daily.csv`

Before combining, the builder verifies 366 unique ordered dates per method,
common inflow within a 1e-10 m³/s CSV-serialization tolerance, the shared initial
state, and units. It does not interpolate or generate model output.

Downloads: [daily.csv](../examples/fe_walter/coupled/outputs/current_tutorial/daily.csv)
and [current tutorial provenance](../examples/fe_walter/coupled/outputs/current_tutorial/provenance.json),
plus the combined figure as [SVG](../examples/fe_walter/coupled/outputs/current_tutorial/reservoir_operations.svg)
or [PDF](../examples/fe_walter/coupled/outputs/current_tutorial/reservoir_operations.pdf).
The standalone [elevation](../examples/fe_walter/coupled/outputs/current_tutorial/daily_water_elevation.pdf)
and [release](../examples/fe_walter/coupled/outputs/current_tutorial/controlled_release_daily.pdf)
exports remain available as secondary downloads.

Open the [main notebook](main.ipynb) for executable saved-data inspection.
[Technical engine evidence and historical audit material](../examples/fe_walter/engine_comparison.md)
remain available without interrupting the main workflow.

![2016 water elevation and water release](../examples/fe_walter/coupled/outputs/current_tutorial/reservoir_operations.png)

**Figure 4.** Saved 2016 operations. (a) End-of-day water elevation (ft NGVD29),
with winter target 1300 ft and summer upper limit 1370 ft. (b–d) Daily water
release (m³/s) for the methods in the panel titles. Release excludes spill;
all panels share operation dates, and the three release panels share a flow scale.
