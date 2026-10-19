# Rule-based and LLM operators

An operator agent controls one physical reservoir. Choose `type: rule_based` to
run explicitly registered user code without a model request, or `type: llm` to
request a release from a configured provider. Both methods return the same
controlled release action to common reservoir physics and routing.

## Start with a Rule-based operator

Use a deterministic user rule to verify IDs, dates, physics, routing, and saved
evidence before introducing a live provider. The template registers a minimal
user-owned rule named `user_registered_rule`; replace its controller or
parameters with the rule your study evaluates.

Download [agents.rule.yaml](../templates/coupled/agents.rule.yaml), browse the
[template folder](TEMPLATES.md), and inspect the included
[rule package](../templates/coupled/extensions/user_registered_rule/__init__.py).

```{literalinclude} ../templates/coupled/agents.rule.yaml
:language: yaml
```

| Field | Purpose and units | Required? | User-filled or referenced value |
|---|---|---|---|
| Agent key | Stable operator ID | Required | Replace `YOUR_AGENT_ID` |
| `reservoir_id` | Physical reservoir controlled by this agent | Required | Key from `reservoirs.yaml` |
| `type` | Public method classification | Required | `rule_based` |
| `rule` | Registered extension ID | Required | Key from `experiment.extensions` |
| `rule_parameters` | Opaque settings interpreted by that rule | Required by selected rule | User values and rule-owned units |
| `auditors` | Diagnostic checks applied to decisions | Optional | Unique IDs from `auditors.yaml` |

Rule modules implement `validate_backend()` and `build_backend()`. Their backend
provides `decide(observation)`, `policy_id`, and `network_calls = 0`. The common
engine remains responsible for storage, spill, routing, auditing, and records.

## Switch to an LLM operator

After the Rule-based setup verifies, point `experiment.yaml` from
`agents.rule.yaml` to `agents.llm.yaml`. The complete LLM agent file keeps model,
prompt, information, and audit choices explicit.

Download [agents.llm.yaml](../templates/coupled/agents.llm.yaml) or browse the
[complete template folder](TEMPLATES.md).

```{literalinclude} ../templates/coupled/agents.llm.yaml
:language: yaml
```

| Field | Purpose and units | Required? | User-filled or referenced value |
|---|---|---|---|
| Agent key | Stable operator ID | Required | Replace `YOUR_AGENT_ID` |
| `reservoir_id` | Physical reservoir controlled by this agent | Required | Key from `reservoirs.yaml` |
| `type` | Public method classification | Required | `llm` |
| `model_profile` | Provider settings selected by ID | Required | Profile key from `models.yaml` |
| `prompt_file` | User message template | Required for the configured backend | Path relative to the agent file |
| `customization.system_prompt_file` | Explicit system message | Optional | Path relative to the agent file |
| `customization.prompt_version` | User prompt provenance label | Optional | Nonempty text |
| `customization.information` | Decision information profile | Optional | Profile ID from `information.yaml` |
| `customization.fallback_models` | Ordered alternate model profiles | Optional | List of model IDs; default empty |
| `auditors` | Diagnostic checks | Optional | Unique IDs from `auditors.yaml` |

Each controlled reservoir must have exactly one unique operator. Model profiles
may be shared, but reservoir state and committed history remain separate.

## Configure a model profile

The model catalog holds provider connection and generation settings. A profile
is validated during `check` without provider discovery or a network request.
Replace `YOUR_MODEL` with the exact model ID selected for the study.

Download [models.yaml](../templates/coupled/models.yaml) or read the
[provider-specific reference](MODEL_PROVIDERS.md).

```{literalinclude} ../templates/coupled/models.yaml
:language: yaml
```

| Field | Purpose | Required? |
|---|---|---|
| `provider` | Request and reply adapter | Required |
| `model` | Provider model ID | Required |
| `base_url` | Final HTTP(S) API base URL | Required |
| `api_key_env` | Environment variable containing a key | Optional; needed by authenticated services |
| `temperature`, `max_tokens` | Generation controls | Optional |
| `timeout_seconds` | Per-attempt timeout | Optional; default 60 |
| `max_attempts` | Bounded attempts for this profile | Optional; default 1 |
| `retry_delay_seconds` | Delay between retryable attempts | Optional; default 2 |

## Select diagnostic auditors

Auditors inspect a proposed action and its context. They write findings but do
not change release, storage, or routing. Agents select auditor IDs from this
shared catalog.

Download [auditors.yaml](../templates/coupled/auditors.yaml).

```{literalinclude} ../templates/coupled/auditors.yaml
:language: yaml
```

| Field | Purpose and units | Required? |
|---|---|---|
| Auditor key | ID listed by an agent | Required |
| `type` | Configured check | Required; `release_bounds` or `field_range` |
| `version` | User provenance label | Optional; default `1` |
| `tolerance_cms` | Allowed release-bound tolerance, m³/s | Optional; default `0` |

## Build the prompt

HydroOpsLLM does not inject a shared system prompt. The supplied text files are
ordinary user-owned templates using Python `string.Template` placeholders.
Write `$$` for a literal dollar sign.

Download [operator.txt](../templates/coupled/prompts/operator.txt) and
[system.txt](../templates/coupled/prompts/system.txt).

```{literalinclude} ../templates/coupled/prompts/operator.txt
:language: text
```

```{literalinclude} ../templates/coupled/prompts/system.txt
:language: text
```

| Placeholder | Value | Required by template? |
|---|---|---|
| `$agent_id` | Current operator ID as JSON | Optional |
| `$observation` | Current protected hydrology and reservoir state | Usually required |
| `$previous_transition` | Previous committed observation, action, and physics; `null` on day one | Optional |
| `$information` | Selected causal information snapshot | Requires an information profile |
| `$knowledge` | Hash-pinned text from the agent knowledge mapping | Requires configured knowledge |

<a id="add-dynamic-context-with-an-extension"></a>

Selecting information or context does not automatically place it in a prompt;
the template must contain its placeholder. Conversely, remove `$information`
when the agent does not select an information profile. Custom fixed values use
`prompt_variables`; custom retrieval or computation uses `context_providers`
that return a provenance-bearing `ContextValue`.

Live `run` and any unfinished LLM decisions during `resume` require explicit
network permission. Rule-based agents and `check` do not call a model provider.
![Prompt construction and response validation](figures/prompt-context-workflow.svg)

*Figure 2. State, completed history and the template form the messages; the
dashed arrow adds optional context. The LLM also receives a response schema.
Validation produces the release proposal. [Editable draw.io source](figures/prompt-context-workflow.drawio).*
