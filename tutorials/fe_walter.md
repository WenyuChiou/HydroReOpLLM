# F.E. Walter: configure and follow a reservoir decision

Follow one real case from its experiment YAML to the daily LLM decision.
The hydrology and reservoir stay fixed while you change the operation method.
Use the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)
for catchment construction and calibration. Here we explain the added agent settings.

## Step 1. Separate the experiment, physical coupling and agent settings

Run commands from the repository root after [installation](../docs/GETTING_STARTED.md).
The canonical entry is [experiment.yaml](../examples/fe_walter/coupled/experiment.yaml).
It selects the deterministic rule as a first connection check. The maintained
[rule.yaml](../examples/fe_walter/coupled/rule.yaml) is an alternative entry for
the same rule run identity/output; do not execute both into that directory.

```{literalinclude} ../examples/fe_walter/coupled/experiment.yaml
:language: yaml
```

| Scope | Files | Responsibility |
|---|---|---|
| Global experiment | `experiment.yaml`, `rule.yaml`, `llm_available.yaml`, `llm_knowledge.yaml` | Schema, dates, run/output, call gate, section references and explicit extension catalog. |
| Hydrology and physical coupling | `hydrology.yaml`, `reservoirs.json` | Weather/native model, source-to-inlet bindings, physical state and routing graph. |
| Per-agent behavior | `agents.rule.yaml`, `agents.llm_available.yaml`, `agents.llm_knowledge.yaml` | Exact reservoir assignment, rule or LLM and its case-specific settings. |
| Shared model and checks | `models.yaml`, `auditors.yaml` | Named provider profile and diagnostic checks selected by each agent. |

All entries use `hydroops-coupled-simulation.v2`. A section reference such as
`hydrology: {file: hydrology.yaml}` loads that section from its sibling file.
Resource paths are relative to the file that declares them. Keep copies in the
same directory unless you deliberately update those paths. For a new study,
choose a new `run_id` and `output`; source files and prior records remain pinned.

The available-information entry selects its own agent and the shared model:

```{literalinclude} ../examples/fe_walter/coupled/llm_available.yaml
:language: yaml
```

The operation dates are `2016-01-01` through `2016-12-31`: 366 daily steps.
The method entries retain distinct identities and outputs.
`max_calls: 0` forbids provider requests for the rule; the LLM entries use
`max_calls: null`, which removes the total cap while retaining each decision's
bounded attempts.

`configuration.read_configuration()` resolves split files and
`agent_configuration.normalize_agent()` translates public agent fields.
`coupled.load_coupled_settings()` checks the connection without running hydrology
or contacting a model. The short `zero_shot/experiment.yaml` is a separate
supplied-inflow tutorial, not the full-weather entry taught here.

## Step 2. Connect accepted hydrology

Read the actual [hydrology.yaml](../examples/fe_walter/coupled/hydrology.yaml):

```{literalinclude} ../examples/fe_walter/coupled/hydrology.yaml
:language: yaml
```

| File or field | What it supplies |
|---|---|
| [Native model](../data/accepted/fe_walter_hydrology.yaml) | Accepted, agent-free GWLF/Lohmann model; 1989-01-01 to 2025-12-31, 13,514 days. |
| Forcing CSV.gz | Seven units × 13,514 dates = 94,598 rows. Required columns: `date`, `subbasin_id`, `precipitation_mm`, `temperature_c`, `pet_cm`. |
| `zero_flow_nodes` | The computational aggregation outlet receives zero local runoff. It is not an eighth physical subcatchment. |
| `FEW_INFLOW.routed` | Route and sum the seven subcatchment contributions at the native aggregation outlet, then supply that flow to the operation network. |
| `Downstream.constant: 0` | No added lateral inflow below the dam in this teaching network. It does not set total downstream flow to zero. |

The seven IDs are `FEW-D-01`, `FEW-D-02`, `FEW-R-01`, `FEW-R-02`,
`FEW-X-01`, `FEW-X-02` and `FEW-X-03`.
Each forcing `subbasin_id` matches a native model outlet exactly.
Stored precipitation is mm/day; `weather.simulate_weather()` converts it to
cm/day for HydroCNHS. Temperature is °C and PET is already cm/day.
The CSV also retains `tmin_c`, `tmax_c` and `forcing_source` as source metadata.

