# Configure agents, prompts and context

Use one `hydroops-coupled-simulation.v2` file as the experiment entry point.
Keep large sections in separate YAML files so hydrology, agents and models can
change independently and remain reviewable.

## Split the configuration

The two-reservoir example uses:

```yaml
schema_version: hydroops-coupled-simulation.v2
run_id: independent-rivers-rule
output: ../../runs/independent-rivers-rule
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
max_calls: null
hydrology: {file: hydrology.yaml}
agents: {file: agents.rule.yaml}
models: {file: models.yaml}
information: {file: information.yaml}
auditors: {file: auditors.yaml}
extensions:
  local_retrieval: extensions/__init__.py
  hanasaki: ../rules/hanasaki/__init__.py
```

`hydrology`, `models`, `agents`, `auditors`, `information` and `extensions` may
be inline. The first five may instead be exactly `{file: path}`. A file reference
cannot contain inline values, and the loader does not deep-merge files.

Every path is relative to the file that declares it. For example, a prompt path
inside `agents.llm.yaml` is relative to `agents.llm.yaml`, while `case` is relative
to the top-level experiment. Cycles and missing section files stop validation.

Older inline `hydroops-coupled-simulation.v1` configurations remain accepted.
Use v2 for new work because it records the split inputs directly.

## Separate the experiment from each reservoir

The top-level experiment sets the shared dates, output, physical case, hydrology,
model catalog, information catalog and auditor catalog. Each entry under `agents`
sets one reservoir's method and selects entries from those catalogs. Reservoirs
in the same experiment may use different methods, models, prompts and information
profiles. A shared catalog does not automatically expose its contents to an agent.

The physical case's `network.connections` and `outlets` describe where water goes.
Information sources and agent information profiles describe what the operator can
see. A gauge or forecast location does not add a physical connection.

## Select rule-based or LLM operation

Rule-based agents need no model or prompt:

```yaml
operator_a:
  reservoir_id: lake_a
  type: rule_based
  rule: hanasaki
  rule_parameters:
    alpha: 0.85
    inflow_statistics_file: statistics_a.json
  auditors: [bounds]
```

`rule` names a rule extension explicitly registered in the experiment's
`extensions` catalog. `rule_parameters` is an opaque mapping interpreted by that
extension. Here `hanasaki` is the example's inflow-history rule, with pinned
statistics and an example `alpha` of `0.85`; it is not a framework method enum.
The example's optional `purpose` retains its existing metadata and does not
select a seasonal-pool or hydropower controller.

To use your own operating curves, water-supply or hydropower controller, register
your Python rule module and select its ID in `rule`. The module implements
`validate_backend`, `build_backend` and `rebase_agent` hooks; the common engine
still applies physics, routing, audits and trace writing. Implement and test the
controller's own parameters and behavior. A controller name does not supply its
algorithm. The physical kernel determines the feasible implemented release.
The built backend provides `decide(observation)`, a `policy_id` and
`network_calls=0`. The generic rule wrapper records the selected `rule_id` and
source pins; it supplies no model transport to the rule module.

A general LLM agent selects a model profile and a user instruction template:

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    prompt_version: '1'
    prompt_variables:
      purpose: demonstrate an independently configured operator
    context_providers:
      guidance:
        extension: local_retrieval
        config:
          documents: knowledge/guidance.json
        preview: 'Offline preview: use only supplied state and guidance.'
    fallback_models: []
  auditors: [bounds]
