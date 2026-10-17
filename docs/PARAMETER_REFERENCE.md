# Parameter reference

This page summarizes the public weather-to-operation configuration. Values shown
as defaults are software defaults. Example values are not recommendations.
Unknown keys, duplicate YAML keys and nonfinite numbers are rejected.

## Coupled experiment

New work uses `hydroops-coupled-simulation.v2`. The v1 inline form remains
accepted.

| Key | Required / default | Meaning |
|---|---|---|
| `schema_version` | required | Configuration format read by the loader: `hydroops-coupled-simulation.v2`; not the package version. |
| `run_id` | required text | Name saved with the run and its decisions; does not set the output location. |
| `output` | required path | New folder for preparation and its `operation/` results subfolder; existing output is refused. |
| `case` | required path | Physical reservoir/network YAML or JSON using `reservoir-physical-case.v1`. |
| `start_date`, `end_date` | required quoted dates | Inclusive operation period inside the native model period. |
| `max_calls` | default `0` | Integer covering planned LLM requests, or explicit `null` for no total cap. |
| `hydrology` | required mapping or file section | Native model, forcing and inlet bindings. |
| `agents` | required nonempty mapping or file section | One agent per controlled reservoir. |
| `models` | default `{}` | Named provider/model settings selected by LLM agents. |
| `auditors` | default `{}` | Named decision checks. |
| `information` | default empty | `sources` and `profiles` mappings. |
| `outcome_checks` | default `{}` | Post-routing control-point diagnostics. |
| `extensions` | default `{}` | Extension ID to package `__init__.py`. |
| `source_dependencies` | generated or explicit | File path to expected SHA256. |

`hydrology`, `models`, `agents`, `auditors`, `information` and `extensions` may
be inline. The first five commonly use exactly `{file: path}`. A referenced
section replaces the whole section; no deep merge occurs. Every resource path is
relative to the file that declares it.

## Hydrology section

| Key | Required / default | Meaning |
|---|---|---|
| `model` | required path | Agent-free HydroCNHS model using GWLF or ABCD with Lohmann routing. |
| `forcing` | required path | Complete daily weather CSV for the full model period. |
| `zero_flow_nodes` | default `[]` | Operation nodes with explicit zero hydrological lateral flow. |
| `inflow_bindings` | required mapping | One non-overlapping hydrology selector for every other routing node. |
| `prepared_from` | optional path | Verified prior preparation to reuse when all hydrology inputs match. |

Weather columns are `date,subbasin_id,precipitation_mm,temperature_c,pet_cm`.
Bindings may select routed output, direct runoff or constant zero as documented in
[Weather inputs](WEATHER_INPUTS.md).

## Model profile

| Key | Required / default | Constraint |
|---|---|---|
| `provider` | required | `openai`, `anthropic`, `gemini`, `ollama` or `openai_compatible`. |
| `model` | required | Exact nonempty provider model ID. |
| `base_url` | required | HTTP(S), final service root, without credentials, query or fragment. |
| `api_key_env` | default `null` | Environment-variable name. |
| `temperature` | omitted | Finite 0 through 2; sent only when present. |
| `max_tokens` | omitted | Positive integer; sent only when present. |
| `seed` | omitted | Integer; only Ollama and OpenAI-compatible. |
| `timeout_seconds` | `60` | Positive attempt timeout. |
| `max_attempts` | `1` | Positive attempt limit per decision and profile. |
| `retry_delay_seconds` | `2` | Nonnegative delay. |
| `retryable_http_statuses` | `[]` | Unique HTTP status integers from 100 through 599. |
| `num_ctx`, `think`, `keep_alive` | omitted | Ollama-only controls. |
| `anthropic_version` | `2023-06-01` | Anthropic header version. |

See [Model providers](MODEL_PROVIDERS.md) for complete profiles and native API
paths.

## Reservoir agent

| Key | Required / default | Meaning |
|---|---|---|
| `reservoir_id` | required | Exact controlled-reservoir ID; one agent per controlled reservoir. |
| `type` | required | `rule_based` or `llm`. |
| `rule` | rule-based required | ID of an explicitly registered rule extension. |
| `rule_parameters` | `{}` | Parameters defined and validated by your selected rule module. |
| `model_profile` | live LLM required | Primary model profile ID from the experiment's `models` catalog. |
| `prompt_file` | LLM required | Nonempty UTF-8 user template; a custom message-building backend may supply its own explicit resources. |
| `auditors` | `[]` | Unique configured auditor IDs. |
| `customization` | `{}` | Optional advanced LLM controls listed below. |

