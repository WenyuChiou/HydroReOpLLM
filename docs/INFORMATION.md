# Decision information

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

Decision information is additional data selected for an agent at decision time,
such as a published inflow forecast or a downstream flow requirement. A profile
names which fields that agent may use. It keeps unavailable future observations
out of the decision and does not change the physical river network.

The core observation already supplies current inflow and reservoir state.
Use this optional information section when your study needs more data. The same
profile mechanism is available to Rule-based and LLM agents; a rule reads the
selected values from its observation, while an LLM template places `$information`.

In a v2 experiment, use one `information` section:

```yaml
information: {file: information.yaml}
```

The section file contains `sources` and `profiles`:

```yaml
sources:
  storage_target:
    type: static
    quantity: storage_target
    unit: m3
    location: lake_a
    value: 750000
  observed_inflow:
    type: csv
    kind: observation
    path: data/inflow_observations.csv
    quantity: inflow
    unit: m3/s
    location: lake_a

profiles:
  operator_view:
    fields:
      target_m3: {source: storage_target}
      recent_inflow:
        source: observed_inflow
        history: 2
        max_age_seconds: 172800
```

The CSV path is relative to `information.yaml`. Older inline v1 experiments may
continue to use `information_sources` and `information_profiles`; do not combine
the legacy keys with the v2 `information` section.

## Select a profile from an agent

The agent selects one profile and its prompt explicitly places `$information`:

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator_with_information.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: operator_view
```

```text
Current physical observation: $observation
Selected causal information: $information
```

The profile and placeholder must be configured together. Selecting a profile does
not expose every source in the catalog.

## Source types

Every source declares `type`, `quantity`, `unit` and `location`. `datum` is
optional structured metadata.

| Type | Additional fields | Selection meaning |
|---|---|---|
| `static` | `value` | Constant JSON value, always available. |
| `csv`, observation | `path`, `kind: observation` | Latest eligible actual sample. |
| `csv`, forecast | `path`, `kind: forecast` | Earliest eligible horizon from the latest eligible issue cycle. |
| `simulation` | none | Causal current or previously committed host value. |
| `extension` | registered provider and parameters | Records supplied by an explicitly registered information provider. |

Observation CSV columns are `valid_time,available_at,value`. Forecast CSV
columns are `issued_at,valid_time,available_at,value`. Timestamps require `Z` or
an explicit UTC offset. CSV bytes and parsed samples are pinned.

Simulation quantities are `inflow`, `storage`, `release` or `flow`. The acting
reservoir's inflow and storage can be current. Another reservoir's state or
release, and routed flow, come from a previously committed step. A label never
selects physical data automatically.

## Profile field controls

| Option | Default | Meaning |
|---|---|---|
| `source` | required | Source selected by this prompt-safe alias. |
| `required` | `true` | Stop before a request if the value is missing or stale. |
| `unit` | source unit | Supported output unit conversion. |
| `history` | `1` | Positive number of eligible samples retained. |
| `max_age_seconds` | no limit | Maximum causal age. |

Supported conversions are m³/s ↔ cfs, m³ ↔ acre-ft, and m ↔ ft. Missing optional
information becomes an explicit `MISSING` record with `value: null`; it is never
silently changed to zero.

For observations, both `valid_time` and `available_at` must be no later than the
decision time. The latest available revision for each valid time wins. For
forecasts, selection uses the latest issue cycle available by decision time and
keeps horizons at or after that time. Forecast age is measured from `issued_at`.

## Distinguish information from prompt context

Use an information profile for typed, timestamped sources that may also support
outcome checks. Use `prompt_variables` for fixed text or JSON. Use
`context_providers` for custom computation or retrieval that returns a
`ContextValue` with provenance.

All three become prompt inputs. None can override the current inflow, storage,
release bound, reservoir physics or network. The two-reservoir example's
`local_retrieval` extension demonstrates a context callback; it is not an
information source and has no vector-database dependency.

## Rendered snapshot

`$information` is a `decision-information.v1` JSON object with
`schema_version`, `decision_time` and `fields`. Each alias records:

- `AVAILABLE` or `MISSING` status;
- value, unit, quantity and location;
- source ID and kind;
- valid, available and forecast-issue times when applicable;
- selected history;
- source hash or provider version; and
- datum metadata or a missing reason.

The selected snapshot is copied into
`observation.context.decision_information` and retained with the rendered
messages. This records what was selected; it does not prove the information was
correct or sufficient for operation.

## Control-point outcome checks

An `outcome_check` evaluates routed flow after routing. It is diagnostic and does
not correct a release or optimize the network:

```yaml
outcome_checks:
  downstream_minimum:
    node: river_a
    minimum_information: {agent: operator_a, field: required_flow_cms}
    maximum_cms: 250
    tolerance_cms: 1.0e-9
```

Each check has a node and at least one bound. A bound can be a nonnegative scalar
or one numeric field selected for an agent at the same timestep. Missing optional
information yields `UNKNOWN`. Results are written to `outcome_audit.jsonl` and do
not change historical decision audits, routing or releases.

The daily simulated inflow used by a teaching case is prescribed forcing. Its
date label does not by itself establish real-world observation availability.

[Prompt and context configuration](CONFIGURATION.md) ·
[LLM modules](LLM_MODULES.md) · [Results and trace](RESULTS_GUIDE.md)