```

`prompt_file` must contain text. No common system prompt is automatically added.
Use `customization.system_prompt_file` only when the study supplies a separate
system instruction. Both templates use Python `string.Template` syntax; write
`$$` for a literal dollar sign. Optional knowledge, context, information, prompt
variables, response schema and fallbacks belong under `customization`.

Choose `type: rule_based` for an explicit operating rule or controller and
`type: llm` when studying model decisions with prompts and available information.
A baseline is a comparison run, not an algorithm name.
Offline means no real model-provider request: rule agents run offline, and test
or replay LLM paths use supplied or saved replies. It is not a third agent type.

### Customize a backend only when needed

`customization.backend` selects an explicitly registered extension. Its
`customization.parameters` mapping contains backend-specific settings, for example
`reference: {...}` for the F.E. Walter case. Parameters cannot replace public
identity, method, model, prompt or auditor fields. An extension that constructs
its own messages may omit `prompt_file`; it must explicitly validate and pin its
prompt resources. `customization.execution: replay` is an offline test option for
custom LLM backends. The default is live execution. The case extension preserves
Anik's message construction; it does not define a shared prompt for other agents.

## Build the prompt namespace

Rule modules can also select an information profile with
`customization: {information: downstream}`. The engine passes the selected,
available values in `observation.context.decision_information`; the rule decides
how to use them. This does not create a water connection or a prompt.

Built-in placeholders are:

| Placeholder | Value |
|---|---|
| `$agent_id` | JSON agent ID |
| `$observation` | Protected current hydrology and static context |
| `$previous_transition` | Previous committed observation, action and physics; `null` on day one |
| `$knowledge` | Hash-pinned full text from the agent's `knowledge` mapping |
| `$information` | Selected `decision-information.v1` snapshot; requires an information profile |

Add fixed text or JSON with `customization.prompt_variables`. The following
blocks are entries inside the agent's `customization` mapping:

```yaml
prompt_variables:
  purpose: flood-season demonstration
  preferences: {avoid_large_changes: true}
```

The alias becomes a template placeholder, such as `$purpose`. Aliases must be
identifiers, cannot replace built-in names and must be unique across fixed and
dynamic context.

## Add dynamic context with an extension

`context_providers` connect a prompt alias to a registered extension:

```yaml
context_providers:
  guidance:
    extension: local_retrieval
    config: {documents: knowledge/guidance.json}
    preview: 'Offline preview used by check.'
```

`check` uses `preview`. It does not call the callback or access a network source.
At decision time, the extension's `build_context(config)` returns a callback. The
callback receives an immutable `DecisionContext` with `agent_id`, `observation`
and `previous_transition`, then returns:

```python
ContextValue(
    value="selected guidance",
    provenance={
        "source_sha256": "...",
        "query": "...",
        "document_ids": ["guide-1"],
        "available_at": "2020-02-27T00:00:00Z",
    },
    available=True,
)
```

The example performs a small local selection from JSON. A project can connect a
vector database through the same callback contract, but HydroOpsLLM does not ship
a general vector-database connector. Pin source bytes and preserve provenance.

Use [decision information](INFORMATION.md) for timestamped observations,
forecasts and simulation fields. Use a context provider for custom computation
or retrieval. Neither path can modify storage, inflow or physical limits.

## Add explicit fallback models

`fallback_models` is an ordered list of model profile IDs. It defaults to an
empty list:

```yaml
model_profile: openai_primary
customization:
  fallback_models: [anthropic_backup, local_backup]
```

Each profile runs its own bounded `max_attempts`. The ledger records every
attempt, actual provider, actual model, request hash, response metadata and error.
Authentication and configuration errors are terminal. Audit FAIL, physical
failure and evidence-write failure never select another model.

Fallbacks are an explicit availability policy. They are not a claim that two
models implement the same operating policy.

## Keep experiment evidence

For reproducible work, retain:

- the complete split configuration and all source hashes;
- full prompts, context provenance and provider request/response records;
- hydrology and reservoir initial-state evidence;
- physics, routing and audit journals; and
- runtime and provider identifiers.

Full raw logs and checkpoints can require substantial storage. Plan retention
before a long experiment. No current example supplies a provider performance or
decision-quality benchmark.

Continue with [model providers](MODEL_PROVIDERS.md), then run the
[offline check, prepare and run sequence](BUILD_SIMULATION.md#5-check-without-running-anything).