Weather is based on Daymet, with documented nClimGrid supplements and precomputed
Hamon PET. The [case hydrology record](../examples/fe_walter/hydrology.md#2-data-and-periods) retains
the sources, land/soil assumptions and C&V evidence. Those inputs are already
prepared; this chapter does not repeat their derivation.

`weather.load_weather()` checks complete daily coverage and units.
`validate_bindings()` rejects overlapping catchment contributions.
`prepare_coupled()` runs the complete accepted hydrology, then selects 2016.
Its warm-up is separate from the initial reservoir storage.

## Step 3. Read the reservoir and agent mapping

Open [reservoirs.json](../examples/fe_walter/coupled/reservoirs.json):

```{literalinclude} ../examples/fe_walter/coupled/reservoirs.json
:language: json
```

```text
Seven FEW-D/R/X subcatchments
  → native __AGGREGATION_OUTLET__
  → operation inlet FEW_INFLOW
  → reservoir node FEWalter ← agent fe_operator
  → Downstream
```

| ID | Where it is used |
|---|---|
| `FEW-D-01`, etc. | Hydrology contributors and forcing rows. No LLM agent is assigned directly to these units. |
| `FEW_INFLOW` | Operation-network inlet; receives the prepared natural flow. |
| `FEWalter` | Reservoir graph key. The agent's `reservoir_id` must match this exact key. |
| `fe_walter` | `physical.reservoir_id` and the case profile ID. The case extension checks their agreement. |
| `fe_operator` | Agent instance name. Its state/history belongs to this reservoir. |
| `Downstream` | Routing destination and terminal outlet. |

The two reservoir identifiers have different roles in this existing case.
Changing `FEWalter` to `fe_walter` in the agent would break the graph mapping.

| Physical field | Saved value | Meaning |
|---|---:|---|
| `capacity_m3` | 135,532,852.33895192 | Maximum modeled storage, m³. |
| `dead_storage_m3` | 49.3392742128 | Inactive storage, m³. |
| `initial_storage_m3` | 2,457,848.279729185 | Explicit initial-state assumption, not an observed 2016 pool measurement. |
| `minimum_release_cms` | 1.41584235 | 50 cfs converted to m³/s. |
| `maximum_release_cms` | 283.16847 | 10,000 cfs converted to m³/s. |
| `dt_seconds` | 86,400 | One daily step. |
| `unit_hydrograph` | `[1.0]` | Identity downstream routing; no calibrated travel-time delay. |

The physical case uses `reservoir-physical-case.v1` and the retained network v1
`outlet: Downstream`. New multi-outlet networks use v2 `outlets`.
`data_kind: simulated_local_inflow` describes the boundary source.
`live_readiness.ready: true` is a declared execution gate, not proof of model quality.
Its note records the initial-storage and identity-routing limitations.
`network.validate_network()` checks topology; `physics.apply_transition()` applies
water availability, release limits, spill and storage balance.
The current kernel assumes zero reservoir evaporation and seepage.

## Step 4. Select the method and model

The available-information agent lives in its own file:

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_available.yaml
:language: yaml
```

`reservoir_id: FEWalter` binds `fe_operator` to the graph node.
`type: llm` selects the general operation class; `model_profile: reservoir_model`
selects a profile in [models.yaml](../examples/fe_walter/coupled/models.yaml).
`customization.backend: reference_v3_7` selects the explicitly registered case
extension. Its `parameters.reference` mapping belongs to this example.

```{literalinclude} ../examples/fe_walter/coupled/models.yaml
:language: yaml
```

| `models.reservoir_model` field | Value | What it controls |
|---|---|---|
| `provider` | `ollama` | Provider adapter. |
| `model` | `gemma3:4b` | Explicit model ID, installed separately. |
| `base_url` | `http://localhost:11434` | Ollama service address. |
| `temperature` | `0.7` | Sampling setting; it does not guarantee identical replies. |
| `max_tokens` | `2048` | Maximum generated tokens. |
| `num_ctx` | `16384` | Ollama context-window setting. |
| `think` | `false` | Explicit Ollama thinking option. |
| `keep_alive` | `30m` | Ollama model residency request. |
| `seed` | `null` | No fixed sampling seed is sent. |
| `timeout_seconds` | `120` | Timeout for an individual provider request. |
| `api_key_env` | `null` | No credential environment variable selected for this local profile. |
| `max_attempts` | `2` | At most two attempts, including the first, for one daily decision. |
| `retry_delay_seconds` | `2` | Delay between eligible attempts. |

`configured_backend.validate_model_settings()` validates the profile;
`providers.py` builds its native request and reads its reply. To use a remote
model, configure the appropriate [provider profile](../docs/MODEL_PROVIDERS.md).
Do not carry Ollama-only options into another provider's profile.
The FE reference extension has no cross-model fallback setting; general configured
LLM agents support explicitly ordered fallbacks. Neither path silently switches to a rule.

### Switch to Rule-based

The canonical entry already selects
[agents.rule.yaml](../examples/fe_walter/coupled/agents.rule.yaml):

```{literalinclude} ../examples/fe_walter/coupled/agents.rule.yaml
:language: yaml
```

`type: rule_based` selects the method. `rule: hanasaki` selects this example's
registered module. Its `alpha: 0.85` and `inflow_statistics_file` belong to that
module; `purpose: flood_control` retains metadata, not a different controller.
The statistics must satisfy the module's pre-operation data checks.
The rule uses no model or prompt. For another rule, register its implementation
and supply its own `rule_parameters`; the generic core has no closed enum of
rule algorithms.

## Step 5. Read the prompt and case resources

`extensions.reference_v3_7` points to [the case module](../examples/fe_walter/extensions/__init__.py).
Its `validate_backend()` checks resources; `build_backend()` constructs a
`ReferenceBackend` over the common `ConfiguredBackend`.
The original standalone Anik runner is a test oracle, not this example's engine.

| `reference` field | Value in the available-information example | Meaning |
|---|---|---|
| `profile` | `fe_walter` | Serialized case profile; must match the physical profile ID. |
| `method` | `zeroshot` | Case machine ID for available-information operation. The other ID is `dkp`. |
| `consultation_mode` | `daily` | Request a decision each day instead of the native inflow-threshold shortcut. |
| `response_validation` | `policy` | Validate the case response contract within the bounded attempt loop. |
| `system_prompt` | Seasonal available-information text file | Exact system message, shown below. |
| `system_prompt_mode` | `custom` | Record the approved seasonal-target edit as a deliberate variation from the serialized original. |
| `prompt_storage` | `false` | Omit the explicit storage-volume line; pool elevation remains available. |
| `hide_availability_line` | `false` | Permit the availability-ceiling line only if `prompt_storage` is enabled. With storage disabled, neither line is shown. |
| `dkp_no_missing_inputs` | `false` | In the knowledge method, retain missing-input response fields and relevant retrieved guidance. Not active in the available-information method. |
| `zeroshot_knowledge` | `target` | Retain the target-condition provenance. The explicit custom system file supplies the actual system text. |

Open [the actual system prompt](../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt):

```{literalinclude} ../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt
:language: text
```

The case does not use a generic `prompt_file`: its extension builds native
messages explicitly. `NativePromptFormatter` adds the date, inflow in cfs,
beginning pool elevation, interval length and up to two committed historical
decisions. History distinguishes requested release from implemented **total
outflow**, including spill. Day one has no prior decision.
This is different from generic agents that render `$observation` in a user template.
No shared system instruction is automatically inserted.

The extension also reads [anik_v3_7.json](../examples/fe_walter/profiles/anik_v3_7.json) and its referenced
elevation–storage CSV. `load_case_profile()` checks their hashes.
`CaseProfile.storage_to_elevation()` interpolates acre-ft to ft NGVD29;
the physical engine continues to use m³. These case resources remain in `examples`.
They are not another basin's default reservoir curve or operating targets.

### Add retrieved operating knowledge

Use [llm_knowledge.yaml](../examples/fe_walter/coupled/llm_knowledge.yaml);
it selects this complete agent file while sharing the same model and hydrology:

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_knowledge.yaml
:language: yaml
```

`reference.method: dkp` selects the case's retrieved-knowledge path.
`reference.dkp` identifies
[DKP_FEWalter_Dam_v1.2.md](../examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md).
Its explicit system message is:

```{literalinclude} ../examples/fe_walter/prompts/dkp_seasonal_v1_system.txt
:language: text
```

Hydrology, physical state, provider settings and daily consultation remain the same.
The case `DKPRetriever` selects relevant local document sections before composing
the prompt. It does not require a vector database.
For another study, generic `knowledge`, `information` and `context_providers`
are described in [prompt customization](../docs/CONFIGURATION.md).
The current FE YAML does not select a generic information profile.
Missing downstream observations are not invented.

## Step 6. Follow the input and output of one decision

1. `network.py` supplies the prepared inlet and current reservoir state.
2. The formatter converts m³/s to cfs and m³ to acre-ft, then derives pool elevation.
3. The selected provider receives the actual system and daily user messages.
4. The case reply contains reasoning, target/direction fields and `release_cfs`.
   The knowledge reply additionally contains `operating_mode`, `rules_applied`
   and `missing_inputs`.
5. `NativeResponseParser` validates the response, converts cfs to m³/s and clips
   the proposal to the case's 50–10,000 cfs limits. The raw reply remains recorded.
6. Common physics applies available water, calculates controlled release, spill
   and ending storage. Routing receives controlled release plus spill once.
7. The committed transition updates the next day's state and two-entry history.

Seasonal target noncompliance is an operating audit result; it is not a reason
to sample another reply. See [Inputs and outputs](../docs/INPUT_OUTPUT.md)
for units, schemas and the exported files.

## Step 7. Check, prepare and inspect

Validate the canonical rule entry, then the LLM method you intend to use:

```powershell
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
reservoir-experiment check examples/fe_walter/coupled/llm_available.yaml
```

Both plans contain 366 days and one agent. The canonical rule plans zero LLM
calls; the LLM entry plans 366 decisions. Both checks make zero provider requests.
The LLM prompt preview uses placeholder flow for validation, not newly simulated
January 1 inflow. Review all selected files and prompt text before execution.

Preparation is separate and makes no provider request:

```powershell
reservoir-experiment prepare examples/fe_walter/coupled/experiment.yaml
```

This runs the accepted continuous hydrology or verifies an explicitly reused
preparation. It writes `inflows.csv`, `case.json`, `experiment.yaml`,
`hydrology.json` and `preparation.json` under your chosen output.
The generated `experiment.yaml` is an operation plan; edit the original input,
not generated files. See [the execution commands](../examples/fe_walter/coupled/README.md#run-an-llm-method)
when you intentionally enable model requests later.

The shared [auditors.yaml](../examples/fe_walter/coupled/auditors.yaml)
declares the check selected by `auditors: [release_limits]`:

```{literalinclude} ../examples/fe_walter/coupled/auditors.yaml
:language: yaml
```

`release_limits` selects `release_bounds` version `1`.
The FE extension also retains its native diagnostic audit. Read `summary.json`,
`reservoir_trajectory.csv`, `network_flows.csv`, `decisions.jsonl`,
`audit.jsonl`, `physics.jsonl`, `provider_attempts.jsonl` and retained raw artifacts
together. Audit FAIL does not by itself mean execution failed.
For interruptions, follow [resume](../docs/BUILD_SIMULATION.md#9-resume-after-an-interruption).

## Step 8. Read the verified 2016 results

> **Example confirmation pending.** The saved outputs verify execution only.
> The prompt version and Anik-example equivalence await user confirmation;
> do not treat these results as an accepted reproduction.

Continue with the [current 2016 annual results](../examples/fe_walter/coupled/README.md#verified-2016-results).
All three methods contain 366 unique daily decisions.
The available-information recovery chain retains **369 actual attempts**:
366 successful replies and three timeouts. It preserves the first eight
committed days and reposts none. The retrieved-knowledge chain retains **368 actual attempts**, including two
timeouts, and also reposts no committed days.


Read [the 2016 daily table](../examples/fe_walter/coupled/outputs/2016/daily.csv),
[verification summary](../examples/fe_walter/coupled/outputs/2016/summary.json) and
[source/output pins](../examples/fe_walter/coupled/outputs/2016/pins.json) together.
Requested release, implemented controlled release and spill remain distinct.
The [15 June available-information sample](../examples/fe_walter/coupled/outputs/2016/llm_available_decision.json)
and [retrieved-knowledge sample](../examples/fe_walter/coupled/outputs/2016/llm_knowledge_decision.json)
show messages, raw response, schema/parser fields, diagnostic audit, normalized
action and the implemented transition. They do not include a next-day
observation. The next state follows from committed ending storage and
implemented total outflow.

Audit FAIL is a diagnostic operating result, not a seasonal pool-compliance
score or model-format failure. Saved-file verification establishes execution
integrity and water accounting; it does not accept policy quality. These
single realizations do not rank the methods.

The [earlier 2016 diagnostic](../examples/fe_walter/coupled/README.md#historical-2016-diagnostic-preserved)
and the older notebooks retain their original prompts, audit counts and samples.
Offline supplied-reply tests establish wiring and recovery, not LLM quality.

## Code map

| User task | Code responsible |
|---|---|
| Read the experiment and resolve files | [configuration.py](../src/llm_reservoir_agent/configuration.py), [agent_configuration.py](../src/llm_reservoir_agent/agent_configuration.py) |
| Check/prepare the full-weather entry | [coupled.py](../src/llm_reservoir_agent/coupled.py): `load_coupled_settings`, `prepare_coupled`, `run_coupled` |
| Load forcing and bind flow | [weather.py](../src/llm_reservoir_agent/weather.py): `load_weather`, `validate_bindings`, `simulate_weather` |
| Preserve FE messages, history and parsing | [reference_backend.py](../examples/fe_walter/extensions/reference_backend.py), [native_case.py](../examples/fe_walter/extensions/native_case.py) |
| Call and record the selected model | [configured_backend.py](../src/llm_reservoir_agent/configured_backend.py), [providers.py](../src/llm_reservoir_agent/providers.py) |
| Apply reservoir physics and route downstream | [physics.py](../src/llm_reservoir_agent/physics.py), [network.py](../src/llm_reservoir_agent/network.py) |
| Commit evidence and recover interruptions | [experiment.py](../src/llm_reservoir_agent/experiment.py), [recovery.py](../src/llm_reservoir_agent/recovery.py) |

[Python API documentation](../docs/API_REFERENCE.md) ·
[Return to the common case](../examples/fe_walter/README.md)
