# Decision-time information

An information profile gives one operator a named, read-only view of additional
data at decision time. It can expose a fixed target, a timestamped observation
or forecast, or a value already committed by the simulation. It cannot change
storage, inflow, release limits, routing, or another reservoir's state.

## What the operator knows at a step

The acting reservoir receives its current interval-mean inlet flow and beginning
storage in the normal observation. This means a daily case assumes the current
day's mean inlet is known when that day's release is chosen. Completed history
contains earlier steps only. Values from other reservoirs become available only
after their step is committed.

For external CSV data, the decision clock is the step timestamp. An observation
is eligible only when both `valid_time` and `available_at` are no later than that
clock. A forecast may describe a future `valid_time`, but both `issued_at` and
`available_at` must be no later than the decision. Timestamps require `Z` or an
explicit UTC offset.

## Configure a profile

Start from [`templates/coupled/information.yaml`](../templates/coupled/information.yaml).
This runnable structure exposes one static value under one prompt-safe alias:

```yaml
sources:
  operating_target:
    type: static
    quantity: target_release
    unit: m3/s
    location: lake_a
    value: 2.5
profiles:
  operator_view:
    fields:
      operating_target_cms:
        source: operating_target
        required: true
```

Reference the catalog from the coupled experiment, then select the profile on
the intended agent:

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.llm.yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

When a generic LLM agent selects an information profile, include the literal
placeholder `$information` in its prompt file. The runtime inserts the selected
snapshot there. A
rule-based extension can read the same snapshot from
`observation.context.decision_information`. Selecting one profile does not
expose the rest of the catalog.

## Source types

| `type` | Required source fields | Availability behavior |
|---|---|---|
| `static` | `quantity`, `unit`, `location`, `value` | Always available; useful for a fixed target or label. |
| `csv` | common fields plus `kind` and `path` | Exact UTF-8 CSV bytes are hashed; causal timestamps select a record. |
| `simulation` | common fields | Reads `inflow`, `storage`, `release`, or `flow` from the current/committed native state. |
| `extension` | common fields plus registered `provider` | Calls a versioned local reader declared by the application. |

Observation CSV columns are exactly `valid_time,available_at,value`. Forecast
columns are exactly `issued_at,valid_time,available_at,value`. A profile field
may also set `unit`, `history`, `max_age_seconds`, and `required`. Supported
conversions include m3/s and cfs, m3 and acre-ft, and m and ft.

If a required field has no causal, fresh record, the decision stops. An optional
field is saved explicitly with `status: MISSING`, `value: null`, and a reason;
missing data is never changed to zero. Available fields include the selected
value, unit, location, source ID, timestamps, requested sample history, and a
CSV hash or extension version when applicable.

Run `reservoir-experiment check path/to/experiment.yaml` after every catalog or
agent change. The selected snapshot is stored inside each decision observation
and checked by `verify`. For static, CSV and simulation sources the verifier
reconstructs the selected values. For registered extensions it checks the saved
timing, provenance and internal consistency without calling the external reader again. Continue with the
[run lifecycle](RUNNING.md) or [results guide](RESULTS_GUIDE.md).
