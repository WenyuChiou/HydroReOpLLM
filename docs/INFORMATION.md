# Decision information

[English](INFORMATION.md) | [繁體中文](INFORMATION.zh-TW.md)

Decision information is a snapshot of selected fields available when a decision
is made. This availability rule makes the snapshot causal. It
does not replace the host observation or physical state. The feature extends
the existing `llm-reservoir-experiment.v1` YAML with optional
`information_sources`, `information_profiles`, and an agent `information` field.
Existing configurations produce identical messages when they do not opt in.
The current loader and runner support this opt-in contract under the same schema
version. Older releases reject the added keys as unknown.

## Source types

Every source requires `type`, `quantity`, `unit`, and `location`. `datum` is
optional structured metadata. Source IDs are unique. IDs and declared text
metadata must not contain surrounding whitespace; invalid declarations stop
before information selection or a model request.

| Type | Additional fields | Selection meaning |
|---|---|---|
| `static` | `value` | Constant JSON value; always available |
| `csv` observation | `path`, `kind: observation` | Latest eligible actual sample |
| `csv` forecast | `path`, `kind: forecast` | Earliest horizon from latest eligible issue cycle |
| `simulation` | none | Causal host value from the current or a previously committed step, as described below |
| `extension` | `provider`, optional `parameters`, optional `kind` | Records from a provider registered in Python and passed through `information_providers=` |

CSV columns are exact. Observations use
`valid_time,available_at,value`; forecasts use
`issued_at,valid_time,available_at,value`. Every timestamp must be an aware ISO
timestamp with `Z` or an explicit UTC offset. CSV bytes and their parsed samples are frozen for saved-file verification. An
extension names a registered provider ID and version; YAML cannot import Python.

Simulation `quantity` is one of `inflow`, `storage`, `release`, or `flow`.
Locations must be known network or reservoir IDs. Only the acting reservoir's
inflow and storage are current at its decision step. Another reservoir's inflow,
storage, or release comes from its prior committed operation; routed flow also
comes from a previous completed step. Simulation sources use native `m3/s` for
flow, inflow, and release and `m3` for storage. A profile field can request a
supported output conversion. A label never selects physical data or an F.E.
Walter operating rubric automatically.

Extension provider IDs are registered by the host and passed with the
`information_providers` keyword to `load_settings` or `run_settings`. YAML cannot
import or name an arbitrary Python object. Extension `kind` defaults to
`observation`. An extension that returns forecasts must declare `kind: forecast`,
and each forecast record must include `issued_at`.

## Profiles and fields

Each profile contains a `fields` mapping. A field alias is the public name shown
to the prompt and to outcome checks.

| Field option | Type | Default | Meaning |
|---|---|---|---|
| `source` | source ID | required | Source selected by this alias |
| `required` | boolean | `true` | Stop before a model request when missing or stale |
| `unit` | text | source unit | Supported output unit conversion |
| `history` | positive integer | `1` | Number of eligible samples retained |
| `max_age_seconds` | nonnegative number | no limit | Maximum causal age |

For observations, eligibility requires both `valid_time` and `available_at` no
later than the decision time. Age is measured from `valid_time`; history is the
latest eligible N actual samples, retaining only the latest available revision for each valid time. For forecasts, the latest issue cycle available
at decision time is chosen. Only horizons whose `valid_time` is at or after the
decision time are eligible. If an issue cycle contains revisions for one
`valid_time`, the latest available revision is retained. The scalar is the
earliest eligible horizon, and history is the earliest N eligible horizons in
that same cycle. Forecast age is measured from `issued_at`.

Missing required or stale information stops before the model. Missing optional
information is an explicit `MISSING` record with a reason and `value: null`; it
is never silently replaced by zero.

## YAML example

This is a configuration fragment for a generic configured strategy; the case,
model profile, auditor and prompt file must also be declared in the complete
experiment. Values below are illustrative, not operating defaults. The preserved `reference_v3_7` profiles reject these extra fields so
their original messages remain byte-reproducible.

