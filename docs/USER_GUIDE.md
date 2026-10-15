# HydroOpsLM settings guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

Start with [Build a simulation](BUILD_SIMULATION.md), then use the
[FE Walter case](../examples/fe_walter/README.md) to see these settings in practice.
This is the formal guide for the generic `configured` strategy.
[LLM modules](LLM_MODULES.md) explains the decision interfaces; method-specific
settings remain with the [FE Walter examples](../examples/fe_walter/README.md).

## 1. Prepare your files

| File | Responsibility |
|---|---|
| Experiment YAML | Dates, output, agents, models, prompts and auditors |
| Case JSON | Reservoirs, river connections, physics, initial state and inflow/hash |
| Inflow CSV | `date,node,local_inflow_cms`, ISO dates, daily local inflow in m³/s |
| Prompt TXT | Independent UTF-8 instruction template |
| Knowledge TXT/MD, optional | Identified, versioned local documents |
| Context JSON, optional | Static supplemental facts |
| Information CSV, optional | Timestamped observations or forecasts selected by a profile |

Export Excel to UTF-8 CSV without BOM. Convert cfs to m³/s with
`0.028316846592`. Include every routing node each day, including zero-flow nodes.
Already routed total inflow must not be added again as incremental local inflow.
Record the CSV SHA256 in the case. See [input preparation](../tutorials/main.ipynb).

## 2. Connect agents to reservoirs

One controlled reservoir needs exactly one independent agent. Passive outlets
have no agent. Agent count is the number of entries in `agents`; no `n_agents`
field is needed. Model profiles may be shared, but backend, feedback and auditor
state belong to each reservoir. River topology determines downstream influence.
The current runner is daily and has no central joint-planning agent.

This is a configuration shape to adapt to **your own case and prompt**, not a
fourth public method or a ready-to-run data bundle:

```yaml
schema_version: llm-reservoir-experiment.v1 # Supported YAML contract.
case: ../my_case/case.json                 # Your network, physics and input/hash.
run_id: my-daily-test                    # Change for each new experiment.
output: ../runs/my-daily-test            # Must not already exist.
max_calls: 3                              # Three days × one LLM agent.
models:
  reservoir_model:
    provider: ollama
    model: gemma3:4b                        # Already installed locally.
    base_url: http://localhost:11434
    temperature: 0.7                       # Explicit sampling setting.
    max_tokens: 2048
    timeout_seconds: 120
auditors:                                 # Versioned operating checks.
  release_limits:
    type: release_bounds
    version: "1"
agents:
  operator_1:                             # Independent decision unit.
    reservoir: R1                         # Exact controlled reservoir key in case.
    strategy: configured                  # Generic prompt/knowledge backend.
    mode: llm                             # Render prompt and request a proposal.
    model: reservoir_model                # Select the profile above.
    prompt: ../my_case/prompts/controller.txt # Instruction template.
    prompt_version: "1"                    # Update when changing the instructions.
    knowledge: {}                         # Optional ID -> local document path.
    context: {}                           # Optional static supplemental facts.
    response_schema: reservoir-action.v1  # Standard normalized action.
    auditors: [release_limits]            # Checks enabled for this agent.
```

### How the settings connect

**Experiment → case → reservoir.** The case supplies water, storage and river
connections. Each entry in `agents` selects one reservoir and one decision method.
Its `model` and `auditors` values refer to named definitions in the same YAML.
The prompt receives the information selected for that decision; it cannot change
the host's inflow, storage or physical limits.

#### Experiment and output

| Field | Meaning in this example |
|---|---|
| `schema_version` | Configuration format understood by the runner; keep the supported value. |
| `case` | Case JSON containing reservoir IDs, physics, initial state and inflow source. |
| `run_id` | Name saved with every record; use a new name for a new experiment. |
| `output` | New folder for results and trace; an existing output is refused. |
| `max_calls` | Maximum model requests for the whole run, not per agent. Here: three days × one LLM agent. |

#### Model and operating checks

| Field | Meaning in this example |
|---|---|
| `models.reservoir_model` | A user-chosen profile name; agents refer to this name. It does not create an agent. |
| `provider` | Provider interface; `ollama` uses the configured Ollama service. |
| `model` inside the profile | Installed model ID, here `gemma3:4b`. No automatic download. |
| `base_url` | Address of that service, here the local Ollama port. |
| `temperature` | Sampling setting; keep **0.7** for this design. It does not guarantee identical replies. |
| `max_tokens` | Maximum generated output tokens per request; an incomplete reply is rejected. |
| `timeout_seconds` | Time allowed for one request. Timeout stops the run; no automatic retry. |
| `auditors.release_limits` | A named audit definition, enabled only by agents that list it. |
| `type: release_bounds` | Compares requested release with the feasible bound in the host observation. |
| `version` | Audit version recorded with its specification and implementation hashes. |

