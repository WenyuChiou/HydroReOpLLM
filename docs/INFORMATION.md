# Decision information

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

Decision information is optional typed data selected for an operator at decision
time, such as a published forecast or operating target. A profile exposes only
named fields and enforces causal availability. It does not change the physical
river network, inflow, storage, or release limits.

Download [information.yaml](../templates/coupled/information.yaml) or browse the
[complete template folder](TEMPLATES.md).

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

An LLM agent selects the profile with `customization.information` and places
`$information` in its prompt. A Rule-based agent may select the same profile and
read the resulting fields from `observation.context.decision_information`.
Selecting one profile does not expose the rest of the source catalog.

Use `prompt_variables` for fixed prompt text or JSON and `context_providers` for
custom retrieval or computation. Those inputs may carry provenance, but they do
not gain authority over reservoir physics.