```yaml
schema_version: llm-reservoir-experiment.v1
case: ../my_case/case.json
run_id: information-example
output: ../runs/information-example
max_calls: 3

information_sources:
  storage_target:
    type: static
    quantity: storage_target
    unit: m3
    location: R1
    value: 2500000.0
  observed_inflow:
    type: csv
    kind: observation
    path: ../my_case/inflow_observations.csv
    quantity: inflow
    unit: m3/s
    location: R1
  routed_forecast:
    type: csv
    kind: forecast
    path: ../my_case/forecast.csv
    quantity: flow
    unit: m3/s
    location: control_point
  required_flow:
    type: static
    quantity: minimum_flow_requirement
    unit: m3/s
    location: control_point
    value: 25.0

information_profiles:
  operator_view:
    fields:
      target_m3: {source: storage_target}
      recent_inflow: {source: observed_inflow, history: 2, max_age_seconds: 172800}
      forecast_cms: {source: routed_forecast, required: false, history: 3}
      required_flow_cms: {source: required_flow}

agents:
  operator_1:
    reservoir: R1
    strategy: configured
    mode: llm
    model: reservoir_model
    prompt: ../my_case/operator.txt
    prompt_version: "2"
    information: operator_view
    knowledge: {}
    context: {}
    response_schema: reservoir-action.v1
    auditors: [release_limits]
```

The source catalog declares what can be selected. The profile gives prompt-safe
aliases to an explicit subset. The agent selects one profile, and its prompt must
place `$information` where that copied snapshot should appear. An outcome check
may reference one selected numeric alias as a bound; it does not search the
catalog or infer a criterion from a source label.

The prompt file must explicitly contain `$information`. Opting in to a profile
does not expose every catalog source. `$observation` remains the protected host
observation; a prompt author can use both placeholders when both are needed.
An opted-in decision must also receive a complete model reply (`done: true` and
not truncated) before the physical state can update.

## Rendered `decision-information.v1`

`$information` is a copied JSON snapshot. Its top level contains
`schema_version`, `decision_time`, and `fields`. Each alias record contains:

| Field | Meaning |
|---|---|
| `status` | `AVAILABLE` or `MISSING` |
| `value`, `unit`, `quantity`, `location` | Selected value and physical identity |
| `source_id`, `kind` | Declared source and source kind |
| `valid_time`, `available_at` | Event time and host-availability time |
| `issued_at` | Forecast issue time, for forecasts |
| `history` | Selected samples with the same provenance fields |
| `source_sha256` or `provider_version` | CSV byte identity or registered extension version |
| `datum` | Optional declared datum metadata |
| `reason` | Why an optional field is missing |

The catalog and returned snapshot are copied before use. A backend cannot mutate
the host physical core through an information object.

The selected snapshot is stored under
`observation.context.decision_information` in the decision trace. Together with
the rendered messages, normalized action, physics record and optional outcome
audit, it preserves the selected source, times, decision and routed result.

## Host time and prescribed forcing

The current runner is daily. Legacy host labels such as `2016-01-01` are anchored
to UTC for catalog selection. This anchor is a reproducibility convention. It
does not claim that an instantaneous observation or a full current-day average
was available in real operations. In the F.E. Walter demonstration, daily
simulated inflow is prescribed forcing, not measured future availability.

## Control-point outcome checks

`outcome_checks` evaluates routed flow after routing. It is diagnostic and does
not optimize routing, correct a release, or guarantee safety.

```yaml
outcome_checks:
  downstream_minimum:
    node: control_point
    minimum_information: {agent: operator_1, field: required_flow_cms}
    maximum_cms: 250.0
    tolerance_cms: 1.0e-9
```

Each check ID maps to `node` and at least one bound. `minimum_cms` and
`maximum_cms` are optional nonnegative scalar bounds. A dynamic bound instead
uses `minimum_information` or `maximum_information`, each with an `agent` and
selected information `field`. A scalar and information reference cannot both
define the same bound. `tolerance_cms` is nonnegative and defaults to `1e-9`.

A dynamic limit uses that agent field at the same decision timestep. The field
must exist; unavailable optional information yields `UNKNOWN`. Results are
written independently to `outcome_audit.jsonl` with schema
`control-point-audit.v1`, check ID, time, node, routed flow, resolved limits,
status, limit sources and decision references. Counts remain separate from
historical request-audit counts. A same-timestep control-point result is a
system result; it does not assign causal blame to one agent.

Choose a criterion explicitly from the basin objective and upstream priorities.
HydroOpsLLM supplies no reservoir-type-specific downstream limits. Full water-use
allocation and turbine/head/energy solving are outside the current scope;
hydrological input tests are not hydropower validation. Registered extensions control their own source access; the LLM request budget does not govern those provider calls. Saved-file verification checks captured extension timing and version without contacting that source again.

[Previous: Model instructions](LLM_MODULES.md) · [Next: Results and trace](RESULTS_GUIDE.md)