#### Agent, prompt and information

| Field | Meaning in this example |
|---|---|
| `agents.operator_1` | User-chosen ID for this independent decision unit. |
| `reservoir` | Exact controlled-reservoir ID from the case, here `R1`. |
| `strategy: configured` | Generic prompt and normalized-action interface. Reference methods have their own options. |
| `mode: llm` | Renders the prompt and requests a model reply when execution is explicitly enabled. |
| `model: reservoir_model` | Selects the model profile above; this is a reference, not another model ID. |
| `prompt` | Independent UTF-8 template containing operating instructions and supported placeholders. |
| `prompt_version` | Version of those instructions; update when changing the template. |
| `knowledge` | Optional document-ID-to-file mapping. Generic mode inserts full documents; reference retrieval is method-specific. |
| `context` | Optional static facts, separate from the protected current observation. |
| `response_schema` | Expected normalized action, here `reservoir-action.v1` with requested `release_cms`. |
| `auditors: [release_limits]` | Enables the named audit for this agent. Audit results do not overwrite a decision. |

For downstream gauges or forecasts, add a declared information source and profile
as shown in [Decision information](INFORMATION.md). The example's empty
`context` and `knowledge` mappings do not read those series automatically.


For an installed wheel with inputs shared across case folders, set `case_root` to their common data-bundle directory.

All paths resolve from the YAML directory. `case_root` optionally sets the
allowed case bundle root. `start_date`/`end_date` are quoted ISO dates inside
the existing continuous input interval. A new starting date does not warm up
the model or inherit another run: provide verified initial storage and routing
state in a new case. Preserve accepted files.

## 3. Choose what the LLM sees

`$observation` is the protected host observation: time, current local inflow,
state, release upper bound and context. `$information` is a separate, opt-in
`decision-information.v1` snapshot assembled from a named profile. Static
context and selected information cannot replace host storage, inflow or physics.

| Placeholder | Contents |
|---|---|
| `$agent_id` | JSON-encoded agent ID |
| `$observation` | Current observation plus separate static context |
| `$knowledge` | Selected package IDs mapped to their full document text |
| `$previous_transition` | Previous committed observation/action/physics record; first day null |
| `$information` | Only aliases selected by the agent's information profile |

Templates use Python `string.Template`; write `$$` for a literal dollar sign.
Unknown placeholders stop validation. The generic backend supplies a fixed
system message for the JSON contract; operation instructions in `prompt`
form the user message. It has no generic YAML `system_prompt` field.
Local knowledge is included in full; automatic retrieval and agent conversations
are not built-in generic YAML options. Timestamped observations and forecasts
use declared [information sources and profiles](INFORMATION.md). Extension
sources name providers registered in Python; YAML cannot import arbitrary code.

Generic `mode: offline` returns `release_cms` directly and does not render or
execute the prompt. The reference examples' offline mode instead renders their
preserved prompt and parses supplied synthetic replies. These are distinct tests.

## 4. Configure a model for a future experiment

`mode: llm` requires an agent `model` referring to a `models` profile;
remove `release_cms`. Model configuration does not download or call a model.
Keep temperature **0.7** for the current experiment design.

| Model field | Meaning |
|---|---|
| `provider` | `ollama` or `openai_compatible` |
| `model`, `base_url` | Available model ID and final HTTP(S) endpoint |
| `temperature` | Sampling temperature; use 0.7 |
| `max_tokens` | Positive output limit; default 512 |
| `timeout_seconds` | Positive single-request timeout; default 60 |
| `seed` | Optional integer; provider support varies, reproducibility is not guaranteed |
| `api_key_env` | Environment-variable name, never the credential value |

Set `max_calls` to cover days × LLM agents. Real execution also requires
`--allow-network` and case readiness; reading saved results requires neither gate nor a model call.
Unsupported settings/provider errors stop without retries or a fallback.
See [live readiness](LIVE_READINESS.md) before enabling a provider.

## 5. Define the proposal, checker and auditor

The normalized proposal is requested controlled release:

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

