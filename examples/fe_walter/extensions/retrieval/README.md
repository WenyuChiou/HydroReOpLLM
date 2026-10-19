# Additional decision inputs

Both FE Walter LLM methods can append downstream observations, fixed text and
retrieved passages to their existing user message. Select these inputs in a copy
of the experiment and agent files. The supplied annual results retain their
original inputs.

1. Add an `information` file reference to the experiment. The complete
   [information template](../../../../tutorials/config/fe_walter_information.yaml)
   selects a downstream flow in cfs. Its CSV is a **synthetic interface fixture**;
   replace it with your station data. Each observation needs `valid_time`,
   `available_at` and `value`, with timezone-qualified timestamps.
2. Select its profile and any extra context inside the agent's existing
   `customization` block. Keep the current `backend` and `parameters`. From
   `examples/fe_walter/coupled/`, the additional fields are:

```yaml
information: downstream_conditions  # Profile ID from the information file.
prompt_variables:
  study_note: Your study-specific instructions.
context_providers:
  operating_context:                 # Label of the appended prompt section.
    extension: saved_retrieval       # Registry ID declared in the experiment.
    config:
      passages_file: ../../../tests/fixtures/fe_walter_information/passages.json
      query: downstream operating guidance
    preview:                         # Displayed during checks; retrieval does not run.
      query: preview only
      passages: []
```

3. Add `saved_retrieval: ../extensions/retrieval/__init__.py` to the experiment's
   existing `extensions` mapping. Add `information: {file:
   ../../../tutorials/config/fe_walter_information.yaml}` at the experiment root.
   Relative file paths start from the file that declares them.

| Input | Prompt and saved record |
|---|---|
| `information` | Selected fields, values, units, status and availability appear under **Additional decision information**. The same snapshot is saved in the observation. |
| `prompt_variables` | Fixed text or JSON appears under **Additional context**, labelled by its key. |
| `context_providers` | Each callback returns text or JSON. Its value and provenance are saved in `backend_trace.context_provenance`; the value is appended to the user message. |
| `preview` | A configuration preview value. It is replaced by the callback result for a decision. |

An observation must have been measured and published by decision time. Optional
missing measurements stay `MISSING` with a null value. Required missing inputs,
callback errors and unavailable or future callback values stop before a provider
request or a physical update. The normal response schema, model parameters and
physical inflow remain in effect. The default daily consultation setting requests
one decision per day; a provider retry reuses that decision's materialized context.

## Connect a vector database

The [local adapter source](__init__.py) implements `validate_context(config,
base_path=...)`, `rebase_context(...)` and `build_context(config)`. It reads
[saved synthetic passages](../../../../tests/fixtures/fe_walter_information/passages.json)
and makes no external request. For a vector database, register your own extension
with the same `build_context` interface and select its registry ID above.

`build_context` returns a callable accepting an immutable `DecisionContext`:
`agent_id`, `observation` and `previous_transition`. It can query with the date,
reservoir state and selected downstream fields. Return a `ContextValue` whose
value contains the query and passages, including document IDs; put the source,
index/version and `available_at` (and `issued_at` when applicable) in provenance.
The framework checks the supplied availability times against decision time.
The retriever must also filter its documents to the information available then.

Configuration checks use only the declared preview. Retrieval is constructed
lazily for each agent and runs once per new decision. On resume, a committed
decision's saved context is reused before a retriever is constructed. This example
adds the connection point; no vector database dependency is installed.
