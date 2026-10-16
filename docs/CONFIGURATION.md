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
```

`hydrology`, `models`, `agents`, `auditors`, `information` and `extensions` may
be inline. The first five may instead be exactly `{file: path}`. A file reference
cannot contain inline values, and the loader does not deep-merge files.

Every path is relative to the file that declares it. For example, a prompt path
inside `agents.llm.yaml` is relative to `agents.llm.yaml`, while `case` is relative
to the top-level experiment. Cycles and missing section files stop validation.

Older inline `hydroops-coupled-simulation.v1` configurations remain accepted.
Use v2 for new work because it records the split inputs directly.

## Select rule-based or configured operation

Rule-based agents need no model or prompt:

```yaml
operator_a:
  reservoir: lake_a
  mode: offline
  strategy: benchmark
  benchmark:
    purpose: flood_control
    alpha: 0.85
    statistics: statistics_a.json
  auditors: [bounds]
```

A general LLM agent selects a model profile and owns both prompt messages:

```yaml
operator_a:
  reservoir: lake_a
  mode: llm
  strategy: configured
  model: local
  prompt:
    system: prompts/system.txt
    user: prompts/operator.txt
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

`strategy: configured` has no hidden shared system text. `prompt.system` and
`prompt.user` are explicit `PromptSpec` inputs. The user template must contain
text; the system template may be empty. Both use Python `string.Template` syntax.
Write `$$` for a literal dollar sign.

## Build the prompt namespace

Built-in placeholders are:

| Placeholder | Value |
|---|---|
| `$agent_id` | JSON agent ID |
| `$observation` | Protected current hydrology and static context |
| `$previous_transition` | Previous committed observation, action and physics; `null` on day one |
| `$knowledge` | Hash-pinned full text from the agent's `knowledge` mapping |
| `$information` | Selected `decision-information.v1` snapshot; requires an information profile |

Add fixed text or JSON with `prompt_variables`:

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
model: openai_primary
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