The reader parses the reply; the checker rejects unsupported fields, invalid
JSON, nonfinite/negative values and incomplete required output before release.
Physics separately determines implemented release and spill.

| Generic auditor | Settings and meaning |
|---|---|
| `release_bounds` | Version and optional nonnegative `tolerance_cms`; requested release versus feasible bound |
| `field_range` | Version, dot-separated `path`, finite `minimum` and/or `maximum`, `on_violation: FAIL` or `WARN` |

Missing/nonnumeric audit fields are UNKNOWN. All enabled checks participate:
FAIL > UNKNOWN > WARN > PASS; original backend audits remain preserved.
An empty suite is UNKNOWN. Audit FAIL is diagnostic and does not silently
substitute a decision. Add case-specific rules through
[versioned auditor plugins](auditor_plugins.md); YAML does not load arbitrary Python.
Specialized response schemas and reference retrieval belong to their specific
[examples](../examples/fe_walter/README.md), not a universal operating rule.

## 6. Check, run and verify

Use `check → run → verify`; `check` makes no provider call. Model execution
requires `run --allow-network` and a ready case. For a no-provider test only,
use a supplied-response configuration and `verify --require-offline`. Existing output is refused; use a new run ID/output
rather than overwriting. This runner has no automatic resume.

Optional `outcome_checks` run after routing and write `outcome_audit.jsonl`.
They compare control-point flow with explicit scalar or selected-information
limits. They are diagnostic: their status does not correct a release, optimize
routing or guarantee safety. See [Decision information](INFORMATION.md#control-point-outcome-checks).

| Output | What to inspect |
|---|---|
| `experiment.json`, `summary.json` | Settings, source/runtime hashes, status and counts |
| `decisions.jsonl`, `audit.jsonl` | Info/proposal and original audit verdict; decision ID binding |
| `physics.jsonl`, `backend_events.jsonl` | Executed outcome, committed feedback and failures |
| `raw/` | Full available prompt/reply/audit and source references |
| `reservoir_trajectory.csv` | Requested/implemented release, spill, storage and balance |
| `network_flows.csv`, `network_balance.csv` | Routed flows and reservoir/channel water balance |
| `reach_volume_trace.json` | Reach inflow, outflow and channel storage |
| `outcome_audit.jsonl` | Optional post-routing control-point diagnostics |

Use [decision-flow inspection](../tutorials/main.ipynb)
to display info, actual prompt, reply, proposal, checker, audit, physics and feedback.
Format acceptance and physical acceptance do not establish strategy quality.
Missing evidence/cost stays unknown; synthetic replies are not live model results.

[Multiple reservoirs / own data](../tutorials/advanced.ipynb) ·
[Native hydrology setup](HYDROLOGY_SETUP.md) · [LLM modules](LLM_MODULES.md)

## Preserved FE Walter prompt profile

The reference examples use `strategy: reference_v3_7` and
`system_prompt_mode: original`. Versioned TXT files remain independent in
`prompts/fe_walter_reference`; native builders render date/state/history and
retrieve DKP excerpts. Live mode forbids a supplied `responses` fixture. Native
release/schema is cfs; the adapter converts it once to m³/s. These FE Walter
options are case-specific, not default rules for another reservoir.

A complete generation is required: Ollama `done: true`, with `done_reason: stop`
when present, or OpenAI-compatible `finish_reason: stop`. Missing, null or
non-stop status is rejected as applicable. Valid JSON alone is insufficient.
`raw/` retains actual messages, request hash, reply, native audit and available
request ID/usage; credential values are excluded. See the saved
[Ollama walkthrough](../examples/fe_walter/README.md).

## Troubleshooting

| What you see | What it means / next step |
|---|---|
| Incomplete generation or invalid response | Execution stops before release is applied. Inspect the raw reply and completion fields; correct the configuration before a new run. |
| Invalid schema, unit or release value | Response checks reject the proposal. Match the selected parser and action schema. |
| Audit FAIL or WARN with valid water balance | The configured operating criteria flagged the decision. Read `audit.jsonl`; physical acceptance does not override it. |
| Audit UNKNOWN | The decision has no applicable strategy verdict. Configure a reservoir-specific auditor if strategy assessment is required. |
| Readiness blocked | Resolve the conditions in [live readiness](LIVE_READINESS.md); do not remove the gate to force execution. |
| Output already exists | Choose a new `run_id` and `output`. Preserve the previous results. |
