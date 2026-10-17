# F.E. Walter: configure and follow a reservoir decision

Apply the common [simulation workflow](../docs/BUILD_SIMULATION.md) and
[agent configuration](../docs/CONFIGURATION.md) to one real reservoir. Read the
[FE Walter study background](../examples/fe_walter/README.md) first: it explains
the site, data, seasonal targets and modeling assumptions.

Here the hydrology and physical reservoir stay fixed while you choose a
Rule-based agent, an LLM with available information, or an LLM with retrieved
operating knowledge. Basin construction, parameter estimation and C&V remain
in the [HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
This walkthrough concentrates on LLM settings and their connections.

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
| Global experiment | `experiment.yaml`, `rule.yaml`, `llm_available.gemma4.yaml`, `llm_knowledge.gemma4.yaml` | Schema, dates, run/output, call gate, section references and explicit extension catalog. |
| Hydrology and physical coupling | `hydrology.yaml`, `reservoirs.json` | Weather/native model, source-to-inlet bindings, physical state and routing graph. |
| Per-agent behavior | `agents.rule.yaml`, `agents.llm_available.yaml`, `agents.llm_knowledge.yaml` | Exact reservoir assignment, rule or LLM and its case-specific settings. |
| Shared model and checks | `models.gemma4.yaml`, `auditors.yaml` | Named provider profile and diagnostic checks selected by each agent. |

All entries use `hydroops-coupled-simulation.v2`. A section reference such as
`hydrology: {file: hydrology.yaml}` loads that section from its sibling file.
Resource paths are relative to the file that declares them. Keep copies in the
same directory unless you deliberately update those paths. For a new study,
choose a new `run_id` and `output`; source files and prior records remain pinned.

The current Gemma 4 entry selects the same case agent and an explicit model
profile. Older unsuffixed LLM entries retain Gemma 3 for historical
reproducibility; use the new entry for the current model controls:

```{literalinclude} ../examples/fe_walter/coupled/llm_available.gemma4.yaml
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

| Change for a new execution | Retain for this comparison | Optional additions |
|---|---|---|
| Run ID/output; method; service address if needed | Accepted hydrology, physical state, seasonal targets, prompts, case profile and daily history | Retrieved knowledge, extra information, custom context and diagnostic auditors |

For another reservoir, set these inputs deliberately; FE Walter values are
example settings, not defaults imposed by the core.

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
selects a profile in [models.gemma4.yaml](../examples/fe_walter/coupled/models.gemma4.yaml).
`customization.backend: reference_v3_7` selects the explicitly registered case
extension. Its `parameters.reference` mapping belongs to this example.

```{literalinclude} ../examples/fe_walter/coupled/models.gemma4.yaml
:language: yaml
```

| `models.reservoir_model` field | Value | What it controls |
|---|---|---|
| `provider` | `ollama` | Provider adapter. |
| `model` | `gemma4:12b` | Explicit model ID, installed separately. |
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

## Step 5. Design what the LLM sees

The [common prompt guide](../docs/CONFIGURATION.md) explains user templates,
optional knowledge and custom context. FE Walter uses a case-owned formatter
to reproduce Anik V3.7, with the confirmed seasonal-target change. Keep this
formatter when reproducing the case; use generic templates for another study.

| Component | FE Walter design | Setting |
|---|---|---|
| System instructions | Operation task, four seasonal targets and response fields | Versioned [available-information prompt](../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt) or [knowledge prompt](../examples/fe_walter/prompts/dkp_seasonal_v2_system.txt) |
| Daily user message | Date, inflow, beginning pool elevation, interval and up to two completed decisions | Case formatter selected by `customization.backend` |
| Optional knowledge | Relevant sections of the operating document, included before the request | Knowledge agent's `reference.dkp` path |
| Response contract | Proposed release in cfs plus the method's explanatory fields | Case response schema and parser |

The LLM does not automatically receive the weather, soil or land-cover tables.
Those inputs produce hydrological inflow. Only information placed in its actual
messages is visible to the model. No shared system instruction is inserted.

The available-information method receives the daily state without retrieved
document sections. To add retrieved knowledge, select
[llm_knowledge.gemma4.yaml](../examples/fe_walter/coupled/llm_knowledge.gemma4.yaml).
It uses this agent file:

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_knowledge.yaml
:language: yaml
```

This case retrieves local document sections without a vector database. Its
knowledge response has eight fields and excludes `missing_inputs`. The
[Anik compatibility reference](#reference-exact-anik-prompt-and-case-contract)
below explains the preserved details after the main workflow.

## Step 6. Follow the input and output of one decision

1. `network.py` supplies the prepared inlet and current reservoir state.
2. The formatter converts m³/s to cfs and m³ to acre-ft, then derives pool elevation.
3. The selected provider receives the actual system and daily user messages.
4. The case reply contains reasoning, target/direction fields and `release_cfs`.
   The knowledge reply additionally contains `operating_mode` and
   `rules_applied`, for eight fields in total; it has no `missing_inputs` field.
5. `NativeResponseParser` validates the response, converts cfs to m³/s and clips
   the proposal to the case's 50–10,000 cfs limits. The raw reply remains recorded.
6. Common physics applies available water, calculates controlled release, spill
   and ending storage. Routing receives controlled release plus spill once.
7. The saved transition updates the next day's state and two-entry history.

Seasonal target noncompliance is an operating audit result; it is not a reason
to sample another reply. See [Inputs and outputs](../docs/INPUT_OUTPUT.md)
for units, schemas and the exported files.

## Step 7. Check, prepare, run and verify

Run commands from the repository root. **Check first**; this previews the
configuration, prompt and schema without hydrology or model requests:

```powershell
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
reservoir-experiment check examples/fe_walter/coupled/llm_available.gemma4.yaml
reservoir-experiment check examples/fe_walter/coupled/llm_knowledge.gemma4.yaml
```

Expect 366 operation days, zero planned provider decisions for the rule, and
366 daily decisions for each LLM method before eligible retries.
The preview uses placeholder inflow, not simulated January 1 flow.

**Prepare and run the rule first** to check the physical connections:

```powershell
reservoir-experiment prepare examples/fe_walter/coupled/experiment.yaml
reservoir-experiment run examples/fe_walter/coupled/experiment.yaml
reservoir-experiment verify runs/fe-walter-coupled-rule/operation
```

Preparation computes the accepted continuous upstream hydrology, then selects
2016. It does not contact a model. If the identical preparation already exists,
follow [Reuse the prepared hydrology](../examples/fe_walter/coupled/README.md#reuse-the-prepared-hydrology)
before preparing LLM entries. Keep the dates, forcing, model, bindings and
runtime unchanged. Each method starts its own reservoir state and history.

**When you intend to request real LLM decisions**, use the Gemma 4 entry:

```powershell
reservoir-experiment prepare examples/fe_walter/coupled/llm_available.gemma4.yaml
reservoir-experiment run examples/fe_walter/coupled/llm_available.gemma4.yaml --allow-network
reservoir-experiment verify runs/fe-walter-coupled-gemma4-llm_available/operation
```

For retrieved knowledge, substitute `llm_knowledge.gemma4.yaml` in both
configuration commands and verify
`runs/fe-walter-coupled-gemma4-llm_knowledge/operation`.
Choose a new run ID/output when repeating an experiment. The model must already
be available at the configured service. `--allow-network` permits requests;
reading this page does not execute them.

| Location | Contents |
|---|---|
| Original `examples/fe_walter/coupled/*.yaml` | Editable user inputs; paths resolve relative to their declaring file |
| Your output root | Prepared `inflows.csv`, `case.json`, generated operation `experiment.yaml`, `hydrology.json` and `preparation.json` |
| `<output>/operation/` | `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `decisions.jsonl`, `audit.jsonl`, `physics.jsonl` and provider evidence |

Edit original inputs rather than generated files. Expect 366 unique dates in
a completed annual trajectory. `verify` checks saved evidence and water
accounting. A seasonal audit FAIL does not mean the provider or execution failed
and never triggers another sample. The selected
[auditor file](../examples/fe_walter/coupled/auditors.yaml) adds release-limit
diagnostics; the FE extension also records its native operating audit.

For an interruption, follow [recovery](../docs/BUILD_SIMULATION.md#9-resume-after-an-interruption).
Use the source run's `operation/` directory and write to a new output. Preserve
raw requests/replies and attempts to explain the result.

## Step 8. Read the verified 2016 results

The [current Gemma 4 comparison](../examples/fe_walter/coupled/README.md#verified-2016-results)
contains four complete 366-day runs: original Anik and HydroOpsLLM, each with
available information and retrieved knowledge. Each used 366 actual HTTP attempts
without retry or fallback. The saved comparison used isolated QA run entries;
the new `.gemma4.yaml` files above expose its model controls as teaching inputs
with new output locations.

Read the [water-level and controlled-release plot](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/pool_release.png),
[daily values](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/daily.csv)
and [comparison summary](../examples/fe_walter/coupled/outputs/gemma4_2016_comparison/summary.json).
Pool elevation is end-of-day; controlled release excludes spill.

Same-reply offline replay checks the two engines with identical saved replies.
Independent real trajectories differ at temperature 0.7; completing a year does
not establish seasonal compliance or rank methods. Read the reported winter
and fall checks alongside engineering verification.

[Earlier Gemma 3 annual results](../examples/fe_walter/coupled/README.md#earlier-2016-configuration-preserved)
and the [historical five-year DKP study](../examples/fe_walter/results.md) retain
their original settings. They are separate experiments.

For the earlier Gemma 3 diagnostic, the preserved files remain downloadable:
[daily values](../examples/fe_walter/coupled/outputs/2016/daily.csv),
[summary](../examples/fe_walter/coupled/outputs/2016/summary.json),
[source pins](../examples/fe_walter/coupled/outputs/2016/pins.json),
[available-information sample](../examples/fe_walter/coupled/outputs/2016/llm_available_decision.json)
and [knowledge sample](../examples/fe_walter/coupled/outputs/2016/llm_knowledge_decision.json).
These files retain the earlier response contract, including its incorrect
missing-information fallback; use the Gemma 4 links above for the current study.

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

## Reference: exact Anik prompt and case contract

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
| `hide_availability_line` | `true` | Preserve Anik V3.7 behavior by omitting the availability-ceiling line. |
| `dkp_no_missing_inputs` | `true` | Preserve Anik V3.7 knowledge behavior: omit `missing_inputs` and the missing-information fallback from the knowledge prompt, response schema and retrieval. Not active in the available-information method. |
| `zeroshot_knowledge` | `target` | Retain the target-condition provenance. The explicit custom system file supplies the actual system text. |

Open [the actual system prompt](../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt):

```{literalinclude} ../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt
:language: text
```

The confirmed operation target keeps the pool within 1297–1303 ft from
November 1 through March 14; between 1300 and 1370 ft from March 15 through
May 9 while filling toward 1370 ft by May 10; at or below 1370 ft from May 10
through October 14; and between 1300 and 1370 ft and falling from October 15
through October 31, reaching near 1300 ft on November 1.

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

Use [llm_knowledge.gemma4.yaml](../examples/fe_walter/coupled/llm_knowledge.gemma4.yaml);
it selects this complete agent file while sharing the same model and hydrology:

```{literalinclude} ../examples/fe_walter/coupled/agents.llm_knowledge.yaml
:language: yaml
```

`reference.method: dkp` selects the case's retrieved-knowledge path.
`reference.dkp` identifies
[DKP_FEWalter_Dam_v1.2.md](../examples/fe_walter/knowledge/DKP_FEWalter_Dam_v1.2.md).
Its explicit system message is:

[Download the available-information prompt](../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt)
or [the corrected knowledge prompt](../examples/fe_walter/prompts/dkp_seasonal_v2_system.txt).

```{literalinclude} ../examples/fe_walter/prompts/dkp_seasonal_v2_system.txt
:language: text
```

Hydrology, physical state, provider settings and daily consultation remain the same.
The case `DKPRetriever` selects relevant local document sections before composing
the prompt. It does not require a vector database.
For another study, generic `knowledge`, `information` and `context_providers`
are described in [prompt customization](../docs/CONFIGURATION.md).
The current FE YAML does not select a generic information profile. With
`dkp_no_missing_inputs: true`, the knowledge system prompt, response schema and
retrieval exclude the missing-information fallback, and the response contract
has exactly eight fields:
`applicable_target_ft`, `pool_position`, `intended_storage_direction`,
`release_relation_to_inflow`, `operating_mode`, `rules_applied`, `reasoning` and
`release_cfs`. It neither requests `missing_inputs` nor invents missing
downstream observations. The frozen v1 prompt remains only as a reproducibility
dependency for prior saved output.