The experiment owns dates, hydrology, physical topology, output and reusable
catalogs. Each agent selects a method, model, prompt, information profile and
auditors for its own reservoir. Information topology describes visibility;
`network.connections` describes water movement.

### Advanced LLM customization

All keys in this table are inside `customization`:

| Key | Required / default | Meaning |
|---|---|---|
| `fallback_models` | `[]` | Ordered unique profile IDs, excluding the primary. |
| `system_prompt_file` | omitted | Explicit UTF-8 system template; no common system prompt is injected. |
| `prompt_version` | `"1"` | User-managed prompt identity. |
| `prompt_variables` | `{}` | Alias to fixed finite text or JSON. |
| `context_providers` | `{}` | Alias to extension, config and required offline `preview`. |
| `knowledge` | `{}` | Stable ID to complete local UTF-8 document path. |
| `context` | `{}` | Static finite JSON mapping. |
| `context_file` | omitted | Alternative JSON file; cannot be combined with `context`. |
| `information` | omitted | Information-profile ID; requires `$information` in a prompt. |
| `response_schema` | `reservoir-action.v1` | Common action or registered response extension. |
| `backend` | omitted | Explicitly registered backend extension; otherwise the generic LLM backend. |
| `parameters` | `{}` | Opaque extension parameters, excluding public identity/method/model/prompt/auditor keys. |
| `execution` | live | `replay` selects offline supplied/saved replies for a custom LLM backend only. |

Built-in placeholders are `$agent_id`, `$observation`, `$knowledge`,
`$previous_transition` and `$information`. Custom aliases must be identifiers and
cannot overlap built-ins. Use `$$` for a literal dollar sign.

## Context provider

| Key | Required / default | Meaning |
|---|---|---|
| `extension` | required | Registered extension ID exposing `build_context`. |
| `config` | `{}` | Finite JSON passed through extension validation. |
| `preview` | required | Offline value used by `check`; no callback runs. |

At run time the callback receives immutable `agent_id`, `observation` and
`previous_transition`, then returns a `ContextValue` containing value,
provenance and availability.

## Rule parameters

Rule agents require no model or prompt. `rule_based` is the operating class;
`rule` chooses a user-registered implementation. The framework does not prescribe
an algorithm list. The example-local Hanasaki wrapper accepts:

| Rule | `rule_parameters` key | Required / default | Meaning |
|---|---|---|---|
| `hanasaki` | `inflow_statistics_file` | required path | Pinned `reservoir-benchmark-statistics.v1` JSON. |
| `hanasaki` | `purpose` | `flood_control` | Existing `flood_control` or `other` metadata; does not select another controller. |
| `hanasaki` | `alpha` | `0.85` | Finite value in `(0, 1]`. |

The statistics document identifies reservoir, reference period, mean and monthly
mean inflow, reference-day count, source path, hash, format and columns. Register
another module to implement your own operating curves, water-supply or hydropower
controller. It must validate and interpret its own `rule_parameters`; these
controller names do not identify built-in algorithms. Rule modules expose
`validate_backend`, `build_backend` and `rebase_agent` hooks.
"Baseline" names a comparison run. "Offline" means no real provider request;
it includes rules and LLM test/replay paths using supplied or saved replies.

## Physical case and network

The weather entry requires `reservoir-physical-case.v1` with `data_kind` equal to
`simulated_local_inflow` or `synthetic_fixture`. Its `network` uses
`llm-reservoir-network.v2` for new work.

| Network key | Required / default | Meaning |
|---|---|---|
| `schema_version` | required | `llm-reservoir-network.v2`. |
| `start_date` | required | First operation date. |
| `reservoirs` | required mapping | Physical and operation settings by exact ID. |
| `junctions` | `[]` | Additional routing-node IDs. |
| `connections` | required | Acyclic source/target edges with optional fraction and unit hydrograph. |
| `outlets` | required nonempty list | Exact terminal nodes; every terminal appears once. |
| `node_locations` | `{}` | Structured metadata for known nodes. |
| `assumptions` | `{}` | Declared case assumptions. |

