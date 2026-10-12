# HydroOpsLM settings guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

Start with an offline [example](../examples/README.md), then adapt its YAML.
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

Export Excel to UTF-8 CSV without BOM. Convert cfs to m³/s with
`0.028316846592`. Include every routing node each day, including zero-flow nodes.
Already routed total inflow must not be added again as incremental local inflow.
Record the CSV SHA256 in the case. See [input preparation](../tutorials/01_input_and_map.ipynb).

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
run_id: my-offline-test                    # Change for each new experiment.
output: ../runs/my-offline-test            # Must not already exist.
max_calls: 0                              # No real-provider calls.
auditors:                                 # Versioned operating checks.
  release_limits:
    type: release_bounds
    version: "1"
agents:
  operator_1:                             # Independent decision unit.
    reservoir: R1                         # Exact controlled reservoir key in case.
    strategy: configured                  # Generic prompt/knowledge backend.
    mode: offline                         # Fixed test action; bypasses model/prompt.
    release_cms: 5                        # Requested controlled release in m³/s.
    prompt: ../my_case/prompts/controller.txt # Instruction template.
    prompt_version: "1"                    # Update when changing the instructions.
    knowledge: {}                         # Optional ID -> local document path.
    context: {}                           # Optional static supplemental facts.
    response_schema: reservoir-action.v1  # Standard normalized action.
    auditors: [release_limits]            # Checks enabled for this agent.
```

All paths resolve from the YAML directory. `case_root` optionally sets the
allowed case bundle root. `start_date`/`end_date` are quoted ISO dates inside
the existing continuous input interval. A new starting date does not warm up
the model or inherit another run: provide verified initial storage and routing
state in a new case. Preserve accepted files.

## 3. Choose what the LLM sees

The teaching label **info** means the supplied observation, not a YAML field.
In the generic template, `$observation` contains `observed_hydrology`
(time, inflow, state, release upper bound and context) and `static_context`.
Static context cannot replace host storage or inflow.

| Placeholder | Contents |
|---|---|
| `$agent_id` | JSON-encoded agent ID |
| `$observation` | Current observation plus separate static context |
| `$knowledge` | Selected package IDs mapped to their full document text |
| `$previous_transition` | Previous committed observation/action/physics record; first day null |

Templates use Python `string.Template`; write `$$` for a literal dollar sign.
Unknown placeholders stop validation. The generic backend supplies a fixed
system message for the JSON contract; operation instructions in `prompt`
form the user message. It has no generic YAML `system_prompt` field.
Local knowledge is included in full; automatic retrieval, arbitrary dynamic CSV
features, forecasts and agent conversations are not built-in generic YAML options.
Extend the Python backend with causal, timestamped inputs when needed.

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
`--allow-network` and case readiness; this guide's validation remains offline.
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

## 6. Run and read evidence

Use the README's `check → run → verify --require-offline` commands with a
complete offline YAML. Existing output is refused; use a new run ID/output
rather than overwriting. This runner has no automatic resume.

| Output | What to inspect |
|---|---|
| `experiment.json`, `summary.json` | Settings, source/runtime hashes, status and counts |
| `decisions.jsonl`, `audit.jsonl` | Info/proposal and original audit verdict; decision ID binding |
| `physics.jsonl`, `backend_events.jsonl` | Executed outcome, committed feedback and failures |
| `raw/` | Full available prompt/reply/audit and source references |
| `reservoir_trajectory.csv` | Requested/implemented release, spill, storage and balance |
| `network_flows.csv`, `network_balance.csv` | Routed flows and reservoir/channel water balance |
| `reach_volume_trace.json` | Reach inflow, outflow and channel storage |

Use [decision-flow inspection](../tutorials/README.md#inspect-a-complete-decision)
to display info, actual prompt, reply, proposal, checker, audit, physics and feedback.
Format acceptance and physical acceptance do not establish strategy quality.
Missing evidence/cost stays unknown; synthetic replies are not live model results.

[Multiple reservoirs / own data](../tutorials/07_multi_and_custom.ipynb) ·
[Native hydrology setup](HYDROLOGY_SETUP.md) · [LLM modules](LLM_MODULES.md)
