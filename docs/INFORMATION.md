# Available information

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

Decision information is optional typed data selected for an operator at decision
time, such as a published forecast or operating target. A profile exposes only
named fields and enforces causal availability. It does not change the physical
river network, inflow, storage, or release limits.

Download [information.yaml](../templates/coupled/information.yaml) or browse the
[complete template folder](TEMPLATES.md).

## Add an observed station series

For example, give `lake_a`'s operator a downstream flow observation. You need
four connected settings: a source, a profile, the agent's selected profile and
the prompt placeholder. The values and names below are a teaching example,
not observations from the article.

**1. Add the source and select its field in `information.yaml`:**

```yaml
sources:
  downstream_gauge:
    type: csv
    kind: observation
    quantity: flow
    unit: m3/s
    location: river_a
    path: observations/gauge.csv
profiles:
  operator_view:
    fields:
      downstream_flow_cms:
        source: downstream_gauge
        required: true
```

**2. Supply `observations/gauge.csv`:**

```text
valid_time,available_at,value
2020-02-27T00:00:00Z,2020-02-27T01:00:00Z,1.2
```

The observation describes `valid_time` and becomes usable at `available_at`.
Both must be no later than the decision. Replace the example with actual dated
observations; future or missing required data stops the request.

**3. Reference the file in `experiment.yaml`, and select the profile in your LLM agent:**

```yaml
# experiment.yaml
information:
  file: information.yaml
```

```yaml
# agents.llm.yaml (the other model and prompt settings are unchanged)
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: primary
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

**4. Include the selected data in `prompts/operator.txt`:**

```text
Current reservoir observation: $observation
Additional information: $information
Return the requested controlled release using the configured action schema.
```

Only the selected profile reaches this operator. To add another datum, add a
source and a named field to that profile. For a forecast, use `kind: forecast`
and CSV columns `issued_at,valid_time,available_at,value`: its issue and
availability times must already be known when the decision is made.

## Add a fixed operating target

Use the static source below when a value does not change with time. The value
is information for the operator, not a new physical release constraint.

```{literalinclude} ../templates/coupled/information.yaml
:language: yaml
```

| Field | Purpose and units | Required? | User-filled or referenced value |
|---|---|---|---|
| `sources` | Catalog of available data declarations | Required section; may be empty | User-defined source IDs |
| `type` | Source adapter | Required per source | `static`, `csv`, `simulation`, or registered `extension` |
| `quantity` | Physical or study quantity label | Required | User-defined text |
| `unit` | Source physical unit | Required | Must match the underlying value |
| `location` | Stable spatial label | Required | Network ID or user-defined location as appropriate |
| `datum` | Structured reference metadata | Optional | JSON-compatible mapping |
| `value` | Constant value | Required for `static` | JSON-compatible user value |
| `path` | Timed record file | Required for `csv` | Path relative to `information.yaml` |
| `kind` | Timed record interpretation | Required for `csv` | `observation` or `forecast` |
| `profiles` | Named views selected by agents | Required section; may be empty | User-defined profile IDs |
| `fields.<alias>.source` | Source exposed under a prompt-safe alias | Required | Source ID from this file |
| `required` | Whether missing or stale data stops the decision | Optional; default `true` | Boolean |
| `unit` | Requested supported output conversion | Optional | Compatible unit |
| `history` | Number of eligible samples retained | Optional; default `1` | Positive integer |
| `max_age_seconds` | Maximum causal age | Optional | Nonnegative seconds |

Observation CSV files use `valid_time,available_at,value`. Forecast files use
`issued_at,valid_time,available_at,value`. Timestamps require `Z` or an explicit
UTC offset. Observations must be valid and available by the decision time.
Forecasts may describe a future time, but their issue and availability times
must already be causal.

Simulation sources expose current or previously committed host values. Supported
quantities are `inflow`, `storage`, `release`, and `flow`. Another reservoir's
state or release and routed flow come from a committed step; a label never reads
physical data automatically.

Supported conversions are m³/s and cfs, m³ and acre-ft, and m and ft. Missing
optional information becomes an explicit `MISSING` value with `value: null`; it
is never changed to zero.

An LLM agent selects the profile with `customization.information`. The generic
prompt uses `$information`; the FE Walter backend appends the selected snapshot
to its existing user message. A Rule-based agent may select the same profile and
read the resulting fields from `observation.context.decision_information`.
Selecting one profile does not expose the rest of the source catalog.

Use `prompt_variables` for fixed prompt text or JSON and `context_providers` for
custom retrieval or computation. Those inputs may carry provenance, but they do
not gain authority over reservoir physics.

For FE Walter, follow [additional decision inputs](../examples/fe_walter/extensions/retrieval/README.md).
It connects a downstream station CSV and a retrieval callback to either LLM
method. The complete [information template](../tutorials/config/fe_walter_information.yaml)
uses explicitly labelled synthetic data. The [notebook](../tutorials/README.md)
shows where these optional fields fit into the existing experiment.

Custom backends opt in with `supports_prompt_context = True`. The workflow then
validates and source-pins their `context_providers`, supplies lazy per-agent
callbacks to `build_backend`, and binds the chosen information profile. Existing
custom backends retain their declared contracts. See the
[FE adapter](../examples/fe_walter/extensions/__init__.py) for the implementation.