Independent river systems use multiple outlets in one experiment. Information
locations do not become routing nodes or edges.

Each controlled reservoir requires `inflow_node` and `physical`. A connection's
`fraction` defaults to 1 and lies in `(0, 1]`. Unit-hydrograph weights are
nonnegative and sum to 1. Outgoing fractions from each internal node sum to 1.

## Reservoir physics

| Key | Unit / constraint |
|---|---|
| `reservoir_id` | Nonempty physical reservoir ID, unique across the network; it may differ from the reservoir graph key. |
| `capacity_m3` | Positive m³. |
| `dead_storage_m3` | Nonnegative m³ below capacity. |
| `initial_storage_m3` | Between dead storage and capacity. |
| `minimum_release_cms` | Nonnegative m³/s. |
| `maximum_release_cms` | m³/s, at least the minimum. |
| `dt_seconds` | Positive seconds; the current runner requires daily `86400`. |

An agent's `reservoir_id` selects the **graph key**; `physical.reservoir_id`
identifies the physical reservoir in its records. For FE Walter these are
`FEWalter` and `fe_walter`, respectively. Preserve each reference in its own role.

The kernel clips a requested release to operating and available-water bounds,
computes spill above capacity, and checks mass balance. Initial storage is an
operation assumption; hydrological warm-up does not create it.

## Information profile

The v2 `information` section contains `sources` and `profiles`. Source types are
`static`, `csv`, `simulation` and registered `extension`. Profile fields specify
`source`, optional `required` (default true), `unit`, `history` (default 1), and
`max_age_seconds`. See [Decision information](INFORMATION.md) for causal selection.

## Auditors and outcome checks

Built-in decision auditors are `release_bounds` and `field_range`. A suite
aggregates `FAIL > UNKNOWN > WARN > PASS`; an empty suite is UNKNOWN. Audits are
diagnostic and do not replace the action.

Outcome checks compare a routed node with scalar or selected-information bounds
after routing. They write `outcome_audit.jsonl` and do not change releases.

## Output evidence

| Path | Contents |
|---|---|
| `experiment.json`, `summary.json` | Normalized settings, hashes, runtime identity and counts. |
| provider ledger and `raw/` | Actual messages, requests, replies, usage, attempts and source references. |
| `decisions.jsonl` | Observation and normalized proposal. |
| `audit.jsonl`, `outcome_audit.jsonl` | Decision and post-routing diagnostics. |
| `physics.jsonl` | Requested/implemented release, spill, storage and balance. |
| `reservoir_trajectory.csv` | Reservoir rates and storage. |
| `network_flows.csv`, `network_balance.csv` | Routed flow and network accounting. |
| `reach_volume_trace.json` | Reach inflow, outflow and channel storage. |

[Build a simulation](BUILD_SIMULATION.md) · [Configuration](CONFIGURATION.md) ·
[Two-reservoir example](MULTI_RESERVOIR.md)

## Legacy compatibility appendix

Earlier agent syntax remains accepted, but one agent cannot mix old and public
fields. Use the public names above for new configurations.

| Earlier syntax | Public syntax |
|---|---|
| `reservoir` | `reservoir_id` |
| `strategy: benchmark`, `mode: offline`, `benchmark.statistics` | `type: rule_based`, `rule: hanasaki`, `rule_parameters.inflow_statistics_file` |
| `strategy: configured`, `mode: offline`, `release_cms` | Retained legacy fixed-release test path; new rule agents select a registered extension. |
| `strategy: configured`, `mode: llm`, `model`, `prompt.user` | `type: llm`, `model_profile`, `prompt_file` |
| `prompt.system`, extra prompt/context fields | `customization.system_prompt_file` and other `customization` entries |
| `strategy: reference_v3_7`, `reference` | `type: llm`, `customization.backend: reference_v3_7`, `customization.parameters.reference` |

Older v1 experiment files and information section names remain supported. Source
and trace records may show normalized internal `mode`/`strategy` identifiers;
those identifiers preserve compatibility rather than adding public agent types.
