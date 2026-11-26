# Gauges and forecasts

<div class="hero-band" markdown="1">

An `information` profile supplies **read-only, time-ordered** stream gauges, inflow forecasts, seasonal guide curves, or committed upstream reservoir states to an operator—never leaking future flood peaks into today's decision.

</div>

## Timing rules at decision time

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Built-in reservoir awareness

- Current beginning `storage_m3` and today's routed `inflow_cms` (already including same-step upstream releases along `unit_hydrograph[0]`).
- Previous committed steps (`$previous_transition` / `$completed_history`).
- Another reservoir's committed `simulation` storage or release **from the prior completed step** (`available` starting Day 2; set `required: false` on Day 1).

</div>
<div class="panel-card" markdown="1">

### No-future-leakage guards

- All CSV timestamps require `Z` or an explicit UTC offset.
- **Observations**: Visible only when `valid_time <= clock` and `available_at <= clock`.
- **Forecasts**: `valid_time` may be future, provided `issued_at <= clock` and `available_at <= clock`.

</div>
</div>

## Source types and unit conversions

| `type` | Required fields | Optional fields | Purpose |
| --- | --- | --- | --- |
| `static` | `quantity`, `unit`, `location`, `value` | `datum` | Constant target release, flood stage, or guide table. |
| `csv` | `quantity`, `unit`, `location`, `kind` (`observation` \| `forecast`), `path` | `datum` | Timestamped gauge observations or issued forecasts. |
| `simulation` | `quantity` (`inflow` \| `storage` \| `release` \| `flow`), `unit`, `location` | `datum` | Read-only state from another reservoir, junction, or outlet (`m3`, `m3/s`). |
| `extension` | `quantity`, `unit`, `location`, `provider` | `kind`, `parameters`, `datum` | Custom Python reader returning timestamped records. |

**Observation CSV** (`valid_time,available_at,value`):

```csv
valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-01T00:00:00Z,1240.0
2021-01-02T00:00:00Z,2021-01-02T00:00:00Z,1580.0
```

**Forecast CSV** (`issued_at,valid_time,available_at,value`):

```csv
issued_at,valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-02T00:00:00Z,2021-01-01T00:00:00Z,1450.0
2021-01-01T00:00:00Z,2021-01-03T00:00:00Z,2021-01-01T00:00:00Z,1920.0
```

Built-in profile conversions (`unit:`): `m3/s` ↔ `cfs` (`35.31466672148859`), `m3` ↔ `acre-ft` (`1 / 1233.48183754752`), and `m` ↔ `ft` (`3.280839895013123`).

## Configuring profiles and agent bindings

```yaml
# information.yaml
sources:
  downstream_gauge:
    type: csv
    kind: observation
    quantity: flow
    unit: cfs
    location: usgs_01449000
    path: data/lehighton_obs.csv
  upstream_storage:
    type: simulation
    quantity: storage
    unit: m3
    location: upper_dam
profiles:
  operator_view:
    fields:
      lehighton_flow_cms: { source: downstream_gauge, unit: m3/s, history: 3, max_age_seconds: 86400, required: false }
      upper_pool_acft: { source: upstream_storage, unit: acre-ft, required: false }  # Unavailable on Day 1 before step 0 completes
```

Reference `information: { file: information.yaml }` in `experiment.yaml`, then set `customization.information: operator_view` on the agent and include `$information` in its prompt (or read `observation["context"]["decision_information"]` in Python rules). See [Rules & LLM prompts](AGENT_DESIGN.md).

## Missing-data handling and verification

| Field setting | Missing or stale behavior | Verification check |
| --- | --- | --- |
| `required: true` | Stops the run immediately (never substitutes `0.0`). | Reconstructs static, CSV, and simulation values during `verify`. |
| `required: false` | Sets `status: "MISSING"`, `value: null`, and an explicit `reason`. | Checks timestamp ordering across every step in `decisions.jsonl`. |
